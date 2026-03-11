"""T2.1 单元测试: BaseAgent + AgentManager

测试覆盖:
- BaseAgent 初始化与配置
- System prompt 构建
- LLM 响应解析（JSON 正常解析、容错、降级）
- LLM 调用（mock）
- AgentManager 生命周期管理
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import (
    BaseAgent,
    Decision,
    LLMCallError,
    ThoughtData,
)
from app.agents.agent_manager import AgentManager, get_agent_manager
from app.models.game import GameAction


# ============================================================
# BaseAgent 初始化
# ============================================================


class TestBaseAgentInit:
    """BaseAgent 初始化测试"""

    def test_default_init(self):
        agent = BaseAgent()
        assert agent.name == "AI Player"
        assert agent.model_id == "openai-gpt4o-mini"
        assert agent.personality == "analytical"
        assert agent.agent_id  # 自动生成 UUID

    def test_custom_init(self):
        agent = BaseAgent(
            agent_id="test-id",
            name="测试选手",
            model_id="anthropic-claude-sonnet",
            personality="aggressive",
            personality_description="一个非常激进的玩家",
        )
        assert agent.agent_id == "test-id"
        assert agent.name == "测试选手"
        assert agent.model_id == "anthropic-claude-sonnet"
        assert agent.personality == "aggressive"
        assert agent.personality_description == "一个非常激进的玩家"

    def test_invalid_model_id_fallback(self):
        agent = BaseAgent(model_id="nonexistent-model")
        assert agent.model_id == "openai-gpt4o-mini"

    def test_default_personality_description(self):
        agent = BaseAgent(personality="bluffer")
        assert "bluffer" in agent.personality_description

    def test_repr(self):
        agent = BaseAgent(name="火焰哥", model_id="openai-gpt4o-mini", personality="aggressive")
        repr_str = repr(agent)
        assert "火焰哥" in repr_str
        assert "openai-gpt4o-mini" in repr_str
        assert "aggressive" in repr_str


# ============================================================
# System Prompt 构建
# ============================================================


class TestBuildSystemPrompt:
    """System prompt 构建测试"""

    def test_contains_agent_identity(self):
        agent = BaseAgent(name="火焰哥", personality_description="激进好斗")
        prompt = agent.build_system_prompt()
        assert "火焰哥" in prompt
        assert "激进好斗" in prompt

    def test_contains_rules(self):
        agent = BaseAgent()
        prompt = agent.build_system_prompt()
        assert "炸金花" in prompt
        assert "豹子" in prompt
        assert "同花顺" in prompt
        assert "弃牌" in prompt

    def test_contains_output_schema(self):
        agent = BaseAgent()
        prompt = agent.build_system_prompt()
        assert '"action"' in prompt
        assert '"thought"' in prompt
        assert '"table_talk"' in prompt
        assert '"confidence"' in prompt

    def test_contains_chat_guidance(self):
        agent = BaseAgent()
        prompt = agent.build_system_prompt()
        assert "牌桌交流" in prompt
        assert "虚张声势" in prompt


# ============================================================
# 响应解析 - 正常 JSON
# ============================================================


class TestParseDecisionNormal:
    """正常 JSON 响应解析测试"""

    def _make_agent(self):
        return BaseAgent(name="测试Agent")

    def test_parse_complete_json(self):
        agent = self._make_agent()
        raw = json.dumps(
            {
                "action": "call",
                "target": None,
                "table_talk": "我跟了，走着瞧",
                "thought": {
                    "hand_evaluation": "一对K，不错",
                    "opponent_analysis": "对手加注频繁",
                    "chat_analysis": "对方在虚张声势",
                    "risk_assessment": "风险可控",
                    "reasoning": "底池赔率值得",
                    "confidence": 0.7,
                    "emotion": "自信",
                },
            }
        )
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.CALL
        assert decision.target is None
        assert decision.table_talk == "我跟了，走着瞧"
        assert decision.thought is not None
        assert decision.thought.hand_evaluation == "一对K，不错"
        assert decision.thought.confidence == 0.7
        assert decision.thought.emotion == "自信"

    def test_parse_fold_action(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "fold", "target": None, "table_talk": None, "thought": {}})
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.FOLD
        assert decision.table_talk is None

    def test_parse_compare_action_with_target(self):
        agent = self._make_agent()
        raw = json.dumps(
            {
                "action": "compare",
                "target": "player-2",
                "table_talk": "来比一把！",
                "thought": {"confidence": 0.9},
            }
        )
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.COMPARE
        assert decision.target == "player-2"

    def test_parse_raise_action(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "raise", "thought": {"emotion": "兴奋"}})
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.RAISE

    def test_parse_check_cards_action(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "check_cards", "thought": {}})
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.CHECK_CARDS


# ============================================================
# 响应解析 - 容错
# ============================================================


class TestParseDecisionFaultTolerance:
    """响应解析容错测试"""

    def _make_agent(self):
        return BaseAgent(name="容错Agent")

    def test_json_in_markdown_code_block(self):
        agent = self._make_agent()
        raw = '```json\n{"action": "call", "thought": {"confidence": 0.5}}\n```'
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.CALL

    def test_json_with_surrounding_text(self):
        agent = self._make_agent()
        raw = '我的决策是: {"action": "raise", "thought": {}} 就这样。'
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.RAISE

    def test_chinese_action_name(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "跟注", "thought": {}})
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.CALL

    def test_chinese_action_name_raise(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "加注", "thought": {}})
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.RAISE

    def test_chinese_action_name_fold(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "弃牌", "thought": {}})
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.FOLD

    def test_null_string_target_treated_as_none(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "call", "target": "null", "thought": {}})
        decision = agent.parse_decision_response(raw)
        assert decision.target is None

    def test_none_string_target_treated_as_none(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "call", "target": "None", "thought": {}})
        decision = agent.parse_decision_response(raw)
        assert decision.target is None

    def test_empty_table_talk_treated_as_none(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "call", "table_talk": "", "thought": {}})
        decision = agent.parse_decision_response(raw)
        assert decision.table_talk is None

    def test_confidence_clamped_to_range(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "call", "thought": {"confidence": 1.5}})
        decision = agent.parse_decision_response(raw)
        assert decision.thought.confidence == 1.0

        raw = json.dumps({"action": "call", "thought": {"confidence": -0.5}})
        decision = agent.parse_decision_response(raw)
        assert decision.thought.confidence == 0.0

    def test_invalid_confidence_defaults(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "call", "thought": {"confidence": "很高"}})
        decision = agent.parse_decision_response(raw)
        assert decision.thought.confidence == 0.5

    def test_missing_thought_field(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "call"})
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.CALL
        # thought 应从空 dict 解析得到默认值
        assert decision.thought is not None


# ============================================================
# 响应解析 - 纯文本降级
# ============================================================


class TestParseDecisionTextFallback:
    """纯文本（非 JSON）降级解析测试"""

    def _make_agent(self):
        return BaseAgent(name="降级Agent")

    def test_text_with_fold_keyword(self):
        agent = self._make_agent()
        raw = "我决定弃牌，这牌太烂了。"
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.FOLD

    def test_text_with_call_keyword(self):
        agent = self._make_agent()
        raw = "I'll call this round."
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.CALL

    def test_text_with_raise_keyword(self):
        agent = self._make_agent()
        raw = "Let me raise the bet!"
        decision = agent.parse_decision_response(raw)
        assert decision.action == GameAction.RAISE

    def test_completely_unparseable_defaults_to_call(self):
        agent = self._make_agent()
        raw = "这是一段完全无关的文字，没有任何操作关键词。"
        available = [GameAction.CALL, GameAction.FOLD, GameAction.RAISE]
        decision = agent.parse_decision_response(raw, available_actions=available)
        # 降级到 call（最安全的默认操作）
        assert decision.action == GameAction.CALL

    def test_fallback_when_call_not_available(self):
        agent = self._make_agent()
        raw = "无法解析的响应"
        available = [GameAction.FOLD, GameAction.RAISE]
        decision = agent.parse_decision_response(raw, available_actions=available)
        assert decision.action == GameAction.FOLD


# ============================================================
# 响应解析 - 非法操作降级
# ============================================================


class TestParseDecisionIllegalActionFallback:
    """非法操作降级测试"""

    def _make_agent(self):
        return BaseAgent(name="降级Agent")

    def test_action_not_in_available_list(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "compare", "thought": {}})
        available = [GameAction.CALL, GameAction.FOLD, GameAction.RAISE]
        decision = agent.parse_decision_response(raw, available_actions=available)
        # compare 不在可用列表中，应降级
        assert decision.action in available

    def test_check_cards_when_already_seen(self):
        agent = self._make_agent()
        raw = json.dumps({"action": "check_cards", "thought": {}})
        # 已看牌，check_cards 不可用
        available = [GameAction.CALL, GameAction.FOLD, GameAction.RAISE, GameAction.COMPARE]
        decision = agent.parse_decision_response(raw, available_actions=available)
        assert decision.action in available
        assert decision.action != GameAction.CHECK_CARDS


# ============================================================
# LLM 调用 (mock)
# ============================================================


class TestCallLLM:
    """LLM 调用测试（mock litellm）"""

    @pytest.mark.asyncio
    async def test_successful_call(self):
        agent = BaseAgent(name="LLM测试", model_id="openai-gpt4o-mini")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"action": "call", "thought": {}}'

        with patch("app.agents.base_agent.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await agent.call_llm(
                [
                    {"role": "system", "content": "test system prompt"},
                    {"role": "user", "content": "test user prompt"},
                ]
            )

            assert result == '{"action": "call", "thought": {}}'
            mock_llm.assert_called_once()

            # 验证调用参数
            call_kwargs = mock_llm.call_args
            assert call_kwargs.kwargs["model"] == "gpt-4o-mini"
            assert call_kwargs.kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        agent = BaseAgent(name="重试测试", model_id="openai-gpt4o-mini")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": "ok"}'

        with patch("app.agents.base_agent.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            # 前两次失败，第三次成功
            mock_llm.side_effect = [
                Exception("API error"),
                Exception("Timeout"),
                mock_response,
            ]

            with patch("app.agents.base_agent.get_settings") as mock_settings:
                settings = MagicMock()
                settings.llm_temperature = 0.7
                settings.llm_timeout = 5
                settings.llm_max_retries = 3
                settings.openai_api_key = "test-key"
                settings.anthropic_api_key = ""
                settings.google_api_key = ""
                mock_settings.return_value = settings

                result = await agent.call_llm([{"role": "user", "content": "test"}])
                assert result == '{"result": "ok"}'
                assert mock_llm.call_count == 3

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        agent = BaseAgent(name="失败测试", model_id="openai-gpt4o-mini")

        with patch("app.agents.base_agent.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("Persistent error")

            with patch("app.agents.base_agent.get_settings") as mock_settings:
                settings = MagicMock()
                settings.llm_temperature = 0.7
                settings.llm_timeout = 5
                settings.llm_max_retries = 3
                settings.openai_api_key = "test-key"
                settings.anthropic_api_key = ""
                settings.google_api_key = ""
                mock_settings.return_value = settings

                with pytest.raises(LLMCallError, match="failed after 3 retries"):
                    await agent.call_llm([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_empty_content_raises_error(self):
        agent = BaseAgent(name="空内容测试", model_id="openai-gpt4o-mini")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        with patch("app.agents.base_agent.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = [mock_response, mock_response, mock_response]

            with patch("app.agents.base_agent.get_settings") as mock_settings:
                settings = MagicMock()
                settings.llm_temperature = 0.7
                settings.llm_timeout = 5
                settings.llm_max_retries = 3
                settings.openai_api_key = "test-key"
                settings.anthropic_api_key = ""
                settings.google_api_key = ""
                mock_settings.return_value = settings

                with pytest.raises(LLMCallError):
                    await agent.call_llm([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_anthropic_model_call(self):
        agent = BaseAgent(name="Claude测试", model_id="anthropic-claude-sonnet")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"action": "fold"}'

        with patch("app.agents.base_agent.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await agent.call_llm([{"role": "user", "content": "test"}])
            assert result == '{"action": "fold"}'

            call_kwargs = mock_llm.call_args
            assert call_kwargs.kwargs["model"] == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_gemini_model_call(self):
        agent = BaseAgent(name="Gemini测试", model_id="google-gemini-flash")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"action": "raise"}'

        with patch("app.agents.base_agent.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await agent.call_llm([{"role": "user", "content": "test"}])
            assert result == '{"action": "raise"}'

            call_kwargs = mock_llm.call_args
            assert call_kwargs.kwargs["model"] == "gemini/gemini-2.0-flash"


# ============================================================
# Memory / 策略上下文
# ============================================================


class TestAgentMemory:
    """Agent 记忆和策略上下文测试"""

    def test_strategy_context_default_empty(self):
        agent = BaseAgent()
        assert agent.get_strategy_context() == ""

    def test_set_and_get_strategy_context(self):
        agent = BaseAgent()
        agent.set_strategy_context("对手A喜欢诈唬，应该更多跟注")
        assert agent.get_strategy_context() == "对手A喜欢诈唬，应该更多跟注"

    def test_record_and_get_thoughts(self):
        agent = BaseAgent()
        thought = ThoughtData(
            hand_evaluation="一对K",
            reasoning="底池赔率好",
            confidence=0.8,
        )
        agent.record_thought(1, thought)
        agent.record_thought(1, ThoughtData(reasoning="第二次思考"))

        thoughts = agent.get_round_thoughts(1)
        assert len(thoughts) == 2
        assert thoughts[0].hand_evaluation == "一对K"

    def test_get_nonexistent_round_thoughts(self):
        agent = BaseAgent()
        assert agent.get_round_thoughts(99) == []

    def test_reset_for_new_game(self):
        agent = BaseAgent()
        agent.set_strategy_context("some strategy")
        agent.record_thought(1, ThoughtData())
        agent.reset_for_new_game()
        assert agent.get_strategy_context() == ""
        assert agent.get_round_thoughts(1) == []


# ============================================================
# AgentManager
# ============================================================


class TestAgentManager:
    """AgentManager 生命周期管理测试"""

    def test_create_agents_for_game(self):
        manager = AgentManager()
        agents = manager.create_agents_for_game(
            "game-1",
            [
                {"model_id": "openai-gpt4o-mini"},
                {"model_id": "anthropic-claude-sonnet", "personality": "aggressive"},
            ],
        )
        assert len(agents) == 2
        assert agents[0].model_id == "openai-gpt4o-mini"
        assert agents[1].model_id == "anthropic-claude-sonnet"
        assert agents[1].personality == "aggressive"

    def test_create_agents_with_custom_names(self):
        manager = AgentManager()
        agents = manager.create_agents_for_game(
            "game-1",
            [
                {"name": "测试玩家A"},
                {"name": "测试玩家B"},
            ],
        )
        assert agents[0].name == "测试玩家A"
        assert agents[1].name == "测试玩家B"

    def test_create_agents_auto_assigns_personality(self):
        manager = AgentManager()
        agents = manager.create_agents_for_game(
            "game-1",
            [
                {},
                {},
                {},
            ],
        )
        # 自动分配的性格应该尽量不重复
        personalities = [a.personality for a in agents]
        assert len(set(personalities)) == 3  # 3 个不同的性格

    def test_create_agents_auto_assigns_names(self):
        manager = AgentManager()
        agents = manager.create_agents_for_game("game-1", [{}, {}])
        names = [a.name for a in agents]
        assert len(set(names)) == 2  # 名字不重复
        assert all(name for name in names)  # 名字非空

    def test_get_agent(self):
        manager = AgentManager()
        agents = manager.create_agents_for_game("game-1", [{"name": "找我"}])
        found = manager.get_agent("game-1", agents[0].agent_id)
        assert found is not None
        assert found.name == "找我"

    def test_get_nonexistent_agent(self):
        manager = AgentManager()
        assert manager.get_agent("no-game", "no-agent") is None

    def test_get_agents_for_game(self):
        manager = AgentManager()
        manager.create_agents_for_game("game-1", [{}, {}, {}])
        agents = manager.get_agents_for_game("game-1")
        assert len(agents) == 3

    def test_get_agents_for_nonexistent_game(self):
        manager = AgentManager()
        assert manager.get_agents_for_game("no-game") == []

    def test_remove_agent(self):
        manager = AgentManager()
        agents = manager.create_agents_for_game("game-1", [{}, {}])
        assert manager.remove_agent("game-1", agents[0].agent_id)
        assert manager.get_agent("game-1", agents[0].agent_id) is None
        assert manager.get_agent("game-1", agents[1].agent_id) is not None

    def test_remove_nonexistent_agent(self):
        manager = AgentManager()
        assert not manager.remove_agent("no-game", "no-agent")

    def test_remove_game(self):
        manager = AgentManager()
        manager.create_agents_for_game("game-1", [{}, {}])
        assert manager.remove_game("game-1")
        assert manager.get_agents_for_game("game-1") == []

    def test_remove_nonexistent_game(self):
        manager = AgentManager()
        assert not manager.remove_game("no-game")

    def test_reset_agents_for_game(self):
        manager = AgentManager()
        agents = manager.create_agents_for_game("game-1", [{}])
        agents[0].set_strategy_context("old strategy")
        manager.reset_agents_for_game("game-1")
        assert agents[0].get_strategy_context() == ""

    def test_active_game_count(self):
        manager = AgentManager()
        assert manager.active_game_count == 0
        manager.create_agents_for_game("game-1", [{}])
        manager.create_agents_for_game("game-2", [{}])
        assert manager.active_game_count == 2

    def test_total_agent_count(self):
        manager = AgentManager()
        manager.create_agents_for_game("game-1", [{}, {}])
        manager.create_agents_for_game("game-2", [{}, {}, {}])
        assert manager.total_agent_count == 5

    def test_recreate_game_clears_old_agents(self):
        manager = AgentManager()
        old_agents = manager.create_agents_for_game("game-1", [{}, {}])
        new_agents = manager.create_agents_for_game("game-1", [{}])
        assert len(manager.get_agents_for_game("game-1")) == 1
        assert manager.get_agent("game-1", old_agents[0].agent_id) is None

    def test_invalid_model_fallback(self):
        manager = AgentManager()
        agents = manager.create_agents_for_game(
            "game-1",
            [
                {"model_id": "nonexistent-model"},
            ],
        )
        assert agents[0].model_id == "openai-gpt4o-mini"

    def test_repr(self):
        manager = AgentManager()
        manager.create_agents_for_game("game-1", [{}, {}])
        repr_str = repr(manager)
        assert "games=1" in repr_str
        assert "agents=2" in repr_str


class TestGetAgentManagerSingleton:
    """全局 AgentManager 单例测试"""

    def test_singleton(self):
        # 重置全局状态
        import app.agents.agent_manager as am

        am._global_agent_manager = None

        m1 = get_agent_manager()
        m2 = get_agent_manager()
        assert m1 is m2

        # 清理
        am._global_agent_manager = None


# ============================================================
# 完整决策流程集成测试 (mock LLM)
# ============================================================


class TestDecisionFlow:
    """完整决策流程：build prompt -> call llm -> parse response"""

    @pytest.mark.asyncio
    async def test_full_decision_flow(self):
        agent = BaseAgent(
            name="集成测试Agent",
            model_id="openai-gpt4o-mini",
            personality="analytical",
            personality_description="冷静分析型玩家，善于概率计算",
        )

        # 构建 system prompt
        system_prompt = agent.build_system_prompt()
        assert "集成测试Agent" in system_prompt
        assert "冷静分析型" in system_prompt

        # mock LLM 响应
        llm_response = json.dumps(
            {
                "action": "call",
                "target": None,
                "table_talk": "概率告诉我应该跟",
                "thought": {
                    "hand_evaluation": "一对9，中等牌力",
                    "opponent_analysis": "对手可能在诈唬",
                    "chat_analysis": "对手说很自信，但语气不太对",
                    "risk_assessment": "底池赔率 3:1，值得跟注",
                    "reasoning": "基于贝叶斯分析，跟注期望值为正",
                    "confidence": 0.65,
                    "emotion": "冷静",
                },
            }
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_response

        with patch("app.agents.base_agent.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            # 调用 LLM
            raw = await agent.call_llm(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "请做出决策"},
                ]
            )

            # 解析响应
            available = [GameAction.CALL, GameAction.FOLD, GameAction.RAISE]
            decision = agent.parse_decision_response(raw, available_actions=available)

            assert decision.action == GameAction.CALL
            assert decision.table_talk == "概率告诉我应该跟"
            assert decision.thought.confidence == 0.65
            assert decision.thought.emotion == "冷静"
            assert decision.raw_response == llm_response

            # 记录思考
            agent.record_thought(1, decision.thought)
            assert len(agent.get_round_thoughts(1)) == 1

    @pytest.mark.asyncio
    async def test_decision_flow_with_llm_failure_fallback(self):
        """LLM 调用失败时，应降级为安全操作"""
        agent = BaseAgent(name="失败降级测试")

        with patch("app.agents.base_agent.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("API down")

            with patch("app.agents.base_agent.get_settings") as mock_settings:
                settings = MagicMock()
                settings.llm_temperature = 0.7
                settings.llm_timeout = 5
                settings.llm_max_retries = 1  # 只试 1 次
                settings.openai_api_key = ""
                settings.anthropic_api_key = ""
                settings.google_api_key = ""
                mock_settings.return_value = settings

                # LLM 调用应该抛出 LLMCallError
                with pytest.raises(LLMCallError):
                    await agent.call_llm([{"role": "user", "content": "test"}])

                # 调用方可以 catch 后降级
                available = [GameAction.CALL, GameAction.FOLD]
                fallback = agent._get_fallback_action(available)
                assert fallback == GameAction.CALL
