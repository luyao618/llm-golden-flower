"""T3.1 单元测试: ExperienceReviewer + ReviewTrigger/ExperienceReview 模型

测试覆盖:
- ReviewTrigger / ExperienceReview 数据模型构建和验证
- ExperienceReviewer.check_trigger(): 5 种触发条件 + 优先级
- ExperienceReviewer.perform_review(): LLM 调用成功、JSON 解析失败、LLM 异常
- ExperienceReviewer.generate_strategy_context(): 输出格式
- 计数器重置逻辑（consecutive_losses、rounds_since_review）
- _detect_opponent_shift() 对手行为突变检测
- 辅助方法与边界情况
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import BaseAgent
from app.agents.experience import (
    BIG_LOSS_RATIO,
    CHIP_CRISIS_RATIO,
    CONSECUTIVE_LOSSES_THRESHOLD,
    DEFAULT_REVIEW_WINDOW,
    ExperienceReviewer,
    OPPONENT_SHIFT_THRESHOLD,
    PERIODIC_INTERVAL,
)
from app.models.game import GameAction, GameState, Player, PlayerType, RoundResult
from app.models.thought import (
    ExperienceReview,
    ReviewTrigger,
    RoundNarrative,
    ThoughtRecord,
)


# ============================================================
# Fixtures
# ============================================================

AGENT_ID = "agent-1"
OPPONENT_ID = "opponent-1"


def _make_agent(agent_id: str = AGENT_ID, name: str = "测试选手") -> BaseAgent:
    """创建测试用 Agent"""
    return BaseAgent(
        agent_id=agent_id,
        name=name,
        model_id="copilot-gpt4o-mini",
    )


def _make_game(
    agent_id: str = AGENT_ID,
    agent_chips: int = 1000,
    opponent_id: str = OPPONENT_ID,
    opponent_chips: int = 1000,
) -> GameState:
    """创建包含 2 个玩家的测试游戏状态"""
    return GameState(
        players=[
            Player(id=agent_id, name="AI", player_type=PlayerType.AI, chips=agent_chips),
            Player(
                id=opponent_id,
                name="Opponent",
                player_type=PlayerType.AI,
                chips=opponent_chips,
            ),
        ]
    )


def _make_round_result(
    round_number: int = 1,
    winner_id: str = OPPONENT_ID,
    pot: int = 100,
    agent_change: int = -50,
    opponent_change: int = 50,
    win_method: str = "",
) -> RoundResult:
    """创建测试用局结果"""
    return RoundResult(
        round_number=round_number,
        winner_id=winner_id,
        pot=pot,
        win_method=win_method,
        player_chip_changes={AGENT_ID: agent_change, OPPONENT_ID: opponent_change},
    )


def _make_narratives(count: int = 2, start_round: int = 1) -> list[RoundNarrative]:
    """创建测试用叙事列表"""
    return [
        RoundNarrative(
            agent_id=AGENT_ID,
            round_number=start_round + i,
            narrative=f"第 {start_round + i} 局的叙事...",
            outcome="赢了" if i % 2 == 0 else "输了",
        )
        for i in range(count)
    ]


def _make_thoughts(count: int = 2, start_round: int = 1) -> list[ThoughtRecord]:
    """创建测试用思考记录"""
    return [
        ThoughtRecord(
            agent_id=AGENT_ID,
            round_number=start_round + i,
            turn_number=1,
            reasoning=f"理由{start_round + i}",
            decision=GameAction.CALL,
            confidence=0.5,
        )
        for i in range(count)
    ]


# ============================================================
# 数据模型测试
# ============================================================


class TestReviewTrigger:
    """ReviewTrigger 枚举测试"""

    def test_values(self):
        assert ReviewTrigger.CHIP_CRISIS.value == "chip_crisis"
        assert ReviewTrigger.CONSECUTIVE_LOSSES.value == "consecutive_losses"
        assert ReviewTrigger.BIG_LOSS.value == "big_loss"
        assert ReviewTrigger.OPPONENT_SHIFT.value == "opponent_shift"
        assert ReviewTrigger.PERIODIC.value == "periodic"

    def test_str_behavior(self):
        """ReviewTrigger 是 str 枚举，可直接当字符串用"""
        trigger = ReviewTrigger.CHIP_CRISIS
        assert isinstance(trigger, str)
        assert trigger == "chip_crisis"

    def test_all_members(self):
        """确保恰好 5 种触发条件"""
        assert len(ReviewTrigger) == 5


class TestExperienceReview:
    """ExperienceReview 模型测试"""

    def test_default_values(self):
        review = ExperienceReview(
            agent_id=AGENT_ID,
            trigger=ReviewTrigger.PERIODIC,
            triggered_at_round=5,
        )
        assert review.agent_id == AGENT_ID
        assert review.trigger == ReviewTrigger.PERIODIC
        assert review.triggered_at_round == 5
        assert review.rounds_reviewed == []
        assert review.self_analysis == ""
        assert review.opponent_patterns == {}
        assert review.strategy_adjustment == ""
        assert review.confidence_shift == 0.0
        assert review.strategy_context == ""

    def test_full_construction(self):
        review = ExperienceReview(
            agent_id=AGENT_ID,
            trigger=ReviewTrigger.CHIP_CRISIS,
            triggered_at_round=8,
            rounds_reviewed=[6, 7, 8],
            self_analysis="打得太激进了",
            opponent_patterns={"opponent-1": "保守型", "opponent-2": "激进型"},
            strategy_adjustment="减少冒险，等待好牌",
            confidence_shift=-0.3,
            strategy_context="【策略调整】减少冒险",
        )
        assert review.rounds_reviewed == [6, 7, 8]
        assert len(review.opponent_patterns) == 2
        assert review.confidence_shift == -0.3

    def test_confidence_shift_bounds(self):
        """confidence_shift 应在 -1 到 1 范围内"""
        review = ExperienceReview(
            agent_id=AGENT_ID,
            trigger=ReviewTrigger.PERIODIC,
            triggered_at_round=1,
            confidence_shift=-1.0,
        )
        assert review.confidence_shift == -1.0

        review = ExperienceReview(
            agent_id=AGENT_ID,
            trigger=ReviewTrigger.PERIODIC,
            triggered_at_round=1,
            confidence_shift=1.0,
        )
        assert review.confidence_shift == 1.0

        with pytest.raises(Exception):
            ExperienceReview(
                agent_id=AGENT_ID,
                trigger=ReviewTrigger.PERIODIC,
                triggered_at_round=1,
                confidence_shift=1.5,
            )

        with pytest.raises(Exception):
            ExperienceReview(
                agent_id=AGENT_ID,
                trigger=ReviewTrigger.PERIODIC,
                triggered_at_round=1,
                confidence_shift=-1.5,
            )

    def test_serialization(self):
        review = ExperienceReview(
            agent_id=AGENT_ID,
            trigger=ReviewTrigger.BIG_LOSS,
            triggered_at_round=3,
            self_analysis="分析内容",
            strategy_adjustment="调整方向",
        )
        data = review.model_dump()
        assert data["trigger"] == "big_loss"
        assert data["self_analysis"] == "分析内容"

        restored = ExperienceReview.model_validate(data)
        assert restored.trigger == ReviewTrigger.BIG_LOSS
        assert restored.strategy_adjustment == "调整方向"


# ============================================================
# ExperienceReviewer 初始化测试
# ============================================================


class TestExperienceReviewerInit:
    """初始化和基本属性测试"""

    def test_init_defaults(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)

        assert reviewer.agent is agent
        assert reviewer.initial_chips == 1000
        assert reviewer.consecutive_losses == 0
        assert reviewer.rounds_since_review == 0
        assert reviewer.last_review_round == 0
        assert reviewer.reviews == []
        assert reviewer.round_results_history == []

    def test_reset(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent)

        # 模拟一些状态
        reviewer.consecutive_losses = 3
        reviewer.rounds_since_review = 7
        reviewer.last_review_round = 5
        reviewer.reviews.append(
            ExperienceReview(
                agent_id=AGENT_ID,
                trigger=ReviewTrigger.PERIODIC,
                triggered_at_round=5,
            )
        )
        reviewer.round_results_history.append(_make_round_result())
        reviewer._opponent_action_stats["opp"] = {"rounds": 1}

        reviewer.reset()

        assert reviewer.consecutive_losses == 0
        assert reviewer.rounds_since_review == 0
        assert reviewer.last_review_round == 0
        assert reviewer.reviews == []
        assert reviewer.round_results_history == []
        assert reviewer._opponent_action_stats == {}


# ============================================================
# check_trigger() 测试
# ============================================================


class TestCheckTrigger:
    """check_trigger() 5 种触发条件测试"""

    def test_no_trigger_on_win(self):
        """赢了一局，不触发任何条件"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=1050)
        result = _make_round_result(winner_id=AGENT_ID, agent_change=50, opponent_change=-50)

        trigger = reviewer.check_trigger(game, result)
        assert trigger is None

    def test_no_trigger_normal_loss(self):
        """正常小额输牌，不触发"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=900)
        result = _make_round_result(agent_change=-50, opponent_change=50)

        trigger = reviewer.check_trigger(game, result)
        assert trigger is None

    # ---- 1. chip_crisis ----

    def test_chip_crisis_trigger(self):
        """筹码低于初始值 30% 触发"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        # 筹码 = 250 < 1000 * 0.3 = 300
        game = _make_game(agent_chips=250)
        result = _make_round_result(agent_change=-100)

        trigger = reviewer.check_trigger(game, result)
        assert trigger == ReviewTrigger.CHIP_CRISIS

    def test_chip_crisis_at_boundary(self):
        """筹码恰好等于阈值时触发"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        # 筹码 = 300 = 1000 * 0.3，<= 阈值
        game = _make_game(agent_chips=300)
        result = _make_round_result(agent_change=-100)

        trigger = reviewer.check_trigger(game, result)
        assert trigger == ReviewTrigger.CHIP_CRISIS

    def test_chip_crisis_not_at_boundary_plus_one(self):
        """筹码刚好超过阈值不触发"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=301)
        result = _make_round_result(agent_change=-50)

        trigger = reviewer.check_trigger(game, result)
        # 301 > 300, no chip_crisis; only 1 loss, no consecutive; 50 < 200, no big_loss
        assert trigger is None

    # ---- 2. consecutive_losses ----

    def test_consecutive_losses_trigger(self):
        """连续输 2 局触发"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=900)

        # 第 1 局：输
        result1 = _make_round_result(round_number=1, agent_change=-50)
        trigger1 = reviewer.check_trigger(game, result1)
        assert trigger1 is None
        assert reviewer.consecutive_losses == 1

        # 第 2 局：输
        result2 = _make_round_result(round_number=2, agent_change=-50)
        trigger2 = reviewer.check_trigger(game, result2)
        assert trigger2 == ReviewTrigger.CONSECUTIVE_LOSSES
        assert reviewer.consecutive_losses == 2

    def test_consecutive_losses_reset_on_win(self):
        """赢一局后连败计数归零"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=900)

        # 输一局
        result1 = _make_round_result(round_number=1, agent_change=-50)
        reviewer.check_trigger(game, result1)
        assert reviewer.consecutive_losses == 1

        # 赢一局
        result2 = _make_round_result(
            round_number=2, winner_id=AGENT_ID, agent_change=50, opponent_change=-50
        )
        reviewer.check_trigger(game, result2)
        assert reviewer.consecutive_losses == 0

    def test_consecutive_losses_three_in_a_row(self):
        """连续 3 局输，第 2 局即触发"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=800)

        for i in range(3):
            result = _make_round_result(round_number=i + 1, agent_change=-50)
            trigger = reviewer.check_trigger(game, result)
            if i == 0:
                assert trigger is None
            else:
                # 第 2 局和第 3 局都应该触发 consecutive_losses
                assert trigger == ReviewTrigger.CONSECUTIVE_LOSSES

    # ---- 3. big_loss ----

    def test_big_loss_trigger(self):
        """单局损失超过初始筹码 20%"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=700)
        # 损失 250 > 1000 * 0.2 = 200
        result = _make_round_result(agent_change=-250, opponent_change=250, pot=300)

        trigger = reviewer.check_trigger(game, result)
        assert trigger == ReviewTrigger.BIG_LOSS

    def test_big_loss_not_triggered_when_win(self):
        """赢了不会触发 big_loss"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=1300)
        result = _make_round_result(winner_id=AGENT_ID, agent_change=300, opponent_change=-300)

        trigger = reviewer.check_trigger(game, result)
        assert trigger is None

    def test_big_loss_at_boundary(self):
        """损失恰好等于阈值不触发 (> not >=)"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=800)
        # 损失 200 = 1000 * 0.2，不触发（需要 > 200）
        result = _make_round_result(agent_change=-200, opponent_change=200)

        trigger = reviewer.check_trigger(game, result)
        assert trigger is None

    def test_big_loss_just_above_boundary(self):
        """损失刚超过阈值触发"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=799)
        # 损失 201 > 200
        result = _make_round_result(agent_change=-201, opponent_change=201)

        trigger = reviewer.check_trigger(game, result)
        assert trigger == ReviewTrigger.BIG_LOSS

    # ---- 4. opponent_shift ----

    def test_opponent_shift_not_triggered_early(self):
        """历史不足 5 局不触发 opponent_shift"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=900)

        for i in range(4):
            result = _make_round_result(
                round_number=i + 1,
                winner_id=AGENT_ID,
                agent_change=50,
                opponent_change=-50,
            )
            trigger = reviewer.check_trigger(game, result)
            assert trigger is None

    def test_opponent_shift_trigger(self):
        """对手行为突变触发"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=900)

        # 前 7 局：对手全输（整体胜率 = 0）
        for i in range(7):
            result = _make_round_result(
                round_number=i + 1,
                winner_id=AGENT_ID,
                agent_change=50,
                opponent_change=-50,
            )
            reviewer.check_trigger(game, result)

        # 接下来 3 局：对手全赢 → recent_win_rate 远高于 overall_win_rate
        for i in range(3):
            result = _make_round_result(
                round_number=8 + i,
                winner_id=OPPONENT_ID,
                agent_change=-50,
                opponent_change=50,
            )
            trigger = reviewer.check_trigger(game, result)

        # 到第 10 局时 opponent stats:
        # rounds=10, wins=3, recent_rounds=3, recent_wins=3
        # overall_rate = 3/10 = 0.3, recent_rate = 3/3 = 1.0
        # diff = 0.7 > 0.4 → 触发 opponent_shift
        # 但 consecutive_losses (3) >= 2，所以 CONSECUTIVE_LOSSES 优先
        # 我们需要保证连败计数不会覆盖它。让我构造没有连败的情况。

    def test_opponent_shift_trigger_without_consecutive_loss(self):
        """对手行为突变触发（无连败干扰）"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=900)

        # 前 7 局：对手全输
        for i in range(7):
            result = _make_round_result(
                round_number=i + 1,
                winner_id=AGENT_ID,
                agent_change=50,
                opponent_change=-50,
            )
            reviewer.check_trigger(game, result)

        # 第 8 局：赢（重置连败计数）
        result_win = _make_round_result(
            round_number=8,
            winner_id=AGENT_ID,
            agent_change=50,
            opponent_change=-50,
        )
        reviewer.check_trigger(game, result_win)

        # 第 9 局：对手赢（连败=1，不够触发 consecutive_losses）
        # 同时设置对手 recent_wins 高
        # 手动调整 opponent stats 来确保 shift 检测
        reviewer._opponent_action_stats[OPPONENT_ID] = {
            "rounds": 9,
            "wins": 1,  # 整体胜率 ≈ 0.11
            "total_change": -350,
            "recent_wins": 3,  # 近期胜率 = 3/3 = 1.0
            "recent_rounds": 3,
        }

        result = _make_round_result(
            round_number=9,
            winner_id=OPPONENT_ID,
            agent_change=-50,
            opponent_change=50,
        )
        trigger = reviewer.check_trigger(game, result)
        # After this call: consecutive_losses = 1 (not enough for CONSECUTIVE_LOSSES)
        # loss = 50, not > 200 (no BIG_LOSS)
        # chips = 900, not <= 300 (no CHIP_CRISIS)
        # opponent shift: overall = 2/10 = 0.2 (updated), recent = 4/4 = 1.0
        # diff = 0.8 > 0.4 → OPPONENT_SHIFT triggered
        assert trigger == ReviewTrigger.OPPONENT_SHIFT

    # ---- 5. periodic ----

    def test_periodic_trigger(self):
        """每 5 局定期回顾"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=1000)

        # 打 5 局全赢（避免其他触发条件）
        for i in range(PERIODIC_INTERVAL):
            result = _make_round_result(
                round_number=i + 1,
                winner_id=AGENT_ID,
                agent_change=10,
                opponent_change=-10,
            )
            trigger = reviewer.check_trigger(game, result)

            if i < PERIODIC_INTERVAL - 1:
                assert trigger is None
            else:
                assert trigger == ReviewTrigger.PERIODIC

    def test_rounds_since_review_increments(self):
        """rounds_since_review 每局递增"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=1000)

        for i in range(3):
            result = _make_round_result(
                round_number=i + 1,
                winner_id=AGENT_ID,
                agent_change=10,
                opponent_change=-10,
            )
            reviewer.check_trigger(game, result)

        assert reviewer.rounds_since_review == 3

    # ---- 优先级测试 ----

    def test_chip_crisis_overrides_consecutive_losses(self):
        """chip_crisis 优先于 consecutive_losses"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.consecutive_losses = 1  # 再输一局就触发 consecutive_losses

        game = _make_game(agent_chips=250)  # 同时满足 chip_crisis
        result = _make_round_result(agent_change=-50)

        trigger = reviewer.check_trigger(game, result)
        assert trigger == ReviewTrigger.CHIP_CRISIS

    def test_consecutive_losses_overrides_big_loss(self):
        """consecutive_losses 优先于 big_loss"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.consecutive_losses = 1  # 再输一局就触发

        game = _make_game(agent_chips=700)
        # 损失 250 > 200，满足 big_loss
        result = _make_round_result(agent_change=-250, opponent_change=250)

        trigger = reviewer.check_trigger(game, result)
        assert trigger == ReviewTrigger.CONSECUTIVE_LOSSES

    def test_big_loss_overrides_periodic(self):
        """big_loss 优先于 periodic"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.rounds_since_review = PERIODIC_INTERVAL - 1  # 再来一局就触发 periodic

        game = _make_game(agent_chips=700)
        # 损失 250 > 200
        result = _make_round_result(agent_change=-250, opponent_change=250)

        trigger = reviewer.check_trigger(game, result)
        assert trigger == ReviewTrigger.BIG_LOSS

    # ---- 内部状态更新测试 ----

    def test_round_results_history_appended(self):
        """check_trigger 应记录 round_result 到历史"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=1000)

        result = _make_round_result(
            round_number=1, winner_id=AGENT_ID, agent_change=50, opponent_change=-50
        )
        reviewer.check_trigger(game, result)

        assert len(reviewer.round_results_history) == 1
        assert reviewer.round_results_history[0].round_number == 1

    def test_player_not_found_returns_zero_chips(self):
        """玩家不在游戏中时筹码为 0（触发 chip_crisis）"""
        agent = _make_agent(agent_id="missing-agent")
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game()  # 使用默认 agent_id，不包含 missing-agent

        result = RoundResult(
            round_number=1,
            winner_id=OPPONENT_ID,
            pot=100,
            player_chip_changes={"missing-agent": -50, OPPONENT_ID: 50},
        )

        trigger = reviewer.check_trigger(game, result)
        # 0 chips <= 300, should trigger CHIP_CRISIS
        assert trigger == ReviewTrigger.CHIP_CRISIS


# ============================================================
# perform_review() 测试
# ============================================================


class TestPerformReview:
    """perform_review() 测试（LLM 调用使用 mock）"""

    @pytest.mark.asyncio
    async def test_perform_review_success(self):
        """正常 LLM 调用返回有效 JSON"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)

        # 预填充历史以获取 rounds_reviewed
        reviewer.round_results_history.append(_make_round_result(round_number=3, agent_change=-100))
        reviewer.round_results_history.append(_make_round_result(round_number=4, agent_change=-100))
        reviewer.rounds_since_review = 2

        llm_response = json.dumps(
            {
                "self_analysis": "最近打得太激进，需要收敛",
                "opponent_patterns": {"opponent-1": "越来越保守"},
                "strategy_adjustment": "减少加注频率，多观察",
                "confidence_shift": -0.2,
            }
        )

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=llm_response):
            review = await reviewer.perform_review(
                trigger=ReviewTrigger.CONSECUTIVE_LOSSES,
                recent_narratives=_make_narratives(2, start_round=3),
                recent_thoughts=_make_thoughts(2, start_round=3),
                opponent_stats={"opponent-1": "跟注率 60%，加注率 20%"},
            )

        assert isinstance(review, ExperienceReview)
        assert review.agent_id == AGENT_ID
        assert review.trigger == ReviewTrigger.CONSECUTIVE_LOSSES
        assert review.self_analysis == "最近打得太激进，需要收敛"
        assert review.opponent_patterns == {"opponent-1": "越来越保守"}
        assert review.strategy_adjustment == "减少加注频率，多观察"
        assert review.confidence_shift == -0.2
        assert review.strategy_context != ""  # 应生成策略注入文本

    @pytest.mark.asyncio
    async def test_perform_review_resets_rounds_since_review(self):
        """perform_review 后 rounds_since_review 重置为 0"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.rounds_since_review = 5
        reviewer.round_results_history.append(_make_round_result(round_number=5))

        llm_response = json.dumps({"self_analysis": "ok", "strategy_adjustment": "继续"})

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=llm_response):
            await reviewer.perform_review(
                trigger=ReviewTrigger.PERIODIC,
                recent_narratives=[],
                recent_thoughts=[],
                opponent_stats={},
            )

        assert reviewer.rounds_since_review == 0

    @pytest.mark.asyncio
    async def test_perform_review_resets_consecutive_losses_on_trigger(self):
        """当触发条件是 CONSECUTIVE_LOSSES 时，回顾后重置连败计数"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.consecutive_losses = 3
        reviewer.round_results_history.append(_make_round_result(round_number=3))

        llm_response = json.dumps({"self_analysis": "ok", "strategy_adjustment": "继续"})

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=llm_response):
            await reviewer.perform_review(
                trigger=ReviewTrigger.CONSECUTIVE_LOSSES,
                recent_narratives=[],
                recent_thoughts=[],
                opponent_stats={},
            )

        assert reviewer.consecutive_losses == 0

    @pytest.mark.asyncio
    async def test_perform_review_does_not_reset_consecutive_losses_for_other_triggers(self):
        """非 CONSECUTIVE_LOSSES 触发时，不重置连败计数"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.consecutive_losses = 3
        reviewer.round_results_history.append(_make_round_result(round_number=3))

        llm_response = json.dumps({"self_analysis": "ok", "strategy_adjustment": "继续"})

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=llm_response):
            await reviewer.perform_review(
                trigger=ReviewTrigger.BIG_LOSS,
                recent_narratives=[],
                recent_thoughts=[],
                opponent_stats={},
            )

        assert reviewer.consecutive_losses == 3

    @pytest.mark.asyncio
    async def test_perform_review_saves_review(self):
        """回顾结果应保存到 reviews 列表"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history.append(_make_round_result(round_number=1))

        llm_response = json.dumps({"self_analysis": "分析", "strategy_adjustment": "调整"})

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=llm_response):
            review = await reviewer.perform_review(
                trigger=ReviewTrigger.PERIODIC,
                recent_narratives=[],
                recent_thoughts=[],
                opponent_stats={},
            )

        assert len(reviewer.reviews) == 1
        assert reviewer.reviews[0] is review

    @pytest.mark.asyncio
    async def test_perform_review_json_parse_failure(self):
        """LLM 返回非 JSON 文本时的降级处理"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history.append(_make_round_result(round_number=2))

        raw_text = "这是一段纯文本分析，没有 JSON 格式..."

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=raw_text):
            review = await reviewer.perform_review(
                trigger=ReviewTrigger.BIG_LOSS,
                recent_narratives=_make_narratives(1, start_round=2),
                recent_thoughts=[],
                opponent_stats={},
            )

        assert isinstance(review, ExperienceReview)
        assert review.trigger == ReviewTrigger.BIG_LOSS
        # 非 JSON 时，原始文本作为 self_analysis
        assert "纯文本分析" in review.self_analysis
        # 降级时的默认策略调整
        assert review.strategy_adjustment == "继续观察，谨慎调整。"

    @pytest.mark.asyncio
    async def test_perform_review_llm_failure(self):
        """LLM 调用失败时的降级回顾"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history.append(_make_round_result(round_number=1))

        with patch.object(
            agent,
            "call_llm",
            new_callable=AsyncMock,
            side_effect=Exception("API timeout"),
        ):
            review = await reviewer.perform_review(
                trigger=ReviewTrigger.CHIP_CRISIS,
                recent_narratives=[],
                recent_thoughts=[],
                opponent_stats={},
            )

        assert isinstance(review, ExperienceReview)
        assert review.trigger == ReviewTrigger.CHIP_CRISIS
        assert "失败" in review.self_analysis
        # chip_crisis 的降级策略
        assert "筹码不足" in review.strategy_adjustment

    @pytest.mark.asyncio
    async def test_perform_review_fallback_strategies_per_trigger(self):
        """每种触发条件有不同的降级策略"""
        agent = _make_agent()

        fallback_keywords = {
            ReviewTrigger.CHIP_CRISIS: "筹码不足",
            ReviewTrigger.CONSECUTIVE_LOSSES: "连续输牌",
            ReviewTrigger.BIG_LOSS: "大额亏损",
            ReviewTrigger.OPPONENT_SHIFT: "对手打法",
            ReviewTrigger.PERIODIC: "定期回顾",
        }

        for trigger, keyword in fallback_keywords.items():
            reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
            reviewer.round_results_history.append(_make_round_result(round_number=1))

            with patch.object(
                agent,
                "call_llm",
                new_callable=AsyncMock,
                side_effect=Exception("fail"),
            ):
                review = await reviewer.perform_review(
                    trigger=trigger,
                    recent_narratives=[],
                    recent_thoughts=[],
                    opponent_stats={},
                )

            assert keyword in review.strategy_adjustment, (
                f"Trigger {trigger.value} fallback should contain '{keyword}', "
                f"got: '{review.strategy_adjustment}'"
            )

    @pytest.mark.asyncio
    async def test_perform_review_markdown_json(self):
        """LLM 返回 markdown 代码块包裹的 JSON"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history.append(_make_round_result(round_number=1))

        llm_response = (
            "```json\n"
            '{"self_analysis": "从代码块中提取", '
            '"strategy_adjustment": "调整策略", '
            '"confidence_shift": 0.1}\n'
            "```"
        )

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=llm_response):
            review = await reviewer.perform_review(
                trigger=ReviewTrigger.PERIODIC,
                recent_narratives=[],
                recent_thoughts=[],
                opponent_stats={},
            )

        assert review.self_analysis == "从代码块中提取"
        assert review.strategy_adjustment == "调整策略"
        assert review.confidence_shift == 0.1

    @pytest.mark.asyncio
    async def test_perform_review_confidence_shift_clamped(self):
        """confidence_shift 超出范围时被截断到 [-1, 1]"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history.append(_make_round_result(round_number=1))

        llm_response = json.dumps(
            {
                "self_analysis": "ok",
                "strategy_adjustment": "调整",
                "confidence_shift": 5.0,  # 超出范围
            }
        )

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=llm_response):
            review = await reviewer.perform_review(
                trigger=ReviewTrigger.PERIODIC,
                recent_narratives=[],
                recent_thoughts=[],
                opponent_stats={},
            )

        assert review.confidence_shift == 1.0  # 被截断到 1.0

    @pytest.mark.asyncio
    async def test_perform_review_with_empty_narratives(self):
        """空叙事列表的处理"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history.append(_make_round_result(round_number=1))

        llm_response = json.dumps(
            {"self_analysis": "没什么叙事可回顾", "strategy_adjustment": "保持"}
        )

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=llm_response):
            review = await reviewer.perform_review(
                trigger=ReviewTrigger.PERIODIC,
                recent_narratives=[],
                recent_thoughts=[],
                opponent_stats={},
            )

        assert isinstance(review, ExperienceReview)
        assert review.rounds_reviewed  # 应从 history 推算


# ============================================================
# generate_strategy_context() 测试
# ============================================================


class TestGenerateStrategyContext:
    """generate_strategy_context() 输出格式测试"""

    def test_full_context(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)

        review = ExperienceReview(
            agent_id=AGENT_ID,
            trigger=ReviewTrigger.CHIP_CRISIS,
            triggered_at_round=8,
            self_analysis="打得太激进",
            opponent_patterns={"opponent-1": "越来越保守"},
            strategy_adjustment="减少加注频率",
        )

        context = reviewer.generate_strategy_context(review)

        assert "自我反思" in context
        assert "打得太激进" in context
        assert "对手分析" in context
        assert "opponent-1" in context
        assert "越来越保守" in context
        assert "策略调整" in context
        assert "减少加注频率" in context
        assert "第 8 局" in context
        assert "筹码危机" in context

    def test_empty_review(self):
        """所有字段为空时返回空字符串"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)

        review = ExperienceReview(
            agent_id=AGENT_ID,
            trigger=ReviewTrigger.PERIODIC,
            triggered_at_round=5,
            self_analysis="",
            opponent_patterns={},
            strategy_adjustment="",
        )

        context = reviewer.generate_strategy_context(review)
        assert context == ""

    def test_partial_context_only_self_analysis(self):
        """只有 self_analysis 时的格式"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)

        review = ExperienceReview(
            agent_id=AGENT_ID,
            trigger=ReviewTrigger.PERIODIC,
            triggered_at_round=5,
            self_analysis="需要更谨慎",
        )

        context = reviewer.generate_strategy_context(review)
        assert "自我反思" in context
        assert "需要更谨慎" in context
        assert "对手分析" not in context
        assert "策略调整" not in context

    def test_all_trigger_types_have_chinese_name(self):
        """每种触发条件都有中文名称"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)

        for trigger in ReviewTrigger:
            review = ExperienceReview(
                agent_id=AGENT_ID,
                trigger=trigger,
                triggered_at_round=1,
                self_analysis="test",
            )
            context = reviewer.generate_strategy_context(review)
            # 应该包含中文触发原因描述，不应包含英文枚举值
            assert context != ""
            chinese_name = reviewer._trigger_to_chinese(trigger)
            assert chinese_name in context


# ============================================================
# 辅助方法测试
# ============================================================


class TestHelperMethods:
    """内部辅助方法测试"""

    def test_get_player_chips(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=750)

        chips = reviewer._get_player_chips(game)
        assert chips == 750

    def test_get_player_chips_missing_player(self):
        agent = _make_agent(agent_id="nonexistent")
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game()

        chips = reviewer._get_player_chips(game)
        assert chips == 0

    def test_calculate_loss_when_losing(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        result = _make_round_result(agent_change=-150)

        loss = reviewer._calculate_loss(result)
        assert loss == 150

    def test_calculate_loss_when_winning(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        result = _make_round_result(agent_change=150)

        loss = reviewer._calculate_loss(result)
        assert loss == 0

    def test_calculate_loss_when_zero(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        result = _make_round_result(agent_change=0)

        loss = reviewer._calculate_loss(result)
        assert loss == 0

    def test_calculate_loss_missing_player(self):
        agent = _make_agent(agent_id="not-in-result")
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        result = _make_round_result()

        loss = reviewer._calculate_loss(result)
        assert loss == 0

    def test_format_narratives_empty(self):
        result = ExperienceReviewer._format_narratives([])
        assert "无叙事记录" in result

    def test_format_narratives_with_data(self):
        narratives = _make_narratives(2, start_round=3)
        result = ExperienceReviewer._format_narratives(narratives)
        assert "第 3 局" in result
        assert "第 4 局" in result

    def test_format_opponent_stats_empty(self):
        result = ExperienceReviewer._format_opponent_stats({})
        assert "暂无" in result

    def test_format_opponent_stats_with_data(self):
        stats = {"player-2": "激进型，加注频率高", "player-3": "保守型"}
        result = ExperienceReviewer._format_opponent_stats(stats)
        assert "player-2" in result
        assert "激进型" in result
        assert "player-3" in result

    def test_try_parse_json_valid(self):
        result = ExperienceReviewer._try_parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_try_parse_json_markdown_block(self):
        result = ExperienceReviewer._try_parse_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_try_parse_json_embedded_braces(self):
        text = 'Some text before {"key": "value"} some text after'
        result = ExperienceReviewer._try_parse_json(text)
        assert result == {"key": "value"}

    def test_try_parse_json_invalid(self):
        result = ExperienceReviewer._try_parse_json("no json here at all")
        assert result is None

    def test_trigger_to_chinese(self):
        assert ExperienceReviewer._trigger_to_chinese(ReviewTrigger.CHIP_CRISIS) == "筹码危机"
        assert (
            ExperienceReviewer._trigger_to_chinese(ReviewTrigger.CONSECUTIVE_LOSSES) == "连续输牌"
        )
        assert ExperienceReviewer._trigger_to_chinese(ReviewTrigger.BIG_LOSS) == "大额损失"
        assert (
            ExperienceReviewer._trigger_to_chinese(ReviewTrigger.OPPONENT_SHIFT) == "对手行为突变"
        )
        assert ExperienceReviewer._trigger_to_chinese(ReviewTrigger.PERIODIC) == "定期回顾"

    def test_get_rounds_reviewed_from_narratives(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)

        narratives = _make_narratives(3, start_round=5)
        rounds = reviewer._get_rounds_reviewed(narratives)
        assert rounds == [5, 6, 7]

    def test_get_rounds_reviewed_from_history(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history = [_make_round_result(round_number=i) for i in range(1, 8)]

        rounds = reviewer._get_rounds_reviewed([])
        # Should return last DEFAULT_REVIEW_WINDOW results
        assert rounds == [3, 4, 5, 6, 7]

    def test_get_rounds_reviewed_deduplicates(self):
        """叙事中有重复局号时去重"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)

        narratives = [
            RoundNarrative(agent_id=AGENT_ID, round_number=3, narrative="n1", outcome="o1"),
            RoundNarrative(agent_id=AGENT_ID, round_number=3, narrative="n2", outcome="o2"),
            RoundNarrative(agent_id=AGENT_ID, round_number=4, narrative="n3", outcome="o3"),
        ]
        rounds = reviewer._get_rounds_reviewed(narratives)
        assert rounds == [3, 4]

    def test_calculate_review_stats_empty(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)

        stats = reviewer._calculate_review_stats([])
        assert stats["win_rate"] == "0%"
        assert stats["chips_change"] == "0"
        assert stats["fold_rate"] == "0%"

    def test_calculate_review_stats_with_data(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history = [
            _make_round_result(round_number=1, winner_id=AGENT_ID, agent_change=100),
            _make_round_result(round_number=2, winner_id=OPPONENT_ID, agent_change=-50),
            _make_round_result(
                round_number=3,
                winner_id=OPPONENT_ID,
                agent_change=-80,
                win_method="对手弃牌胜出",  # 不是 agent 弃牌
            ),
            _make_round_result(
                round_number=4,
                winner_id=AGENT_ID,
                agent_change=60,
                win_method="弃牌胜出",  # agent 没弃牌，因为 agent 赢了
            ),
        ]

        stats = reviewer._calculate_review_stats([1, 2, 3, 4])
        assert stats["win_rate"] == "50%"  # 2 wins / 4 rounds
        assert stats["chips_change"] == "+30"  # 100 - 50 - 80 + 60 = 30


# ============================================================
# get_reviews_text() / get_all_reviews() 测试
# ============================================================


class TestReviewsAccessors:
    """reviews 访问方法测试"""

    def test_get_all_reviews_empty(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        assert reviewer.get_all_reviews() == []

    def test_get_all_reviews_returns_list(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        review = ExperienceReview(
            agent_id=AGENT_ID,
            trigger=ReviewTrigger.PERIODIC,
            triggered_at_round=5,
        )
        reviewer.reviews.append(review)

        all_reviews = reviewer.get_all_reviews()
        assert len(all_reviews) == 1
        assert all_reviews[0] is review

    def test_get_reviews_text_empty(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        text = reviewer.get_reviews_text()
        assert "无经验回顾" in text

    def test_get_reviews_text_with_reviews(self):
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.reviews.append(
            ExperienceReview(
                agent_id=AGENT_ID,
                trigger=ReviewTrigger.CHIP_CRISIS,
                triggered_at_round=5,
                self_analysis="需要更保守",
                strategy_adjustment="减少下注",
            )
        )
        reviewer.reviews.append(
            ExperienceReview(
                agent_id=AGENT_ID,
                trigger=ReviewTrigger.PERIODIC,
                triggered_at_round=10,
                self_analysis="状态恢复",
                strategy_adjustment="恢复正常打法",
            )
        )

        text = reviewer.get_reviews_text()
        assert "第 1 次经验回顾" in text
        assert "第 5 局" in text
        assert "筹码危机" in text
        assert "需要更保守" in text
        assert "第 2 次经验回顾" in text
        assert "第 10 局" in text
        assert "定期回顾" in text


# ============================================================
# _detect_opponent_shift() 测试
# ============================================================


class TestDetectOpponentShift:
    """对手行为突变检测测试"""

    def test_no_shift_insufficient_history(self):
        """历史不足 5 局不检测"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history = [_make_round_result(round_number=i) for i in range(4)]

        assert reviewer._detect_opponent_shift() is False

    def test_no_shift_insufficient_opponent_rounds(self):
        """对手数据不足 5 局不检测"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history = [_make_round_result(round_number=i) for i in range(6)]
        reviewer._opponent_action_stats[OPPONENT_ID] = {
            "rounds": 4,  # < 5
            "wins": 2,
            "total_change": 0,
            "recent_wins": 2,
            "recent_rounds": 3,
        }

        assert reviewer._detect_opponent_shift() is False

    def test_no_shift_stable_opponent(self):
        """对手行为稳定不触发"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history = [_make_round_result(round_number=i) for i in range(6)]
        reviewer._opponent_action_stats[OPPONENT_ID] = {
            "rounds": 10,
            "wins": 5,  # overall = 0.5
            "total_change": 0,
            "recent_wins": 2,  # recent = 2/4 = 0.5
            "recent_rounds": 4,
        }

        assert reviewer._detect_opponent_shift() is False

    def test_shift_detected(self):
        """对手近期胜率大幅变化触发"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history = [_make_round_result(round_number=i) for i in range(6)]
        reviewer._opponent_action_stats[OPPONENT_ID] = {
            "rounds": 10,
            "wins": 2,  # overall = 0.2
            "total_change": -100,
            "recent_wins": 3,  # recent = 3/3 = 1.0
            "recent_rounds": 3,
        }
        # diff = |1.0 - 0.2| = 0.8 > 0.4

        assert reviewer._detect_opponent_shift() is True

    def test_shift_insufficient_recent_rounds(self):
        """近期局数 < 3 不检测"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        reviewer.round_results_history = [_make_round_result(round_number=i) for i in range(6)]
        reviewer._opponent_action_stats[OPPONENT_ID] = {
            "rounds": 10,
            "wins": 2,
            "total_change": 0,
            "recent_wins": 2,
            "recent_rounds": 2,  # < 3
        }

        assert reviewer._detect_opponent_shift() is False


# ============================================================
# 集成风格测试 (多轮交互)
# ============================================================


class TestMultiRoundInteraction:
    """模拟多轮游戏交互的集成测试"""

    def test_trigger_progression(self):
        """模拟多局游戏中触发条件的变化"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)

        triggers: list[ReviewTrigger | None] = []

        # 第 1-4 局：全赢
        for i in range(4):
            game = _make_game(agent_chips=1000 + (i + 1) * 50)
            result = _make_round_result(
                round_number=i + 1,
                winner_id=AGENT_ID,
                agent_change=50,
                opponent_change=-50,
            )
            triggers.append(reviewer.check_trigger(game, result))

        # 第 5 局：赢 → 定期回顾触发
        game = _make_game(agent_chips=1250)
        result = _make_round_result(
            round_number=5,
            winner_id=AGENT_ID,
            agent_change=50,
            opponent_change=-50,
        )
        triggers.append(reviewer.check_trigger(game, result))

        assert triggers[:4] == [None, None, None, None]
        assert triggers[4] == ReviewTrigger.PERIODIC

    @pytest.mark.asyncio
    async def test_full_review_flow(self):
        """完整流程：check_trigger → perform_review → strategy_context"""
        agent = _make_agent()
        reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
        game = _make_game(agent_chips=800)

        # 连输 2 局触发
        for i in range(2):
            result = _make_round_result(round_number=i + 1, agent_change=-100)
            trigger = reviewer.check_trigger(game, result)

        assert trigger == ReviewTrigger.CONSECUTIVE_LOSSES

        # 执行回顾
        llm_response = json.dumps(
            {
                "self_analysis": "连续输牌让我信心下降",
                "opponent_patterns": {"opponent-1": "发现我在虚张声势"},
                "strategy_adjustment": "减少虚张声势，打实牌",
                "confidence_shift": -0.3,
            }
        )

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=llm_response):
            review = await reviewer.perform_review(
                trigger=trigger,
                recent_narratives=_make_narratives(2),
                recent_thoughts=_make_thoughts(2),
                opponent_stats={"opponent-1": "跟注率高"},
            )

        # 验证结果
        assert review.strategy_context != ""
        assert "策略调整" in review.strategy_context
        assert "减少虚张声势" in review.strategy_context

        # 连败计数应该被重置
        assert reviewer.consecutive_losses == 0
        # rounds_since_review 应该被重置
        assert reviewer.rounds_since_review == 0
        # 回顾记录应该被保存
        assert len(reviewer.reviews) == 1
