"""单元测试: Prompt 模板

测试覆盖:
- 6 种 Prompt 模板的渲染和变量替换
- BaseAgent 基本创建
- AgentManager 创建 Agent
"""

from __future__ import annotations

from app.agents.prompts import (
    BYSTANDER_OUTPUT_SCHEMA,
    DECISION_OUTPUT_SCHEMA,
    EXPERIENCE_REVIEW_OUTPUT_SCHEMA,
    GAME_SUMMARY_OUTPUT_SCHEMA,
    ROUND_NARRATIVE_OUTPUT_SCHEMA,
    RULES_SUMMARY,
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
# System Prompt 模板
# ============================================================


class TestSystemPromptTemplate:
    """System Prompt 模板测试"""

    def test_render_basic(self):
        """基本渲染"""
        result = render_system_prompt(agent_name="火焰哥")
        assert "火焰哥" in result

    def test_contains_rules(self):
        """包含游戏规则"""
        result = render_system_prompt("Test")
        assert "炸金花" in result
        assert "豹子" in result
        assert "同花顺" in result
        assert "弃牌" in result
        assert "比牌" in result

    def test_contains_output_schema(self):
        """包含输出格式"""
        result = render_system_prompt("Test")
        assert '"action"' in result
        assert '"thought"' in result
        assert '"table_talk"' in result
        assert "confidence" in result

    def test_contains_chat_guide(self):
        """包含牌桌交流指导"""
        result = render_system_prompt("Test")
        assert "牌桌交流" in result
        assert "虚张声势" in result

    def test_no_personality_references(self):
        """不应包含性格系统占位符"""
        result = render_system_prompt("Name")
        # 不应有未替换的 personality 相关占位符
        assert "{personality_name}" not in result
        assert "{personality_description}" not in result

    def test_contains_win_goal(self):
        """包含'目标是赢'的指导"""
        result = render_system_prompt("TestAgent")
        assert "赢" in result or "胜" in result


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
            round_number=3,
            hand_description="一对K",
            round_outcome="赢得了 200 筹码",
            round_thoughts="手牌不错，决定加注",
            chat_messages="火焰哥: 谁来？\n稳如山: 我跟",
            action_history="火焰哥加注, 稳如山跟注",
        )
        assert "火焰哥" in result
        assert "第 3 局" in result
        assert "一对K" in result
        assert "200 筹码" in result

    def test_contains_narrative_instructions(self):
        """包含叙事写作指导"""
        result = render_round_narrative_prompt("n", 1, "h", "o", "t", "c", "a")
        assert "第一人称" in result
        assert "200-400" in result

    def test_contains_output_schema(self):
        """包含输出格式"""
        result = render_round_narrative_prompt("n", 1, "h", "o", "t", "c", "a")
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
            rounds_played=10,
            rounds_won=4,
            total_chips_won=500,
            total_chips_lost=300,
            biggest_win=200,
            biggest_loss=150,
            fold_rate="30%",
            all_narratives="第1局叙事...\n第2局叙事...",
            all_reviews="经验回顾1...",
            opponents_info="稳如山, 数据侠",
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
        result = render_game_summary_prompt("n", 1, 0, 0, 0, 0, 0, "0%", "n", "r", "o")
        assert "关键时刻" in result
        assert "对手印象" in result
        assert "自我反思" in result or "自我" in result
        assert "聊天策略" in result
        assert "学习历程" in result
        assert "总结叙事" in result

    def test_contains_output_schema(self):
        """包含输出格式"""
        result = render_game_summary_prompt("n", 1, 0, 0, 0, 0, 0, "0%", "n", "r", "o")
        assert "key_moments" in result
        assert "opponent_impressions" in result
        assert "self_reflection" in result
        assert "narrative_summary" in result
        assert "chat_strategy_summary" in result
        assert "learning_journey" in result


# ============================================================
# BaseAgent 基本测试
# ============================================================


class TestBaseAgentBasic:
    """BaseAgent 基本功能测试"""

    def test_create_agent_default(self):
        """默认创建 Agent"""
        agent = BaseAgent()
        assert agent.name == "AI Player"
        assert agent.agent_id is not None

    def test_create_agent_with_name(self):
        """指定名称创建 Agent"""
        agent = BaseAgent(name="测试AI")
        assert agent.name == "测试AI"

    def test_system_prompt_contains_agent_name(self):
        """system prompt 包含 Agent 名称"""
        agent = BaseAgent(name="火焰哥")
        prompt = agent.build_system_prompt()
        assert "火焰哥" in prompt
        assert "炸金花" in prompt
        assert '"action"' in prompt

    def test_no_personality_attributes(self):
        """Agent 不应有 personality 相关属性"""
        agent = BaseAgent(name="测试")
        assert not hasattr(agent, "personality")
        assert not hasattr(agent, "personality_profile")
        assert not hasattr(agent, "personality_description")


# ============================================================
# AgentManager 基本测试
# ============================================================


class TestAgentManagerBasic:
    """AgentManager 基本功能测试"""

    def test_create_agents(self):
        """创建多个 Agent"""
        manager = AgentManager()
        agents = manager.create_agents_for_game(
            "game-1",
            [{"model_id": "copilot-gpt4o-mini"}, {"model_id": "copilot-gpt4o-mini"}],
        )
        assert len(agents) == 2
        for agent in agents:
            assert agent.name
            assert agent.model_id == "copilot-gpt4o-mini"

    def test_agents_have_unique_names(self):
        """Agent 名称不重复"""
        manager = AgentManager()
        agents = manager.create_agents_for_game(
            "game-2",
            [{} for _ in range(5)],
        )
        names = [a.name for a in agents]
        assert len(set(names)) == 5

    def test_explicit_name(self):
        """显式指定名称"""
        manager = AgentManager()
        agents = manager.create_agents_for_game(
            "game-3",
            [{"name": "自定义名"}],
        )
        assert agents[0].name == "自定义名"


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
        render_system_prompt("name")
        # Decision Prompt
        render_decision_prompt("h", "s", 0, 0, 0, "p", "a", "c", "v")
        # Bystander React
        render_bystander_react_prompt("e", "c", "s", 0, "a")
        # Experience Review
        render_experience_review_prompt("r", "n", 1, "w", "c", "f", "o")
        # Round Narrative
        render_round_narrative_prompt("n", 1, "h", "o", "t", "c", "a")
        # Game Summary
        render_game_summary_prompt("n", 1, 0, 0, 0, 0, 0, "f", "n", "r", "o")
