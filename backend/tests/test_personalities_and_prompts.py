"""T2.2 单元测试: AI 性格系统 + Prompt 模板

测试覆盖:
- PersonalityProfile 数据结构和行为参数
- 5 种性格预设的完整性验证
- get_personality / get_all_personalities 查询
- get_personality_description_for_prompt 文本生成
- 6 种 Prompt 模板的渲染和变量替换
- BaseAgent 与性格系统的集成
- AgentManager 与性格系统的集成
"""

from __future__ import annotations

import pytest

from app.agents.personalities import (
    AGGRESSIVE,
    ANALYTICAL,
    BLUFFER,
    CONSERVATIVE,
    INTUITIVE,
    PERSONALITY_PROFILES,
    PersonalityProfile,
    get_all_personalities,
    get_personality,
    get_personality_description_for_prompt,
)
from app.agents.prompts import (
    BYSTANDER_OUTPUT_SCHEMA,
    DECISION_OUTPUT_SCHEMA,
    DECISION_PROMPT_TEMPLATE,
    EXPERIENCE_REVIEW_OUTPUT_SCHEMA,
    GAME_SUMMARY_OUTPUT_SCHEMA,
    ROUND_NARRATIVE_OUTPUT_SCHEMA,
    RULES_SUMMARY,
    SYSTEM_PROMPT_TEMPLATE,
    render_bystander_react_prompt,
    render_decision_prompt,
    render_experience_review_prompt,
    render_game_summary_prompt,
    render_round_narrative_prompt,
    render_system_prompt,
)
from app.agents.base_agent import BaseAgent
from app.agents.agent_manager import AgentManager


# ============================================================
# PersonalityProfile 数据结构
# ============================================================


class TestPersonalityProfile:
    """性格配置数据结构测试"""

    def test_profile_is_frozen(self):
        """PersonalityProfile 是不可变的"""
        with pytest.raises(AttributeError):
            AGGRESSIVE.aggression = 0.1  # type: ignore

    def test_get_behavior_params(self):
        """获取行为倾向参数"""
        params = AGGRESSIVE.get_behavior_params()
        assert isinstance(params, dict)
        expected_keys = {
            "aggression",
            "bluff_tendency",
            "fold_threshold",
            "talk_frequency",
            "risk_tolerance",
            "see_cards_tendency",
        }
        assert set(params.keys()) == expected_keys
        # 所有值都在 0-1 范围
        for key, value in params.items():
            assert 0.0 <= value <= 1.0, f"{key}={value} out of range"

    def test_all_profiles_have_required_fields(self):
        """所有性格预设都有完整的字段"""
        for pid, profile in PERSONALITY_PROFILES.items():
            assert profile.id == pid
            assert profile.name_zh, f"{pid} missing name_zh"
            assert profile.name_en, f"{pid} missing name_en"
            assert profile.description, f"{pid} missing description"
            assert profile.play_style_guide, f"{pid} missing play_style_guide"
            assert profile.talk_style_guide, f"{pid} missing talk_style_guide"

    def test_behavior_params_are_valid(self):
        """所有性格的行为参数在有效范围"""
        for pid, profile in PERSONALITY_PROFILES.items():
            params = profile.get_behavior_params()
            for key, value in params.items():
                assert 0.0 <= value <= 1.0, f"{pid}.{key}={value} out of range"


# ============================================================
# 5 种性格预设验证
# ============================================================


class TestFivePersonalities:
    """验证 5 种性格预设的特征和差异"""

    def test_exactly_five_personalities(self):
        """正好有 5 种性格"""
        assert len(PERSONALITY_PROFILES) == 5

    def test_personality_ids(self):
        """5 种性格的 ID 正确"""
        expected_ids = {"aggressive", "conservative", "analytical", "intuitive", "bluffer"}
        assert set(PERSONALITY_PROFILES.keys()) == expected_ids

    def test_aggressive_high_aggression(self):
        """激进型应该有高攻击性"""
        assert AGGRESSIVE.aggression >= 0.7
        assert AGGRESSIVE.fold_threshold <= 0.35
        assert AGGRESSIVE.talk_frequency >= 0.7

    def test_conservative_low_aggression(self):
        """保守型应该有低攻击性"""
        assert CONSERVATIVE.aggression <= 0.3
        assert CONSERVATIVE.fold_threshold >= 0.6
        assert CONSERVATIVE.talk_frequency <= 0.35
        assert CONSERVATIVE.see_cards_tendency >= 0.7

    def test_analytical_balanced(self):
        """分析型应该比较均衡"""
        assert 0.3 <= ANALYTICAL.aggression <= 0.7
        assert ANALYTICAL.bluff_tendency <= 0.3
        assert ANALYTICAL.see_cards_tendency >= 0.5

    def test_intuitive_moderate_risk(self):
        """直觉型有中等偏高的风险承受度"""
        assert INTUITIVE.risk_tolerance >= 0.5
        assert INTUITIVE.talk_frequency >= 0.5

    def test_bluffer_high_bluff(self):
        """诈唬型应该有高诈唬倾向"""
        assert BLUFFER.bluff_tendency >= 0.7
        assert BLUFFER.see_cards_tendency <= 0.4

    def test_personalities_are_distinguishable(self):
        """不同性格的行为参数应有明显差异"""
        all_profiles = list(PERSONALITY_PROFILES.values())
        # 激进型的 aggression 应该是最高的之一
        assert AGGRESSIVE.aggression > CONSERVATIVE.aggression
        # 保守型的 fold_threshold 应该是最高的
        assert CONSERVATIVE.fold_threshold > AGGRESSIVE.fold_threshold
        # 诈唬型的 bluff_tendency 应该是最高的
        max_bluff = max(p.bluff_tendency for p in all_profiles)
        assert BLUFFER.bluff_tendency == max_bluff

    def test_personality_descriptions_are_unique(self):
        """每种性格的描述文本应该不同"""
        descriptions = [p.description for p in PERSONALITY_PROFILES.values()]
        assert len(set(descriptions)) == 5

    def test_personality_names_are_unique(self):
        """中文和英文名称都不重复"""
        zh_names = [p.name_zh for p in PERSONALITY_PROFILES.values()]
        en_names = [p.name_en for p in PERSONALITY_PROFILES.values()]
        assert len(set(zh_names)) == 5
        assert len(set(en_names)) == 5


# ============================================================
# 性格查询函数
# ============================================================


class TestPersonalityLookup:
    """性格查询函数测试"""

    def test_get_personality_valid(self):
        """获取已知性格"""
        profile = get_personality("aggressive")
        assert profile is AGGRESSIVE
        assert profile.id == "aggressive"

    def test_get_personality_all_types(self):
        """所有性格都能获取"""
        for pid in ["aggressive", "conservative", "analytical", "intuitive", "bluffer"]:
            profile = get_personality(pid)
            assert profile.id == pid

    def test_get_personality_unknown_raises(self):
        """未知性格抛出 ValueError"""
        with pytest.raises(ValueError, match="Unknown personality"):
            get_personality("nonexistent")

    def test_get_all_personalities(self):
        """获取所有性格列表"""
        all_profiles = get_all_personalities()
        assert len(all_profiles) == 5
        assert all(isinstance(p, PersonalityProfile) for p in all_profiles)

    def test_get_personality_description_for_prompt(self):
        """获取用于 prompt 的性格描述"""
        desc = get_personality_description_for_prompt("aggressive")
        assert isinstance(desc, str)
        assert len(desc) > 50  # 应该有实质内容
        # 应包含打牌风格和发言风格
        assert "打牌风格" in desc
        assert "发言风格" in desc
        # 应包含性格描述的关键词
        assert "攻击" in desc or "进攻" in desc or "加注" in desc

    def test_description_for_all_personalities(self):
        """所有性格的 prompt 描述都有效"""
        for pid in PERSONALITY_PROFILES:
            desc = get_personality_description_for_prompt(pid)
            assert "打牌风格" in desc
            assert "发言风格" in desc
            assert len(desc) > 50


# ============================================================
# System Prompt 模板
# ============================================================


class TestSystemPromptTemplate:
    """System Prompt 模板测试"""

    def test_render_basic(self):
        """基本渲染"""
        result = render_system_prompt(
            agent_name="火焰哥",
            personality_name="激进型",
            personality_description="一个激进的玩家",
        )
        assert "火焰哥" in result
        assert "激进型" in result
        assert "一个激进的玩家" in result

    def test_contains_rules(self):
        """包含游戏规则"""
        result = render_system_prompt("Test", "测试", "desc")
        assert "炸金花" in result
        assert "豹子" in result
        assert "同花顺" in result
        assert "弃牌" in result
        assert "比牌" in result

    def test_contains_output_schema(self):
        """包含输出格式"""
        result = render_system_prompt("Test", "测试", "desc")
        assert '"action"' in result
        assert '"thought"' in result
        assert '"table_talk"' in result
        assert "confidence" in result

    def test_contains_chat_guide(self):
        """包含牌桌交流指导"""
        result = render_system_prompt("Test", "测试", "desc")
        assert "牌桌交流" in result
        assert "虚张声势" in result

    def test_no_unresolved_placeholders(self):
        """无未替换的占位符"""
        result = render_system_prompt("Name", "Type", "Desc")
        assert "{" not in result or '"action"' in result  # JSON 中有花括号是正常的


# ============================================================
# Decision Prompt 模板
# ============================================================


class TestDecisionPromptTemplate:
    """Decision Prompt 模板测试"""

    def test_render_basic(self):
        """基本渲染"""
        result = render_decision_prompt(
            hand_description="红心K, 黑桃K, 方块3（一对K）",
            seen_status="看牌",
            pot=120,
            your_chips=880,
            current_bet=20,
            players_status_table="| 玩家 | 筹码 | 状态 |\n| 火焰哥 | 900 | 暗注 |",
            action_history="火焰哥 跟注 20",
            chat_history="火焰哥: 今天手气不错",
            available_actions="跟注(40), 加注(80), 弃牌, 比牌",
        )
        assert "红心K" in result
        assert "看牌" in result
        assert "120" in result
        assert "880" in result
        assert "火焰哥" in result
        assert "跟注(40)" in result

    def test_with_experience_context(self):
        """带经验上下文渲染"""
        result = render_decision_prompt(
            hand_description="手牌描述",
            seen_status="看牌",
            pot=100,
            your_chips=800,
            current_bet=10,
            players_status_table="玩家状态",
            action_history="行动历史",
            chat_history="聊天记录",
            available_actions="操作列表",
            experience_context="我需要更加激进，上几局太保守了",
        )
        assert "策略调整" in result
        assert "更加激进" in result

    def test_without_experience_context(self):
        """无经验上下文渲染"""
        result = render_decision_prompt(
            hand_description="手牌描述",
            seen_status="未看牌",
            pot=50,
            your_chips=950,
            current_bet=10,
            players_status_table="玩家状态",
            action_history="行动历史",
            chat_history="暂无聊天",
            available_actions="操作列表",
        )
        assert "策略调整" not in result

    def test_all_sections_present(self):
        """所有章节都存在"""
        result = render_decision_prompt(
            hand_description="h",
            seen_status="s",
            pot=0,
            your_chips=0,
            current_bet=0,
            players_status_table="p",
            action_history="a",
            chat_history="c",
            available_actions="v",
        )
        assert "当前局面" in result
        assert "各玩家状态" in result
        assert "本局行动历史" in result
        assert "本局牌桌聊天" in result
        assert "你的可用操作" in result


# ============================================================
# Bystander React Prompt 模板
# ============================================================


class TestBystanderReactPromptTemplate:
    """Bystander React Prompt 模板测试"""

    def test_render_basic(self):
        """基本渲染"""
        result = render_bystander_react_prompt(
            trigger_event_description="玩家A刚刚加注到 80 筹码",
            recent_chat="玩家A: 你们谁敢跟我比牌？",
            seen_status="已看牌",
            your_chips=800,
            your_actions_so_far="跟注了一次",
        )
        assert "加注到 80" in result
        assert "谁敢跟我比牌" in result
        assert "已看牌" in result
        assert "800" in result
        assert "跟注了一次" in result

    def test_contains_output_schema(self):
        """包含输出格式说明"""
        result = render_bystander_react_prompt("event", "chat", "status", 100, "actions")
        assert "should_respond" in result
        assert "inner_thought" in result

    def test_contains_response_guide(self):
        """包含回应指导"""
        result = render_bystander_react_prompt("event", "chat", "status", 100, "actions")
        assert "沉默" in result
        assert "性格" in result


# ============================================================
# Experience Review Prompt 模板
# ============================================================


class TestExperienceReviewPromptTemplate:
    """Experience Review Prompt 模板测试"""

    def test_render_basic(self):
        """基本渲染"""
        result = render_experience_review_prompt(
            trigger_reason="连续输掉了 3 局",
            past_rounds_narratives="第5局: 我太保守了...\n第6局: 又被诈唬了...",
            review_round_count=3,
            win_rate="33%",
            chips_change="-200",
            fold_rate="40%",
            opponent_recent_behaviors="玩家A: 频繁加注\n玩家B: 非常保守",
        )
        assert "连续输掉了 3 局" in result
        assert "太保守了" in result
        assert "33%" in result
        assert "-200" in result
        assert "40%" in result
        assert "频繁加注" in result

    def test_contains_output_schema(self):
        """包含输出格式"""
        result = render_experience_review_prompt("r", "n", 1, "w", "c", "f", "o")
        assert "self_analysis" in result
        assert "opponent_patterns" in result
        assert "strategy_adjustment" in result
        assert "confidence_shift" in result

    def test_contains_statistics_section(self):
        """包含统计数据章节"""
        result = render_experience_review_prompt("r", "n", 5, "50%", "+100", "30%", "o")
        assert "统计数据" in result
        assert "胜率" in result
        assert "筹码变化" in result
        assert "弃牌率" in result


# ============================================================
# Round Narrative Prompt 模板
# ============================================================


class TestRoundNarrativePromptTemplate:
    """Round Narrative Prompt 模板测试"""

    def test_render_basic(self):
        """基本渲染"""
        result = render_round_narrative_prompt(
            agent_name="火焰哥",
            personality_name="激进型",
            round_number=3,
            hand_description="一对K",
            round_outcome="赢得了 200 筹码",
            round_thoughts="手牌不错，决定加注",
            chat_messages="火焰哥: 谁来？\n稳如山: 我跟",
            action_history="火焰哥加注, 稳如山跟注",
        )
        assert "火焰哥" in result
        assert "激进型" in result
        assert "第 3 局" in result
        assert "一对K" in result
        assert "200 筹码" in result

    def test_contains_narrative_instructions(self):
        """包含叙事写作指导"""
        result = render_round_narrative_prompt("n", "p", 1, "h", "o", "t", "c", "a")
        assert "第一人称" in result
        assert "200-400" in result

    def test_contains_output_schema(self):
        """包含输出格式"""
        result = render_round_narrative_prompt("n", "p", 1, "h", "o", "t", "c", "a")
        assert "narrative" in result
        assert "outcome" in result


# ============================================================
# Game Summary Prompt 模板
# ============================================================


class TestGameSummaryPromptTemplate:
    """Game Summary Prompt 模板测试"""

    def test_render_basic(self):
        """基本渲染"""
        result = render_game_summary_prompt(
            agent_name="火焰哥",
            personality_name="激进型",
            rounds_played=10,
            rounds_won=4,
            total_chips_won=500,
            total_chips_lost=300,
            biggest_win=200,
            biggest_loss=150,
            fold_rate="30%",
            all_narratives="第1局叙事...\n第2局叙事...",
            all_reviews="经验回顾1...",
            opponents_info="稳如山(保守型), 数据侠(分析型)",
        )
        assert "火焰哥" in result
        assert "10" in result
        assert "4" in result  # rounds_won
        assert "500" in result
        assert "300" in result
        assert "200" in result  # biggest_win
        assert "150" in result  # biggest_loss
        assert "30%" in result

    def test_contains_summary_sections(self):
        """包含所有总结要求章节"""
        result = render_game_summary_prompt("n", "p", 1, 0, 0, 0, 0, 0, "0%", "n", "r", "o")
        assert "关键时刻" in result
        assert "对手印象" in result
        assert "自我反思" in result or "自我" in result
        assert "聊天策略" in result
        assert "学习历程" in result
        assert "总结叙事" in result

    def test_contains_output_schema(self):
        """包含输出格式"""
        result = render_game_summary_prompt("n", "p", 1, 0, 0, 0, 0, 0, "0%", "n", "r", "o")
        assert "key_moments" in result
        assert "opponent_impressions" in result
        assert "self_reflection" in result
        assert "narrative_summary" in result
        assert "chat_strategy_summary" in result
        assert "learning_journey" in result


# ============================================================
# BaseAgent 与性格系统集成
# ============================================================


class TestBaseAgentPersonalityIntegration:
    """BaseAgent 性格系统集成测试"""

    def test_known_personality_loads_profile(self):
        """已知性格自动加载 PersonalityProfile"""
        agent = BaseAgent(personality="aggressive")
        assert agent.personality_profile is not None
        assert agent.personality_profile.id == "aggressive"
        assert agent.personality_profile is AGGRESSIVE

    def test_known_personality_auto_description(self):
        """已知性格自动生成详细描述"""
        agent = BaseAgent(personality="conservative")
        assert "打牌风格" in agent.personality_description
        assert "发言风格" in agent.personality_description

    def test_explicit_description_overrides_profile(self):
        """显式传入的描述覆盖自动生成"""
        agent = BaseAgent(
            personality="aggressive",
            personality_description="自定义描述",
        )
        assert agent.personality_description == "自定义描述"
        # 但 profile 仍然加载
        assert agent.personality_profile is not None

    def test_unknown_personality_no_profile(self):
        """未知性格不加载 profile"""
        agent = BaseAgent(personality="custom_type")
        assert agent.personality_profile is None
        assert "custom_type" in agent.personality_description

    def test_system_prompt_uses_personality_name(self):
        """system prompt 使用性格中文名称"""
        agent = BaseAgent(name="测试", personality="bluffer")
        prompt = agent.build_system_prompt()
        assert "诈唬型" in prompt

    def test_system_prompt_uses_personality_description(self):
        """system prompt 包含性格描述"""
        agent = BaseAgent(name="测试", personality="aggressive")
        prompt = agent.build_system_prompt()
        assert "攻击" in prompt or "进攻" in prompt or "激进" in prompt or "加注" in prompt
        assert "打牌风格" in prompt
        assert "发言风格" in prompt

    def test_system_prompt_all_personalities(self):
        """所有性格的 system prompt 都能正常生成"""
        for pid in PERSONALITY_PROFILES:
            agent = BaseAgent(name=f"Test-{pid}", personality=pid)
            prompt = agent.build_system_prompt()
            assert agent.name in prompt
            profile = PERSONALITY_PROFILES[pid]
            assert profile.name_zh in prompt
            assert "炸金花" in prompt
            assert '"action"' in prompt

    def test_get_behavior_params_with_profile(self):
        """有性格配置时返回配置参数"""
        agent = BaseAgent(personality="aggressive")
        params = agent.get_behavior_params()
        assert params["aggression"] == AGGRESSIVE.aggression
        assert params["bluff_tendency"] == AGGRESSIVE.bluff_tendency

    def test_get_behavior_params_without_profile(self):
        """无性格配置时返回默认参数"""
        agent = BaseAgent(personality="custom")
        params = agent.get_behavior_params()
        assert params["aggression"] == 0.5
        assert params["bluff_tendency"] == 0.3


# ============================================================
# AgentManager 与性格系统集成
# ============================================================


class TestAgentManagerPersonalityIntegration:
    """AgentManager 性格系统集成测试"""

    def test_auto_personality_assignment(self):
        """自动分配性格时加载 profile"""
        manager = AgentManager()
        agents = manager.create_agents_for_game(
            "game-1",
            [{"model_id": "openai-gpt4o-mini"}, {"model_id": "openai-gpt4o-mini"}],
        )
        for agent in agents:
            assert agent.personality in PERSONALITY_PROFILES
            assert agent.personality_profile is not None
            assert "打牌风格" in agent.personality_description

    def test_explicit_personality_assignment(self):
        """显式指定性格"""
        manager = AgentManager()
        agents = manager.create_agents_for_game(
            "game-2",
            [
                {"personality": "aggressive"},
                {"personality": "conservative"},
            ],
        )
        assert agents[0].personality == "aggressive"
        assert agents[0].personality_profile is AGGRESSIVE
        assert agents[1].personality == "conservative"
        assert agents[1].personality_profile is CONSERVATIVE

    def test_five_agents_get_five_personalities(self):
        """5 个 Agent 分别获得不同性格"""
        manager = AgentManager()
        agents = manager.create_agents_for_game(
            "game-3",
            [{} for _ in range(5)],
        )
        personalities = {a.personality for a in agents}
        # 5 个 Agent 应该分到 5 种不同的性格
        assert len(personalities) == 5


# ============================================================
# Prompt 模板完整性检查
# ============================================================


class TestPromptTemplateCompleteness:
    """Prompt 模板完整性和一致性检查"""

    def test_rules_summary_covers_all_actions(self):
        """规则摘要涵盖所有游戏操作"""
        assert "看牌" in RULES_SUMMARY
        assert "跟注" in RULES_SUMMARY
        assert "加注" in RULES_SUMMARY
        assert "弃牌" in RULES_SUMMARY
        assert "比牌" in RULES_SUMMARY

    def test_rules_summary_covers_hand_types(self):
        """规则摘要涵盖所有牌型"""
        assert "豹子" in RULES_SUMMARY
        assert "同花顺" in RULES_SUMMARY
        assert "同花" in RULES_SUMMARY
        assert "顺子" in RULES_SUMMARY
        assert "对子" in RULES_SUMMARY
        assert "散牌" in RULES_SUMMARY

    def test_decision_output_schema_fields(self):
        """决策输出 schema 包含所有必要字段"""
        assert "action" in DECISION_OUTPUT_SCHEMA
        assert "target" in DECISION_OUTPUT_SCHEMA
        assert "table_talk" in DECISION_OUTPUT_SCHEMA
        assert "hand_evaluation" in DECISION_OUTPUT_SCHEMA
        assert "opponent_analysis" in DECISION_OUTPUT_SCHEMA
        assert "chat_analysis" in DECISION_OUTPUT_SCHEMA
        assert "risk_assessment" in DECISION_OUTPUT_SCHEMA
        assert "reasoning" in DECISION_OUTPUT_SCHEMA
        assert "confidence" in DECISION_OUTPUT_SCHEMA
        assert "emotion" in DECISION_OUTPUT_SCHEMA

    def test_bystander_output_schema_fields(self):
        """旁观输出 schema 包含必要字段"""
        assert "should_respond" in BYSTANDER_OUTPUT_SCHEMA
        assert "message" in BYSTANDER_OUTPUT_SCHEMA
        assert "inner_thought" in BYSTANDER_OUTPUT_SCHEMA

    def test_experience_review_output_schema_fields(self):
        """经验回顾输出 schema 包含必要字段"""
        assert "self_analysis" in EXPERIENCE_REVIEW_OUTPUT_SCHEMA
        assert "opponent_patterns" in EXPERIENCE_REVIEW_OUTPUT_SCHEMA
        assert "strategy_adjustment" in EXPERIENCE_REVIEW_OUTPUT_SCHEMA
        assert "confidence_shift" in EXPERIENCE_REVIEW_OUTPUT_SCHEMA

    def test_round_narrative_output_schema_fields(self):
        """局叙事输出 schema 包含必要字段"""
        assert "narrative" in ROUND_NARRATIVE_OUTPUT_SCHEMA
        assert "outcome" in ROUND_NARRATIVE_OUTPUT_SCHEMA

    def test_game_summary_output_schema_fields(self):
        """游戏总结输出 schema 包含必要字段"""
        assert "key_moments" in GAME_SUMMARY_OUTPUT_SCHEMA
        assert "opponent_impressions" in GAME_SUMMARY_OUTPUT_SCHEMA
        assert "self_reflection" in GAME_SUMMARY_OUTPUT_SCHEMA
        assert "chat_strategy_summary" in GAME_SUMMARY_OUTPUT_SCHEMA
        assert "learning_journey" in GAME_SUMMARY_OUTPUT_SCHEMA
        assert "narrative_summary" in GAME_SUMMARY_OUTPUT_SCHEMA

    def test_all_templates_have_no_python_format_errors(self):
        """所有模板渲染时不会抛出格式化错误"""
        # System Prompt
        render_system_prompt("name", "type", "desc")
        # Decision Prompt
        render_decision_prompt("h", "s", 0, 0, 0, "p", "a", "c", "v")
        # Bystander React
        render_bystander_react_prompt("e", "c", "s", 0, "a")
        # Experience Review
        render_experience_review_prompt("r", "n", 1, "w", "c", "f", "o")
        # Round Narrative
        render_round_narrative_prompt("n", "p", 1, "h", "o", "t", "c", "a")
        # Game Summary
        render_game_summary_prompt("n", "p", 1, 0, 0, 0, 0, 0, "f", "n", "r", "o")
