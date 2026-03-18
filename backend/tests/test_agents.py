"""T2.1 + T2.3 单元测试: BaseAgent + AgentManager + make_decision

测试覆盖:
- BaseAgent 初始化与配置
- System prompt 构建
- LLM 响应解析（JSON 正常解析、容错、降级）
- LLM 调用（mock）
- AgentManager 生命周期管理
- T2.3: make_decision 完整决策流程
- T2.3: 决策上下文格式化函数
- T2.3: 比牌目标验证与自动选择
- T2.3: LLM 失败降级处理
- T2.3: 非法操作降级处理
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
    format_hand_description,
    format_players_status,
    format_action_history,
    format_chat_history,
    format_available_actions,
)
from app.agents.agent_manager import AgentManager, get_agent_manager
from app.models.game import (
    ActionRecord,
    GameAction,
    GameConfig,
    GamePhase,
    GameState,
    Player,
    PlayerStatus,
    PlayerType,
    RoundState,
)
from app.models.card import Card, Rank, Suit


def _make_llm_config(
    temperature: float = 0.7,
    timeout: int = 5,
    max_retries: int = 3,
) -> dict:
    """构造 get_runtime_llm_config 返回值"""
    return {
        "llm_temperature": temperature,
        "llm_timeout": timeout,
        "llm_max_retries": max_retries,
    }


# ============================================================
# BaseAgent 初始化
# ============================================================


class TestBaseAgentInit:
    """BaseAgent 初始化测试"""

    def test_default_init(self):
        agent = BaseAgent()
        assert agent.name == "AI Player"
        assert agent.model_id == "copilot-gpt4o"  # 默认取注册表中第一个模型
        assert agent.agent_id  # 自动生成 UUID

    def test_custom_init(self):
        agent = BaseAgent(
            agent_id="test-id",
            name="测试选手",
            model_id="copilot-claude-sonnet",
        )
        assert agent.agent_id == "test-id"
        assert agent.name == "测试选手"
        assert agent.model_id == "copilot-claude-sonnet"

    def test_invalid_model_id_fallback(self):
        agent = BaseAgent(model_id="nonexistent-model")
        assert agent.model_id == "copilot-gpt4o"  # 回退到注册表第一个模型

    def test_repr(self):
        agent = BaseAgent(name="火焰哥", model_id="copilot-gpt4o-mini")
        repr_str = repr(agent)
        assert "火焰哥" in repr_str
        assert "copilot-gpt4o-mini" in repr_str


# ============================================================
# System Prompt 构建
# ============================================================


class TestBuildSystemPrompt:
    """System prompt 构建测试"""

    def test_contains_agent_identity(self):
        agent = BaseAgent(name="火焰哥")
        prompt = agent.build_system_prompt()
        assert "火焰哥" in prompt

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
    """LLM 调用测试（mock copilot）"""

    @pytest.mark.asyncio
    async def test_successful_call(self):
        agent = BaseAgent(name="LLM测试", model_id="copilot-gpt4o-mini")

        mock_copilot = MagicMock()
        mock_copilot.call_copilot_api = AsyncMock(return_value='{"action": "call", "thought": {}}')

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_copilot):
            result = await agent.call_llm(
                [
                    {"role": "system", "content": "test system prompt"},
                    {"role": "user", "content": "test user prompt"},
                ]
            )

            assert result == '{"action": "call", "thought": {}}'
            mock_copilot.call_copilot_api.assert_called_once()

            # 验证调用参数
            call_kwargs = mock_copilot.call_copilot_api.call_args
            assert call_kwargs.kwargs["model"] == "gpt-4o-mini"
            assert call_kwargs.kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        agent = BaseAgent(name="重试测试", model_id="copilot-gpt4o-mini")

        mock_copilot = MagicMock()
        mock_copilot.call_copilot_api = AsyncMock(
            side_effect=[
                Exception("API error"),
                Exception("Timeout"),
                '{"result": "ok"}',
            ]
        )

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_copilot):
            with patch("app.agents.base_agent.get_settings") as mock_settings:
                settings = MagicMock()
                settings.llm_temperature = 0.7
                settings.llm_timeout = 5
                settings.llm_max_retries = 3
                mock_settings.return_value = settings

                with patch(
                    "app.agents.base_agent.get_runtime_llm_config",
                    return_value=_make_llm_config(max_retries=3),
                ):
                    result = await agent.call_llm([{"role": "user", "content": "test"}])
                    assert result == '{"result": "ok"}'
                    assert mock_copilot.call_copilot_api.call_count == 3

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        agent = BaseAgent(name="失败测试", model_id="copilot-gpt4o-mini")

        mock_copilot = MagicMock()
        mock_copilot.call_copilot_api = AsyncMock(side_effect=Exception("Persistent error"))

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_copilot):
            with patch("app.agents.base_agent.get_settings") as mock_settings:
                settings = MagicMock()
                settings.llm_temperature = 0.7
                settings.llm_timeout = 5
                settings.llm_max_retries = 3
                mock_settings.return_value = settings

                with patch(
                    "app.agents.base_agent.get_runtime_llm_config",
                    return_value=_make_llm_config(max_retries=3),
                ):
                    with pytest.raises(LLMCallError, match="failed after 3 retries"):
                        await agent.call_llm([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_empty_content_raises_error(self):
        """Copilot 返回空内容时，call_copilot_api 应抛出异常触发重试"""
        agent = BaseAgent(name="空内容测试", model_id="copilot-gpt4o-mini")

        mock_copilot = MagicMock()
        # Copilot 路径中，call_copilot_api 返回空字符串也算成功
        # 但如果抛出异常则会重试
        mock_copilot.call_copilot_api = AsyncMock(side_effect=Exception("Empty response"))

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_copilot):
            with patch("app.agents.base_agent.get_settings") as mock_settings:
                settings = MagicMock()
                settings.llm_temperature = 0.7
                settings.llm_timeout = 5
                settings.llm_max_retries = 3
                mock_settings.return_value = settings

                with patch(
                    "app.agents.base_agent.get_runtime_llm_config",
                    return_value=_make_llm_config(max_retries=3),
                ):
                    with pytest.raises(LLMCallError):
                        await agent.call_llm([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_copilot_claude_model_call(self):
        agent = BaseAgent(name="Claude测试", model_id="copilot-claude-sonnet")

        with patch("app.agents.base_agent.get_settings") as mock_settings:
            settings = MagicMock()
            settings.llm_temperature = 0.7
            settings.llm_timeout = 5
            settings.llm_max_retries = 1
            mock_settings.return_value = settings

            mock_copilot = MagicMock()
            mock_copilot.call_copilot_api = AsyncMock(return_value='{"action": "fold"}')

            with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_copilot):
                with patch(
                    "app.agents.base_agent.get_runtime_llm_config",
                    return_value=_make_llm_config(max_retries=1),
                ):
                    result = await agent.call_llm([{"role": "user", "content": "test"}])
                    assert result == '{"action": "fold"}'

                    call_kwargs = mock_copilot.call_copilot_api.call_args
                    assert call_kwargs.kwargs["model"] == "claude-3.5-sonnet"

    @pytest.mark.asyncio
    async def test_copilot_gpt4o_model_call(self):
        agent = BaseAgent(name="GPT4o测试", model_id="copilot-gpt4o")

        with patch("app.agents.base_agent.get_settings") as mock_settings:
            settings = MagicMock()
            settings.llm_temperature = 0.7
            settings.llm_timeout = 5
            settings.llm_max_retries = 1
            mock_settings.return_value = settings

            mock_copilot = MagicMock()
            mock_copilot.call_copilot_api = AsyncMock(return_value='{"action": "raise"}')

            with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_copilot):
                with patch(
                    "app.agents.base_agent.get_runtime_llm_config",
                    return_value=_make_llm_config(max_retries=1),
                ):
                    result = await agent.call_llm([{"role": "user", "content": "test"}])
                    assert result == '{"action": "raise"}'

                    call_kwargs = mock_copilot.call_copilot_api.call_args
                    assert call_kwargs.kwargs["model"] == "gpt-4o"


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
                {"model_id": "copilot-gpt4o-mini"},
                {"model_id": "copilot-claude-sonnet"},
            ],
        )
        assert len(agents) == 2
        assert agents[0].model_id == "copilot-gpt4o-mini"
        assert agents[1].model_id == "copilot-claude-sonnet"

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
        assert agents[0].model_id == "copilot-gpt4o"  # 回退到注册表第一个模型

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
            model_id="copilot-gpt4o-mini",
        )

        # 构建 system prompt
        system_prompt = agent.build_system_prompt()
        assert "集成测试Agent" in system_prompt

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

        mock_copilot = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_copilot):
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

        mock_copilot = MagicMock()
        mock_copilot.call_copilot_api = AsyncMock(side_effect=Exception("API down"))

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_copilot):
            with patch("app.agents.base_agent.get_settings") as mock_settings:
                settings = MagicMock()
                settings.llm_temperature = 0.7
                settings.llm_timeout = 5
                settings.llm_max_retries = 1  # 只试 1 次
                mock_settings.return_value = settings

                with patch(
                    "app.agents.base_agent.get_runtime_llm_config",
                    return_value=_make_llm_config(max_retries=1),
                ):
                    # LLM 调用应该抛出 LLMCallError
                    with pytest.raises(LLMCallError):
                        await agent.call_llm([{"role": "user", "content": "test"}])

                # 调用方可以 catch 后降级
                available = [GameAction.CALL, GameAction.FOLD]
                fallback = agent._get_fallback_action(available)
                assert fallback == GameAction.CALL


# ============================================================
# T2.3: 决策上下文格式化函数
# ============================================================


def _make_card(suit: Suit, rank: Rank) -> Card:
    """快速创建一张牌"""
    return Card(suit=suit, rank=rank)


def _make_player(
    name: str,
    player_id: str = "",
    chips: int = 1000,
    status: PlayerStatus = PlayerStatus.ACTIVE_BLIND,
    player_type: PlayerType = PlayerType.AI,
    hand: list[Card] | None = None,
    total_bet: int = 10,
) -> Player:
    """快速创建一个玩家"""
    return Player(
        id=player_id or f"player-{name}",
        name=name,
        player_type=player_type,
        chips=chips,
        status=status,
        hand=hand,
        total_bet_this_round=total_bet,
    )


def _make_game_state(
    players: list[Player] | None = None,
    round_number: int = 1,
    pot: int = 30,
    current_bet: int = 10,
    current_player_index: int = 0,
    phase: GamePhase = GamePhase.BETTING,
    actions: list[ActionRecord] | None = None,
) -> GameState:
    """快速创建一个游戏状态"""
    if players is None:
        hand_p1 = [
            _make_card(Suit.HEARTS, Rank.KING),
            _make_card(Suit.SPADES, Rank.KING),
            _make_card(Suit.DIAMONDS, Rank.THREE),
        ]
        hand_p2 = [
            _make_card(Suit.CLUBS, Rank.ACE),
            _make_card(Suit.HEARTS, Rank.ACE),
            _make_card(Suit.SPADES, Rank.SEVEN),
        ]
        hand_p3 = [
            _make_card(Suit.DIAMONDS, Rank.FIVE),
            _make_card(Suit.CLUBS, Rank.SIX),
            _make_card(Suit.HEARTS, Rank.SEVEN),
        ]
        players = [
            _make_player("玩家A", "p1", hand=hand_p1, status=PlayerStatus.ACTIVE_SEEN),
            _make_player("玩家B", "p2", hand=hand_p2),
            _make_player("玩家C", "p3", hand=hand_p3),
        ]

    round_state = RoundState(
        round_number=round_number,
        pot=pot,
        current_bet=current_bet,
        dealer_index=0,
        current_player_index=current_player_index,
        phase=phase,
        actions=actions or [],
    )

    return GameState(
        game_id="test-game",
        players=players,
        current_round=round_state,
        config=GameConfig(),
        status="playing",
    )


class TestFormatHandDescription:
    """手牌描述格式化测试"""

    def test_seen_hand_with_pair(self):
        hand = [
            _make_card(Suit.HEARTS, Rank.KING),
            _make_card(Suit.SPADES, Rank.KING),
            _make_card(Suit.DIAMONDS, Rank.THREE),
        ]
        desc = format_hand_description(hand, has_seen=True)
        assert "红心K" in desc
        assert "黑桃K" in desc
        assert "方块3" in desc
        assert "对K" in desc

    def test_seen_hand_with_straight(self):
        hand = [
            _make_card(Suit.HEARTS, Rank.FIVE),
            _make_card(Suit.SPADES, Rank.SIX),
            _make_card(Suit.DIAMONDS, Rank.SEVEN),
        ]
        desc = format_hand_description(hand, has_seen=True)
        assert "顺子" in desc

    def test_unseen_hand(self):
        hand = [
            _make_card(Suit.HEARTS, Rank.ACE),
            _make_card(Suit.SPADES, Rank.KING),
            _make_card(Suit.DIAMONDS, Rank.QUEEN),
        ]
        desc = format_hand_description(hand, has_seen=False)
        assert "未知" in desc
        assert "还没有看牌" in desc

    def test_none_hand(self):
        desc = format_hand_description(None, has_seen=False)
        assert "未知" in desc
        assert "未发牌" in desc


class TestFormatPlayersStatus:
    """玩家状态格式化测试"""

    def test_basic_status(self):
        players = [
            _make_player("玩家A", "p1", status=PlayerStatus.ACTIVE_SEEN),
            _make_player("玩家B", "p2", status=PlayerStatus.ACTIVE_BLIND),
            _make_player("玩家C", "p3", status=PlayerStatus.FOLDED),
        ]
        round_state = RoundState(round_number=1, current_player_index=0)
        text = format_players_status(players, "p1", round_state)
        assert "玩家A（你）" in text
        assert "明注（已看牌）" in text
        assert "暗注（未看牌）" in text
        assert "已弃牌" in text
        assert "当前行动" in text

    def test_out_status(self):
        players = [
            _make_player("玩家A", "p1"),
            _make_player("玩家D", "p4", status=PlayerStatus.OUT, chips=0),
        ]
        round_state = RoundState(round_number=1, current_player_index=0)
        text = format_players_status(players, "p1", round_state)
        assert "已出局" in text


class TestFormatActionHistory:
    """行动历史格式化测试"""

    def test_empty_history(self):
        text = format_action_history([])
        assert "尚无行动记录" in text

    def test_with_actions(self):
        actions = [
            ActionRecord(player_id="p1", player_name="玩家A", action=GameAction.CALL, amount=10),
            ActionRecord(player_id="p2", player_name="玩家B", action=GameAction.RAISE, amount=20),
            ActionRecord(player_id="p3", player_name="玩家C", action=GameAction.FOLD),
        ]
        text = format_action_history(actions)
        assert "玩家A" in text
        assert "跟注" in text
        assert "10 筹码" in text
        assert "玩家B" in text
        assert "加注" in text
        assert "20 筹码" in text
        assert "玩家C" in text
        assert "弃牌" in text

    def test_compare_action_with_target(self):
        actions = [
            ActionRecord(
                player_id="p1",
                player_name="玩家A",
                action=GameAction.COMPARE,
                amount=20,
                target_id="p2",
            ),
        ]
        text = format_action_history(actions)
        assert "比牌" in text
        assert "p2" in text


class TestFormatChatHistory:
    """聊天记录格式化测试"""

    def test_empty_chat(self):
        text = format_chat_history(None)
        assert "暂无聊天记录" in text

    def test_empty_list(self):
        text = format_chat_history([])
        assert "暂无聊天记录" in text

    def test_with_messages(self):
        chat = [
            {"sender": "玩家A", "message": "我牌很好"},
            {"sender": "玩家B", "message": "别吹了"},
        ]
        text = format_chat_history(chat)
        assert "玩家A: 我牌很好" in text
        assert "玩家B: 别吹了" in text


class TestFormatAvailableActions:
    """可用操作格式化测试"""

    def test_blind_player_actions(self):
        player = _make_player("玩家A", "p1", status=PlayerStatus.ACTIVE_BLIND)
        round_state = RoundState(round_number=1, current_bet=10)
        actions = [GameAction.FOLD, GameAction.CALL, GameAction.CHECK_CARDS, GameAction.RAISE]
        text = format_available_actions(actions, round_state, player, [player])
        assert "弃牌" in text
        assert "跟注" in text
        assert "看牌" in text
        assert "加注" in text
        assert "无费用" in text
        assert "费用:" in text

    def test_seen_player_with_compare(self):
        player = _make_player("玩家A", "p1", status=PlayerStatus.ACTIVE_SEEN, chips=500)
        opponent = _make_player("玩家B", "p2", status=PlayerStatus.ACTIVE_BLIND)
        round_state = RoundState(round_number=1, current_bet=10)
        actions = [GameAction.FOLD, GameAction.CALL, GameAction.RAISE, GameAction.COMPARE]
        text = format_available_actions(actions, round_state, player, [player, opponent])
        assert "比牌" in text
        assert "可比对象" in text
        assert "玩家B" in text


# ============================================================
# T2.3: make_decision 完整决策流程测试
# ============================================================


def _mock_llm_response(
    action: str = "call",
    target: str | None = None,
    table_talk: str | None = None,
    thought: dict | None = None,
) -> str:
    """生成 mock LLM 响应 JSON"""
    return json.dumps(
        {
            "action": action,
            "target": target,
            "table_talk": table_talk,
            "thought": thought
            or {
                "hand_evaluation": "中等牌力",
                "opponent_analysis": "对手行为正常",
                "reasoning": "跟注是合理的",
                "confidence": 0.6,
                "emotion": "平静",
            },
        }
    )


def _patch_llm(response_content: str):
    """创建 mock LLM 的 patch context（已弃用，保留兼容）"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = response_content
    return mock_response


def _mock_copilot(response_content: str):
    """创建 mock Copilot auth 对象

    Copilot 模型通过 _call_copilot -> copilot.call_copilot_api 调用，
    call_copilot_api 直接返回字符串内容（不是 response 对象）。
    """
    mock = MagicMock()
    mock.call_copilot_api = AsyncMock(return_value=response_content)
    return mock


class TestMakeDecision:
    """T2.3: make_decision 完整流程测试"""

    @pytest.mark.asyncio
    async def test_make_decision_call(self):
        """正常决策流程：AI 选择跟注"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        llm_response = _mock_llm_response(
            action="call",
            table_talk="概率分析后跟注",
            thought={
                "hand_evaluation": "一对K，牌力不错",
                "opponent_analysis": "玩家B可能在诈唬",
                "reasoning": "底池赔率划算",
                "confidence": 0.7,
                "emotion": "冷静",
            },
        )
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)

            assert decision.action == GameAction.CALL
            assert decision.table_talk == "概率分析后跟注"
            assert decision.thought is not None
            assert decision.thought.confidence == 0.7
            assert decision.thought.emotion == "冷静"

            # 验证思考数据已记录
            thoughts = agent.get_round_thoughts(1)
            assert len(thoughts) == 1
            assert thoughts[0].hand_evaluation == "一对K，牌力不错"

    @pytest.mark.asyncio
    async def test_make_decision_fold(self):
        """AI 选择弃牌"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        llm_response = _mock_llm_response(action="fold", table_talk=None)
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)
            assert decision.action == GameAction.FOLD
            assert decision.table_talk is None

    @pytest.mark.asyncio
    async def test_make_decision_raise(self):
        """AI 选择加注"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        llm_response = _mock_llm_response(
            action="raise",
            table_talk="你确定要跟？",
        )
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)
            assert decision.action == GameAction.RAISE
            assert decision.table_talk == "你确定要跟？"

    @pytest.mark.asyncio
    async def test_make_decision_check_cards_blind(self):
        """暗注玩家选择看牌"""
        agent = BaseAgent(agent_id="p2", name="玩家B")
        game = _make_game_state(current_player_index=1)
        player = game.players[1]
        player.status = PlayerStatus.ACTIVE_BLIND

        llm_response = _mock_llm_response(action="check_cards")
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)
            assert decision.action == GameAction.CHECK_CARDS

    @pytest.mark.asyncio
    async def test_make_decision_compare_with_valid_target(self):
        """AI 选择比牌，指定合法目标"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        llm_response = _mock_llm_response(
            action="compare",
            target="p2",
            table_talk="来比一比！",
        )
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)
            assert decision.action == GameAction.COMPARE
            assert decision.target == "p2"

    @pytest.mark.asyncio
    async def test_make_decision_compare_auto_select_target(self):
        """AI 选择比牌但未指定目标，自动选择筹码最少的对手"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        players = [
            _make_player(
                "玩家A",
                "p1",
                chips=800,
                status=PlayerStatus.ACTIVE_SEEN,
                hand=[
                    _make_card(Suit.HEARTS, Rank.KING),
                    _make_card(Suit.SPADES, Rank.KING),
                    _make_card(Suit.DIAMONDS, Rank.THREE),
                ],
            ),
            _make_player(
                "玩家B",
                "p2",
                chips=500,
                hand=[
                    _make_card(Suit.CLUBS, Rank.ACE),
                    _make_card(Suit.HEARTS, Rank.ACE),
                    _make_card(Suit.SPADES, Rank.SEVEN),
                ],
            ),
            _make_player(
                "玩家C",
                "p3",
                chips=200,
                hand=[
                    _make_card(Suit.DIAMONDS, Rank.FIVE),
                    _make_card(Suit.CLUBS, Rank.SIX),
                    _make_card(Suit.HEARTS, Rank.SEVEN),
                ],
            ),
        ]
        game = _make_game_state(players=players)

        llm_response = _mock_llm_response(action="compare", target=None)
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, players[0])
            assert decision.action == GameAction.COMPARE
            # 应自动选择筹码最少的玩家C
            assert decision.target == "p3"

    @pytest.mark.asyncio
    async def test_make_decision_compare_invalid_target_auto_select(self):
        """AI 比牌指定了无效目标，自动重选"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        # 指定一个不存在的目标
        llm_response = _mock_llm_response(action="compare", target="nonexistent-id")
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)
            assert decision.action == GameAction.COMPARE
            # 应自动选择一个合法目标
            assert decision.target in ["p2", "p3"]

    @pytest.mark.asyncio
    async def test_make_decision_compare_target_folded_auto_select(self):
        """AI 比牌指定了已弃牌的目标，自动重选"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        players = [
            _make_player(
                "玩家A",
                "p1",
                status=PlayerStatus.ACTIVE_SEEN,
                hand=[
                    _make_card(Suit.HEARTS, Rank.KING),
                    _make_card(Suit.SPADES, Rank.KING),
                    _make_card(Suit.DIAMONDS, Rank.THREE),
                ],
            ),
            _make_player(
                "玩家B",
                "p2",
                status=PlayerStatus.FOLDED,
                hand=[
                    _make_card(Suit.CLUBS, Rank.ACE),
                    _make_card(Suit.HEARTS, Rank.ACE),
                    _make_card(Suit.SPADES, Rank.SEVEN),
                ],
            ),
            _make_player(
                "玩家C",
                "p3",
                status=PlayerStatus.ACTIVE_BLIND,
                hand=[
                    _make_card(Suit.DIAMONDS, Rank.FIVE),
                    _make_card(Suit.CLUBS, Rank.SIX),
                    _make_card(Suit.HEARTS, Rank.SEVEN),
                ],
            ),
        ]
        game = _make_game_state(players=players)

        llm_response = _mock_llm_response(action="compare", target="p2")
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, players[0])
            assert decision.action == GameAction.COMPARE
            # p2 已弃牌，应自动选择 p3
            assert decision.target == "p3"


class TestMakeDecisionIllegalActionFallback:
    """T2.3: 非法操作降级测试"""

    @pytest.mark.asyncio
    async def test_illegal_action_fallback_to_call(self):
        """LLM 返回不在可用列表中的操作，降级为跟注"""
        agent = BaseAgent(agent_id="p2", name="玩家B")
        game = _make_game_state(current_player_index=1)
        player = game.players[1]
        player.status = PlayerStatus.ACTIVE_BLIND

        # LLM 返回 compare，但暗注玩家不能比牌
        llm_response = _mock_llm_response(action="compare", target="p1")
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)
            # compare 不在暗注玩家的可用操作中，应降级
            assert decision.action != GameAction.COMPARE
            assert decision.action in [
                GameAction.CALL,
                GameAction.FOLD,
                GameAction.CHECK_CARDS,
                GameAction.RAISE,
            ]

    @pytest.mark.asyncio
    async def test_illegal_check_cards_when_already_seen(self):
        """已看牌玩家不能再次看牌"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        llm_response = _mock_llm_response(action="check_cards")
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)
            assert decision.action != GameAction.CHECK_CARDS


class TestMakeDecisionLLMFailure:
    """T2.3: LLM 调用失败降级测试"""

    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self):
        """LLM 调用失败时降级为安全操作"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        mock_cop = MagicMock()
        mock_cop.call_copilot_api = AsyncMock(side_effect=Exception("API down"))

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            with patch("app.agents.base_agent.get_settings") as mock_settings:
                settings = MagicMock()
                settings.llm_temperature = 0.7
                settings.llm_timeout = 5
                settings.llm_max_retries = 1
                mock_settings.return_value = settings

                with patch(
                    "app.agents.base_agent.get_runtime_llm_config",
                    return_value=_make_llm_config(max_retries=1),
                ):
                    decision = await agent.make_decision(game, player)

                    # 应降级为 CALL（最安全的操作）
                    assert decision.action == GameAction.CALL
                    assert decision.thought is not None
                    assert (
                        "失败" in decision.thought.reasoning or "降级" in decision.thought.reasoning
                    )
                    assert decision.thought.confidence == 0.0

    @pytest.mark.asyncio
    async def test_llm_failure_fallback_fold_when_no_call(self):
        """LLM 失败且筹码不足跟注时，降级为弃牌"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        players = [
            _make_player(
                "玩家A",
                "p1",
                chips=0,
                status=PlayerStatus.ACTIVE_SEEN,
                hand=[
                    _make_card(Suit.HEARTS, Rank.KING),
                    _make_card(Suit.SPADES, Rank.KING),
                    _make_card(Suit.DIAMONDS, Rank.THREE),
                ],
            ),
            _make_player(
                "玩家B",
                "p2",
                chips=500,
                hand=[
                    _make_card(Suit.CLUBS, Rank.ACE),
                    _make_card(Suit.HEARTS, Rank.ACE),
                    _make_card(Suit.SPADES, Rank.SEVEN),
                ],
            ),
        ]
        game = _make_game_state(players=players)

        mock_cop = MagicMock()
        mock_cop.call_copilot_api = AsyncMock(side_effect=Exception("API down"))

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            with patch("app.agents.base_agent.get_settings") as mock_settings:
                settings = MagicMock()
                settings.llm_temperature = 0.7
                settings.llm_timeout = 5
                settings.llm_max_retries = 1
                mock_settings.return_value = settings

                with patch(
                    "app.agents.base_agent.get_runtime_llm_config",
                    return_value=_make_llm_config(max_retries=1),
                ):
                    decision = await agent.make_decision(game, players[0])
                    assert decision.action == GameAction.FOLD


class TestMakeDecisionWithContext:
    """T2.3: make_decision 上下文注入测试"""

    @pytest.mark.asyncio
    async def test_chat_context_included_in_prompt(self):
        """验证聊天上下文被传入 LLM"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        chat_context = [
            {"sender": "玩家B", "message": "我牌超好的！"},
            {"sender": "玩家C", "message": "别信他"},
        ]

        llm_response = _mock_llm_response(action="call")
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player, chat_context=chat_context)
            assert decision.action == GameAction.CALL

            # 验证 LLM 被调用，且 messages 包含聊天上下文
            call_args = mock_cop.call_copilot_api.call_args
            messages = call_args.kwargs["messages"]
            user_prompt = messages[1]["content"]
            assert "我牌超好的" in user_prompt
            assert "别信他" in user_prompt

    @pytest.mark.asyncio
    async def test_experience_context_included_in_prompt(self):
        """验证经验策略上下文被传入 LLM"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        agent.set_strategy_context("对手B喜欢诈唬，应该更多跟注")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        llm_response = _mock_llm_response(action="call")
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)

            call_args = mock_cop.call_copilot_api.call_args
            messages = call_args.kwargs["messages"]
            user_prompt = messages[1]["content"]
            assert "对手B喜欢诈唬" in user_prompt

    @pytest.mark.asyncio
    async def test_action_history_included_in_prompt(self):
        """验证行动历史被传入 LLM"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        actions = [
            ActionRecord(player_id="p2", player_name="玩家B", action=GameAction.RAISE, amount=20),
            ActionRecord(player_id="p3", player_name="玩家C", action=GameAction.FOLD),
        ]
        game = _make_game_state(actions=actions)
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        llm_response = _mock_llm_response(action="call")
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)

            call_args = mock_cop.call_copilot_api.call_args
            messages = call_args.kwargs["messages"]
            user_prompt = messages[1]["content"]
            assert "玩家B" in user_prompt
            assert "加注" in user_prompt
            assert "玩家C" in user_prompt
            assert "弃牌" in user_prompt

    @pytest.mark.asyncio
    async def test_blind_player_hand_not_revealed(self):
        """暗注玩家的手牌描述应为'未知'"""
        agent = BaseAgent(agent_id="p2", name="玩家B")
        game = _make_game_state(current_player_index=1)
        player = game.players[1]
        player.status = PlayerStatus.ACTIVE_BLIND

        llm_response = _mock_llm_response(action="call")
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)

            call_args = mock_cop.call_copilot_api.call_args
            messages = call_args.kwargs["messages"]
            user_prompt = messages[1]["content"]
            assert "未知" in user_prompt
            assert "还没有看牌" in user_prompt

    @pytest.mark.asyncio
    async def test_available_actions_with_costs_in_prompt(self):
        """验证可用操作及费用信息被传入 LLM"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        llm_response = _mock_llm_response(action="call")
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)

            call_args = mock_cop.call_copilot_api.call_args
            messages = call_args.kwargs["messages"]
            user_prompt = messages[1]["content"]
            # 明注跟注费用 = current_bet * 2 = 20
            assert "费用" in user_prompt
            assert "筹码" in user_prompt


class TestMakeDecisionThoughtRecording:
    """T2.3: 思考数据记录测试"""

    @pytest.mark.asyncio
    async def test_thought_recorded_after_decision(self):
        """决策后思考数据应被记录到 memory"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        llm_response = _mock_llm_response(
            action="call",
            thought={
                "hand_evaluation": "一对K，中上牌力",
                "opponent_analysis": "对手B加注频率高",
                "reasoning": "值得跟注",
                "confidence": 0.75,
                "emotion": "自信",
            },
        )
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)

            # 检查思考数据已被记录
            thoughts = agent.get_round_thoughts(1)
            assert len(thoughts) == 1
            assert thoughts[0].hand_evaluation == "一对K，中上牌力"
            assert thoughts[0].confidence == 0.75

    @pytest.mark.asyncio
    async def test_multiple_decisions_accumulate_thoughts(self):
        """同一局多次决策应累积思考数据"""
        agent = BaseAgent(agent_id="p1", name="玩家A")

        for i in range(3):
            game = _make_game_state()
            player = game.players[0]
            player.status = PlayerStatus.ACTIVE_SEEN

            llm_response = _mock_llm_response(
                action="call",
                thought={"reasoning": f"第{i + 1}次决策", "confidence": 0.5 + i * 0.1},
            )
            mock_cop = _mock_copilot(llm_response)

            with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
                await agent.make_decision(game, player)

        thoughts = agent.get_round_thoughts(1)
        assert len(thoughts) == 3
        assert thoughts[0].reasoning == "第1次决策"
        assert thoughts[2].reasoning == "第3次决策"

    @pytest.mark.asyncio
    async def test_llm_failure_still_records_thought(self):
        """LLM 失败时降级决策也应记录思考"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        mock_cop = MagicMock()
        mock_cop.call_copilot_api = AsyncMock(side_effect=Exception("API down"))

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            with patch("app.agents.base_agent.get_settings") as mock_settings:
                settings = MagicMock()
                settings.llm_temperature = 0.7
                settings.llm_timeout = 5
                settings.llm_max_retries = 1
                settings.siliconflow_api_key = ""
                settings.azure_openai_api_key = ""
                mock_settings.return_value = settings

                with patch(
                    "app.agents.base_agent.get_runtime_llm_config",
                    return_value=_make_llm_config(max_retries=1),
                ):
                    decision = await agent.make_decision(game, player)

                    thoughts = agent.get_round_thoughts(1)
                    assert len(thoughts) == 1
                    assert thoughts[0].confidence == 0.0


class TestMakeDecisionEdgeCases:
    """T2.3: make_decision 边界情况测试"""

    @pytest.mark.asyncio
    async def test_chinese_action_in_llm_response(self):
        """LLM 返回中文操作名称"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        llm_response = json.dumps(
            {
                "action": "跟注",
                "thought": {"reasoning": "跟注比较安全"},
            }
        )
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)
            assert decision.action == GameAction.CALL

    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """LLM 返回格式不规范的 JSON（包含在文本中）"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        # JSON 嵌套在文本中
        llm_response = (
            '我决定 ```json\n{"action": "raise", "thought": {"reasoning": "感觉不错"}}\n``` 就这样'
        )
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)
            assert decision.action == GameAction.RAISE

    @pytest.mark.asyncio
    async def test_completely_unparseable_response(self):
        """LLM 返回完全无法解析的响应"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = _make_game_state()
        player = game.players[0]
        player.status = PlayerStatus.ACTIVE_SEEN

        llm_response = "这是一段完全无关的文字，没有任何有用信息。天气真好。"
        mock_cop = _mock_copilot(llm_response)

        with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_cop):
            decision = await agent.make_decision(game, player)
            # 应降级到安全操作
            assert decision.action in [GameAction.CALL, GameAction.FOLD]

    @pytest.mark.asyncio
    async def test_no_round_state_raises(self):
        """没有 current_round 时应该 assert 失败"""
        agent = BaseAgent(agent_id="p1", name="玩家A")
        game = GameState(game_id="test", players=[], status="waiting")
        player = _make_player("玩家A", "p1")

        with pytest.raises(AssertionError):
            await agent.make_decision(game, player)
