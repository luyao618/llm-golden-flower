"""LLM 集成测试 — 真实 API 调用（智谱 GLM）

需要设置环境变量 ZHIPU_API_KEY 并使用 pytest -m integration 运行。
使用 glm-4-flash（免费模型）以降低测试成本。

覆盖 5 个 LLM 调用路径:
1. BaseAgent.call_llm — 基础连通性
2. BaseAgent.make_decision — AI 决策
3. ChatEngine.maybe_react_as_bystander — 旁观者聊天反应
4. ExperienceReviewer.perform_review — 经验回顾
5. ThoughtReporter.generate_round_narrative / generate_game_summary — 叙事生成
"""

from __future__ import annotations

import json
import os

import pytest

from app.agents.base_agent import BaseAgent, Decision, LLMCallError
from app.agents.chat_engine import ChatEngine, TriggerEvent, TriggerEventType
from app.agents.experience import ExperienceReviewer
from app.config import add_zhipu_model, remove_zhipu_model
from app.models.card import Card, Rank, Suit
from app.models.chat import ChatContext
from app.models.game import (
    GameAction,
    GameConfig,
    GamePhase,
    GameState,
    Player,
    PlayerStatus,
    PlayerType,
    RoundResult,
    RoundState,
)
from app.models.thought import ReviewTrigger, RoundNarrative, ThoughtRecord
from app.thought.reporter import ThoughtReporter

# ============================================================
# 标记：所有测试都是 integration
# ============================================================

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# 测试用模型
ZHIPU_TEST_MODEL = "glm-4-flash"
ZHIPU_TEST_MODEL_ID = "zhipu-glm-4-flash"
ZHIPU_TEST_DISPLAY_NAME = "GLM-4 Flash"


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(autouse=True)
def setup_zhipu_provider():
    """注册智谱模型

    测试结束后清理注册的模型。
    API Key 通过 agent.set_api_keys() 在 zhipu_agent fixture 中设置。
    """
    api_key = os.environ.get("ZHIPU_API_KEY", "")
    if not api_key:
        pytest.skip("ZHIPU_API_KEY 环境变量未设置")

    # 注册模型
    model_id = add_zhipu_model(ZHIPU_TEST_MODEL, ZHIPU_TEST_DISPLAY_NAME)
    assert model_id == ZHIPU_TEST_MODEL_ID

    yield

    # 清理模型注册
    remove_zhipu_model(ZHIPU_TEST_MODEL_ID)


@pytest.fixture
def zhipu_agent() -> BaseAgent:
    """创建使用智谱模型的 Agent"""
    api_key = os.environ.get("ZHIPU_API_KEY", "")
    agent = BaseAgent(
        agent_id="test-agent-zhipu",
        name="测试选手",
        model_id=ZHIPU_TEST_MODEL_ID,
    )
    agent.set_api_keys({"zhipu": api_key})
    return agent


@pytest.fixture
def game_state_for_decision() -> GameState:
    """创建适合决策测试的游戏状态

    3 人局：当前玩家（已看牌，一对K），2 个对手
    """
    hand_self = [
        Card(suit=Suit.HEARTS, rank=Rank.KING),
        Card(suit=Suit.SPADES, rank=Rank.KING),
        Card(suit=Suit.DIAMONDS, rank=Rank.THREE),
    ]
    hand_p2 = [
        Card(suit=Suit.CLUBS, rank=Rank.ACE),
        Card(suit=Suit.HEARTS, rank=Rank.ACE),
        Card(suit=Suit.SPADES, rank=Rank.SEVEN),
    ]
    hand_p3 = [
        Card(suit=Suit.DIAMONDS, rank=Rank.FIVE),
        Card(suit=Suit.CLUBS, rank=Rank.SIX),
        Card(suit=Suit.HEARTS, rank=Rank.SEVEN),
    ]

    players = [
        Player(
            id="test-agent-zhipu",
            name="测试选手",
            player_type=PlayerType.AI,
            chips=900,
            status=PlayerStatus.ACTIVE_SEEN,
            hand=hand_self,
            total_bet_this_round=10,
        ),
        Player(
            id="opponent-1",
            name="对手A",
            player_type=PlayerType.AI,
            chips=1000,
            status=PlayerStatus.ACTIVE_BLIND,
            hand=hand_p2,
            total_bet_this_round=10,
        ),
        Player(
            id="opponent-2",
            name="对手B",
            player_type=PlayerType.AI,
            chips=800,
            status=PlayerStatus.ACTIVE_BLIND,
            hand=hand_p3,
            total_bet_this_round=10,
        ),
    ]

    round_state = RoundState(
        round_number=1,
        pot=30,
        current_bet=10,
        dealer_index=0,
        current_player_index=0,
        phase=GamePhase.BETTING,
        actions=[],
    )

    return GameState(
        game_id="integration-test-game",
        players=players,
        current_round=round_state,
        config=GameConfig(),
        status="playing",
    )


# ============================================================
# 2.1 LLM 连通性测试
# ============================================================


class TestLLMConnectivity:
    """验证智谱 API 的基础连通性"""

    async def test_simple_completion(self, zhipu_agent: BaseAgent):
        """最简单的 LLM 调用：发送问候，期望非空响应"""
        messages = [
            {"role": "system", "content": "你是一个简洁的助手。"},
            {"role": "user", "content": "请用一句话回答：1+1等于几？"},
        ]

        response = await zhipu_agent.call_llm(
            messages,
            temperature=0.1,
            response_format={"type": "text"},
            max_tokens_override=64,
        )

        assert response is not None
        assert len(response.strip()) > 0
        # 验证回答包含 "2"
        assert "2" in response

    async def test_json_mode_completion(self, zhipu_agent: BaseAgent):
        """验证 JSON 模式输出"""
        messages = [
            {"role": "system", "content": "你是一个只输出 JSON 的助手。"},
            {
                "role": "user",
                "content": (
                    '请以 JSON 格式回答：{"answer": 数字} 的形式回答 1+1 等于几。'
                    "只输出 JSON，不要任何其他文字。"
                ),
            },
        ]

        response = await zhipu_agent.call_llm(
            messages,
            temperature=0.1,
            response_format={"type": "json_object"},
            max_tokens_override=64,
        )

        assert response is not None
        parsed = json.loads(response)
        assert "answer" in parsed
        assert parsed["answer"] == 2

    async def test_chinese_understanding(self, zhipu_agent: BaseAgent):
        """验证中文理解能力（炸金花规则相关）"""
        messages = [
            {"role": "system", "content": "你是一个炸金花专家。请用 JSON 格式回答。"},
            {
                "role": "user",
                "content": (
                    "在炸金花中，以下哪个牌型最大？"
                    "A: 对子  B: 同花顺  C: 顺子"
                    '\n请回答 JSON 格式：{"answer": "A或B或C", "reason": "理由"}'
                ),
            },
        ]

        response = await zhipu_agent.call_llm(
            messages,
            temperature=0.1,
            response_format={"type": "json_object"},
            max_tokens_override=128,
        )

        parsed = json.loads(response)
        assert parsed["answer"] == "B"

    async def test_invalid_model_raises_error(self):
        """使用无效模型 ID 应抛出 LLMCallError"""
        # 注册一个指向不存在模型的配置
        from app.config import ALL_MODELS
        from app.config import ZHIPU_MODELS as _ZHIPU_MODELS

        bad_model_id = "zhipu-nonexistent-model"
        _ZHIPU_MODELS[bad_model_id] = {
            "model": "openai/nonexistent-model-xyz",
            "display_name": "Bad Model",
            "provider": "zhipu",
            "zhipu_id": "nonexistent-model-xyz",
        }
        ALL_MODELS[bad_model_id] = _ZHIPU_MODELS[bad_model_id]

        try:
            agent = BaseAgent(
                agent_id="bad-agent",
                name="Bad Agent",
                model_id=bad_model_id,
            )
            api_key = os.environ.get("ZHIPU_API_KEY", "")
            agent.set_api_keys({"zhipu": api_key})

            with pytest.raises(LLMCallError):
                await agent.call_llm(
                    [{"role": "user", "content": "hello"}],
                    max_tokens_override=16,
                )
        finally:
            _ZHIPU_MODELS.pop(bad_model_id, None)
            ALL_MODELS.pop(bad_model_id, None)


# ============================================================
# 2.2 AI Agent 决策测试
# ============================================================


class TestAgentDecision:
    """验证 make_decision 的真实 LLM 决策"""

    async def test_make_decision_returns_valid_action(
        self,
        zhipu_agent: BaseAgent,
        game_state_for_decision: GameState,
    ):
        """make_decision 应返回合法的 Decision 对象"""
        player = game_state_for_decision.players[0]

        decision = await zhipu_agent.make_decision(
            game=game_state_for_decision,
            player=player,
        )

        # 基本类型检查
        assert isinstance(decision, Decision)
        assert isinstance(decision.action, GameAction)

        # 操作必须是合法的
        valid_actions = {
            GameAction.FOLD,
            GameAction.CALL,
            GameAction.RAISE,
            GameAction.COMPARE,
            # CHECK_CARDS 不可用（已看牌）
        }
        assert decision.action in valid_actions

        # 比牌操作必须有目标
        if decision.action == GameAction.COMPARE:
            assert decision.target is not None
            assert decision.target in ("opponent-1", "opponent-2")

    async def test_decision_includes_thought_data(
        self,
        zhipu_agent: BaseAgent,
        game_state_for_decision: GameState,
    ):
        """决策应包含结构化的思考数据"""
        player = game_state_for_decision.players[0]

        decision = await zhipu_agent.make_decision(
            game=game_state_for_decision,
            player=player,
        )

        # 非降级决策应包含思考数据
        if not decision.is_fallback:
            assert decision.thought is not None
            assert decision.thought.reasoning != ""
            assert 0.0 <= decision.thought.confidence <= 1.0
            assert decision.thought.emotion != ""

    async def test_decision_with_chat_context(
        self,
        zhipu_agent: BaseAgent,
        game_state_for_decision: GameState,
    ):
        """带聊天上下文的决策"""
        player = game_state_for_decision.players[0]
        chat_context = [
            {"sender": "对手A", "message": "这局我手气好得很！"},
            {"sender": "对手B", "message": "别吹了，看看谁笑到最后。"},
        ]

        decision = await zhipu_agent.make_decision(
            game=game_state_for_decision,
            player=player,
            chat_context=chat_context,
        )

        assert isinstance(decision, Decision)
        assert isinstance(decision.action, GameAction)

    async def test_multiple_decisions_consistency(
        self,
        zhipu_agent: BaseAgent,
        game_state_for_decision: GameState,
    ):
        """连续多次决策都应返回合法操作（稳定性验证）"""
        player = game_state_for_decision.players[0]

        results = []
        for _ in range(3):
            decision = await zhipu_agent.make_decision(
                game=game_state_for_decision,
                player=player,
            )
            results.append(decision)

        for decision in results:
            assert isinstance(decision.action, GameAction)
            assert decision.action != GameAction.CHECK_CARDS  # 已看牌不能再看


# ============================================================
# 2.3 聊天引擎旁观者反应测试
# ============================================================


class TestChatEngineBystander:
    """验证 ChatEngine.maybe_react_as_bystander 的真实 LLM 反应"""

    async def test_bystander_reaction_to_raise(self, zhipu_agent: BaseAgent):
        """旁观者对加注事件的反应"""
        engine = ChatEngine()
        chat_ctx = ChatContext()

        event = TriggerEvent(
            event_type=TriggerEventType.RAISE,
            actor_id="opponent-1",
            actor_name="对手A",
            description="对手A 加注到 40 筹码",
            details={"amount": 40, "current_bet": 20},
        )

        agent_state = {
            "chips": 900,
            "actions_summary": "本局尚未操作",
            "hand_description": "未知（你还没有看牌）",
            "pot": 60,
            "current_bet": 40,
            "players_status": "对手A: 筹码960, 明注\n对手B: 筹码1000, 暗注",
        }

        reaction = await engine.maybe_react_as_bystander(
            trigger_event=event,
            agent=zhipu_agent,
            chat_context=chat_ctx,
            agent_state=agent_state,
        )

        # 反应可以为 None（LLM 选择不回应）或 BystanderReaction
        if reaction is not None:
            assert reaction.agent_id == zhipu_agent.agent_id
            assert reaction.agent_name == zhipu_agent.name
            # should_respond 是布尔值
            assert isinstance(reaction.should_respond, bool)
            # 如果选择回应，message 不应为空
            if reaction.should_respond:
                assert reaction.message and len(reaction.message.strip()) > 0

    async def test_bystander_reaction_to_player_message(self, zhipu_agent: BaseAgent):
        """旁观者对人类玩家消息的反应（must_respond 场景）"""
        engine = ChatEngine()
        chat_ctx = ChatContext()

        event = TriggerEvent(
            event_type=TriggerEventType.PLAYER_MESSAGE,
            actor_id="human-player",
            actor_name="人类玩家",
            description='人类玩家 说: "你们AI也太弱了吧！"',
            must_respond=True,
        )

        agent_state = {
            "chips": 1000,
            "actions_summary": "跟注 1 次",
            "hand_description": "未知（你还没有看牌）",
            "pot": 30,
            "current_bet": 10,
            "players_status": "人类玩家: 筹码990, 暗注\n对手B: 筹码1000, 暗注",
        }

        reaction = await engine.maybe_react_as_bystander(
            trigger_event=event,
            agent=zhipu_agent,
            chat_context=chat_ctx,
            agent_state=agent_state,
            must_respond=True,
        )

        # must_respond 场景下应该有回应
        assert reaction is not None
        assert reaction.should_respond is True
        assert reaction.message and len(reaction.message.strip()) > 0

    async def test_bystander_self_skip(self, zhipu_agent: BaseAgent):
        """旁观者不应对自己的行动做出反应"""
        engine = ChatEngine()
        chat_ctx = ChatContext()

        event = TriggerEvent(
            event_type=TriggerEventType.RAISE,
            actor_id=zhipu_agent.agent_id,  # 自己的行动
            actor_name=zhipu_agent.name,
            description=f"{zhipu_agent.name} 加注到 40 筹码",
        )

        reaction = await engine.maybe_react_as_bystander(
            trigger_event=event,
            agent=zhipu_agent,
            chat_context=chat_ctx,
        )

        # 自己的行动应返回 None
        assert reaction is None


# ============================================================
# 2.4 经验回顾测试
# ============================================================


class TestExperienceReview:
    """验证 ExperienceReviewer.perform_review 的真实 LLM 分析"""

    async def test_perform_review_consecutive_losses(self, zhipu_agent: BaseAgent):
        """连续输牌触发的经验回顾"""
        reviewer = ExperienceReviewer(agent=zhipu_agent, initial_chips=1000)

        # 模拟连续输牌历史
        for i in range(3):
            reviewer.round_results_history.append(
                RoundResult(
                    round_number=i + 1,
                    winner_id="opponent-1",
                    winner_name="对手A",
                    win_method="比牌获胜",
                    pot=60,
                    player_chip_changes={
                        zhipu_agent.agent_id: -20,
                        "opponent-1": 40,
                    },
                )
            )

        recent_thoughts = [
            ThoughtRecord(
                agent_id=zhipu_agent.agent_id,
                round_number=3,
                turn_number=1,
                hand_evaluation="一对3，牌力较弱",
                opponent_analysis="对手A 频繁加注，可能有大牌",
                risk_assessment="高风险",
                decision=GameAction.CALL,
                reasoning="跟注观察",
                confidence=0.3,
                emotion="焦虑",
            ),
        ]

        review = await reviewer.perform_review(
            trigger=ReviewTrigger.CONSECUTIVE_LOSSES,
            recent_narratives=[],
            recent_thoughts=recent_thoughts,
            opponent_stats={"对手A": "3 局全赢，频繁加注，胜率 100%"},
        )

        assert review is not None
        assert review.agent_id == zhipu_agent.agent_id
        assert review.trigger == ReviewTrigger.CONSECUTIVE_LOSSES
        # LLM 应生成非空分析
        assert review.self_analysis and len(review.self_analysis.strip()) > 0
        assert review.strategy_adjustment and len(review.strategy_adjustment.strip()) > 0
        # 策略注入文本应被生成
        assert review.strategy_context and len(review.strategy_context.strip()) > 0

    async def test_perform_review_chip_crisis(self, zhipu_agent: BaseAgent):
        """筹码危机触发的经验回顾"""
        reviewer = ExperienceReviewer(agent=zhipu_agent, initial_chips=1000)

        reviewer.round_results_history.append(
            RoundResult(
                round_number=5,
                winner_id="opponent-2",
                winner_name="对手B",
                win_method="其他玩家弃牌",
                pot=100,
                player_chip_changes={
                    zhipu_agent.agent_id: -50,
                    "opponent-2": 100,
                },
            )
        )

        review = await reviewer.perform_review(
            trigger=ReviewTrigger.CHIP_CRISIS,
            recent_narratives=[
                RoundNarrative(
                    agent_id=zhipu_agent.agent_id,
                    round_number=5,
                    narrative="这一局我被对手B的虚张声势吓到了，白白丢了50筹码。",
                    outcome="输",
                ),
            ],
            recent_thoughts=[],
            opponent_stats={
                "对手B": "喜欢虚张声势，弃牌率低",
            },
        )

        assert review is not None
        assert review.trigger == ReviewTrigger.CHIP_CRISIS
        assert review.self_analysis != ""


# ============================================================
# 2.5 叙事生成测试
# ============================================================


class TestThoughtNarrative:
    """验证 ThoughtReporter 的真实 LLM 叙事生成"""

    async def test_generate_round_narrative(self, zhipu_agent: BaseAgent):
        """生成单局叙事回顾"""
        reporter = ThoughtReporter(agent=zhipu_agent)

        thoughts = [
            ThoughtRecord(
                agent_id=zhipu_agent.agent_id,
                round_number=1,
                turn_number=1,
                hand_evaluation="一对K，牌力较强",
                opponent_analysis="对手A 暗注跟注，对手B 暗注跟注",
                risk_assessment="中等风险",
                decision=GameAction.CALL,
                reasoning="先跟注观察对手反应",
                confidence=0.7,
                emotion="自信",
                table_talk="嗯，我先跟着。",
            ),
            ThoughtRecord(
                agent_id=zhipu_agent.agent_id,
                round_number=1,
                turn_number=2,
                hand_evaluation="一对K，牌力较强",
                opponent_analysis="对手A 加注，可能有大牌或在虚张声势",
                risk_assessment="中高风险",
                decision=GameAction.RAISE,
                reasoning="我有一对K，加注试探",
                confidence=0.65,
                emotion="兴奋",
                table_talk="来吧，加注！",
            ),
        ]

        narrative = await reporter.generate_round_narrative(
            round_number=1,
            round_thoughts=thoughts,
            chat_messages="对手A: 这牌不错\n测试选手: 嗯，我先跟着。\n测试选手: 来吧，加注！",
            action_history=(
                "1. 对手A 跟注\n2. 对手B 跟注\n3. 测试选手 跟注\n4. 对手A 加注\n5. 测试选手 加注"
            ),
            hand_description="红心K, 黑桃K, 方块3（一对K）",
            round_outcome="测试选手 赢得 120 筹码",
        )

        assert isinstance(narrative, RoundNarrative)
        assert narrative.agent_id == zhipu_agent.agent_id
        assert narrative.round_number == 1
        # 叙事不应为空且应有一定长度
        assert len(narrative.narrative.strip()) > 20

    async def test_generate_game_summary(self, zhipu_agent: BaseAgent):
        """生成整场游戏总结"""
        reporter = ThoughtReporter(agent=zhipu_agent)

        summary = await reporter.generate_game_summary(
            rounds_played=10,
            rounds_won=4,
            total_chips_won=350,
            total_chips_lost=200,
            biggest_win=120,
            biggest_loss=80,
            fold_rate="30%",
            all_narratives=(
                "第1局：我拿到一对K，最终赢了120筹码。\n"
                "第2局：手牌太差，果断弃牌。\n"
                "第3局：被对手A虚张声势骗了，输了80筹码。\n"
            ),
            all_reviews="第5局后经验回顾：需要更注意对手的加注模式。",
            opponents_info="对手A: 激进型选手，喜欢虚张声势\n对手B: 保守型，只在有好牌时下注",
        )

        assert summary is not None
        assert summary.agent_id == zhipu_agent.agent_id
        assert summary.rounds_played == 10
        assert summary.rounds_won == 4
        # LLM 生成的叙事总结应有内容
        # 注意: narrative_summary 可能来自 JSON 解析或直接文本
        has_content = (
            summary.narrative_summary and len(summary.narrative_summary.strip()) > 20
        ) or (summary.self_reflection and len(summary.self_reflection.strip()) > 0)
        assert has_content, "游戏总结应包含有意义的叙事或反思内容"
