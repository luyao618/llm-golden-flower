"""规则引擎单元测试

覆盖场景：
- 暗注/明注操作费用差异
- 各种状态下的可用操作列表
- 筹码不足时的操作限制
- 比牌资格校验（需要看牌 + 有活跃对手 + 指定合法目标）
- 下注上限限制
- validate_action 全面校验
- 边界情况
"""

import pytest

from app.models.game import (
    GameAction,
    GameConfig,
    GamePhase,
    Player,
    PlayerStatus,
    PlayerType,
    RoundState,
)
from app.engine.rules import (
    get_action_cost,
    get_available_actions,
    get_call_cost,
    get_compare_cost,
    get_raise_cost,
    validate_action,
)


# ========== Fixtures ==========


def _make_player(
    player_id: str = "p1",
    name: str = "玩家1",
    chips: int = 1000,
    status: PlayerStatus = PlayerStatus.ACTIVE_BLIND,
    player_type: PlayerType = PlayerType.HUMAN,
) -> Player:
    """创建测试用玩家"""
    return Player(
        id=player_id,
        name=name,
        chips=chips,
        status=status,
        player_type=player_type,
    )


def _make_round_state(
    current_bet: int = 10,
    pot: int = 30,
    phase: GamePhase = GamePhase.BETTING,
    round_number: int = 1,
) -> RoundState:
    """创建测试用局面状态"""
    return RoundState(
        round_number=round_number,
        pot=pot,
        current_bet=current_bet,
        phase=phase,
    )


def _make_players_3() -> list[Player]:
    """创建 3 人游戏的玩家列表"""
    return [
        _make_player("p1", "玩家1", 1000, PlayerStatus.ACTIVE_BLIND, PlayerType.HUMAN),
        _make_player("p2", "AI-1", 1000, PlayerStatus.ACTIVE_BLIND, PlayerType.AI),
        _make_player("p3", "AI-2", 1000, PlayerStatus.ACTIVE_BLIND, PlayerType.AI),
    ]


# ========== 费用计算测试 ==========


class TestGetCallCost:
    """跟注费用计算测试"""

    def test_blind_player_call_cost(self):
        """暗注玩家跟注费用 = current_bet × 1"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.ACTIVE_BLIND)
        assert get_call_cost(rs, player) == 10

    def test_seen_player_call_cost(self):
        """明注玩家跟注费用 = current_bet × 2"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.ACTIVE_SEEN)
        assert get_call_cost(rs, player) == 20

    def test_blind_player_call_cost_high_bet(self):
        """暗注玩家在高注额时的跟注费用"""
        rs = _make_round_state(current_bet=50)
        player = _make_player(status=PlayerStatus.ACTIVE_BLIND)
        assert get_call_cost(rs, player) == 50

    def test_seen_player_call_cost_high_bet(self):
        """明注玩家在高注额时的跟注费用"""
        rs = _make_round_state(current_bet=50)
        player = _make_player(status=PlayerStatus.ACTIVE_SEEN)
        assert get_call_cost(rs, player) == 100

    def test_folded_player_call_cost(self):
        """已弃牌玩家的跟注费用为 0"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.FOLDED)
        assert get_call_cost(rs, player) == 0

    def test_out_player_call_cost(self):
        """出局玩家的跟注费用为 0"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.OUT)
        assert get_call_cost(rs, player) == 0


class TestGetRaiseCost:
    """加注费用计算测试"""

    def test_blind_player_raise_cost(self):
        """暗注玩家加注费用 = current_bet × 2"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.ACTIVE_BLIND)
        assert get_raise_cost(rs, player) == 20

    def test_seen_player_raise_cost(self):
        """明注玩家加注费用 = current_bet × 4"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.ACTIVE_SEEN)
        assert get_raise_cost(rs, player) == 40

    def test_blind_player_raise_cost_high_bet(self):
        """暗注玩家在高注额时的加注费用"""
        rs = _make_round_state(current_bet=50)
        player = _make_player(status=PlayerStatus.ACTIVE_BLIND)
        assert get_raise_cost(rs, player) == 100

    def test_seen_player_raise_cost_high_bet(self):
        """明注玩家在高注额时的加注费用"""
        rs = _make_round_state(current_bet=50)
        player = _make_player(status=PlayerStatus.ACTIVE_SEEN)
        assert get_raise_cost(rs, player) == 200

    def test_folded_player_raise_cost(self):
        """已弃牌玩家的加注费用为 0"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.FOLDED)
        assert get_raise_cost(rs, player) == 0

    def test_out_player_raise_cost(self):
        """出局玩家的加注费用为 0"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.OUT)
        assert get_raise_cost(rs, player) == 0


class TestGetCompareCost:
    """比牌费用计算测试"""

    def test_seen_player_compare_cost(self):
        """已看牌玩家比牌费用 = 跟注费用 = current_bet × 2"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.ACTIVE_SEEN)
        assert get_compare_cost(rs, player) == 20

    def test_seen_player_compare_cost_high_bet(self):
        """高注额时的比牌费用"""
        rs = _make_round_state(current_bet=50)
        player = _make_player(status=PlayerStatus.ACTIVE_SEEN)
        assert get_compare_cost(rs, player) == 100

    def test_blind_player_compare_cost(self):
        """暗注玩家不能比牌，费用为 0"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.ACTIVE_BLIND)
        assert get_compare_cost(rs, player) == 0

    def test_folded_player_compare_cost(self):
        """已弃牌玩家不能比牌，费用为 0"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.FOLDED)
        assert get_compare_cost(rs, player) == 0


class TestGetActionCost:
    """操作费用综合测试"""

    def test_fold_cost_is_zero(self):
        """弃牌不需要费用"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.ACTIVE_BLIND)
        assert get_action_cost(rs, player, GameAction.FOLD) == 0

    def test_check_cards_cost_is_zero(self):
        """看牌不需要费用"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.ACTIVE_BLIND)
        assert get_action_cost(rs, player, GameAction.CHECK_CARDS) == 0

    def test_call_cost_matches(self):
        """call 操作费用应与 get_call_cost 一致"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.ACTIVE_SEEN)
        assert get_action_cost(rs, player, GameAction.CALL) == get_call_cost(rs, player)

    def test_raise_cost_matches(self):
        """raise 操作费用应与 get_raise_cost 一致"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.ACTIVE_BLIND)
        assert get_action_cost(rs, player, GameAction.RAISE) == get_raise_cost(rs, player)

    def test_compare_cost_matches(self):
        """compare 操作费用应与 get_compare_cost 一致"""
        rs = _make_round_state(current_bet=10)
        player = _make_player(status=PlayerStatus.ACTIVE_SEEN)
        assert get_action_cost(rs, player, GameAction.COMPARE) == get_compare_cost(rs, player)


# ========== 可用操作测试 ==========


class TestGetAvailableActionsBlind:
    """暗注玩家可用操作测试"""

    def test_blind_player_normal(self):
        """暗注玩家正常情况：弃牌、跟注、看牌、加注"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        player = players[0]
        actions = get_available_actions(rs, player, players)
        assert GameAction.FOLD in actions
        assert GameAction.CALL in actions
        assert GameAction.CHECK_CARDS in actions
        assert GameAction.RAISE in actions
        assert GameAction.COMPARE not in actions

    def test_blind_player_cannot_compare(self):
        """暗注玩家不能比牌"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        player = players[0]  # ACTIVE_BLIND
        actions = get_available_actions(rs, player, players)
        assert GameAction.COMPARE not in actions

    def test_blind_player_insufficient_chips_for_raise(self):
        """暗注玩家筹码不足以加注"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].chips = 15  # 加注需要 20，筹码不够
        actions = get_available_actions(rs, players[0], players)
        assert GameAction.RAISE not in actions
        assert GameAction.CALL in actions  # 跟注只需 10，还够
        assert GameAction.CHECK_CARDS in actions

    def test_blind_player_insufficient_chips_for_call(self):
        """暗注玩家筹码不足以跟注"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].chips = 5  # 跟注需要 10，筹码不够
        actions = get_available_actions(rs, players[0], players)
        assert GameAction.CALL not in actions
        assert GameAction.RAISE not in actions
        assert GameAction.FOLD in actions
        assert GameAction.CHECK_CARDS in actions

    def test_blind_player_zero_chips(self):
        """暗注玩家筹码为 0 时只能弃牌或看牌"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].chips = 0
        actions = get_available_actions(rs, players[0], players)
        assert GameAction.FOLD in actions
        assert GameAction.CHECK_CARDS in actions
        assert GameAction.CALL not in actions
        assert GameAction.RAISE not in actions


class TestGetAvailableActionsSeen:
    """明注玩家可用操作测试"""

    def test_seen_player_normal(self):
        """明注玩家正常情况：弃牌、跟注、加注、比牌"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        actions = get_available_actions(rs, players[0], players)
        assert GameAction.FOLD in actions
        assert GameAction.CALL in actions
        assert GameAction.RAISE in actions
        assert GameAction.COMPARE in actions
        assert GameAction.CHECK_CARDS not in actions

    def test_seen_player_cannot_check_cards(self):
        """明注玩家不能再次看牌"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        actions = get_available_actions(rs, players[0], players)
        assert GameAction.CHECK_CARDS not in actions

    def test_seen_player_insufficient_chips_for_raise(self):
        """明注玩家筹码不足以加注"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        players[0].chips = 35  # 加注需要 40，不够
        actions = get_available_actions(rs, players[0], players)
        assert GameAction.RAISE not in actions
        assert GameAction.CALL in actions  # 跟注需要 20，够
        assert GameAction.COMPARE in actions  # 比牌需要 20，够

    def test_seen_player_insufficient_chips_for_call(self):
        """明注玩家筹码不足以跟注"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        players[0].chips = 15  # 跟注需要 20，不够
        actions = get_available_actions(rs, players[0], players)
        assert GameAction.CALL not in actions
        assert GameAction.RAISE not in actions
        assert GameAction.COMPARE not in actions  # 比牌也需要 20
        assert GameAction.FOLD in actions

    def test_seen_player_insufficient_chips_for_compare(self):
        """明注玩家筹码足以跟注但不足以比牌（实际上比牌=跟注费用，同时满足或同时不满足）"""
        # 比牌费用 = 跟注费用，所以如果够跟注就够比牌
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        players[0].chips = 20  # 跟注和比牌都需要 20，刚好够
        actions = get_available_actions(rs, players[0], players)
        assert GameAction.CALL in actions
        assert GameAction.COMPARE in actions

    def test_seen_player_no_compare_target(self):
        """没有可比牌对手时不能比牌（其他人都弃牌了）"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        players[1].status = PlayerStatus.FOLDED
        players[2].status = PlayerStatus.FOLDED
        actions = get_available_actions(rs, players[0], players)
        # 只剩自己一个活跃玩家，没有比牌对象
        assert GameAction.COMPARE not in actions


class TestGetAvailableActionsInactive:
    """不活跃玩家操作测试"""

    def test_folded_player_no_actions(self):
        """已弃牌玩家没有任何操作"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.FOLDED
        actions = get_available_actions(rs, players[0], players)
        assert actions == []

    def test_out_player_no_actions(self):
        """出局玩家没有任何操作"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.OUT
        actions = get_available_actions(rs, players[0], players)
        assert actions == []


class TestGetAvailableActionsPhase:
    """游戏阶段限制测试"""

    def test_waiting_phase_no_actions(self):
        """等待阶段不允许操作"""
        rs = _make_round_state(current_bet=10, phase=GamePhase.WAITING)
        players = _make_players_3()
        actions = get_available_actions(rs, players[0], players)
        assert actions == []

    def test_dealing_phase_no_actions(self):
        """发牌阶段不允许操作"""
        rs = _make_round_state(current_bet=10, phase=GamePhase.DEALING)
        players = _make_players_3()
        actions = get_available_actions(rs, players[0], players)
        assert actions == []

    def test_settlement_phase_no_actions(self):
        """结算阶段不允许操作"""
        rs = _make_round_state(current_bet=10, phase=GamePhase.SETTLEMENT)
        players = _make_players_3()
        actions = get_available_actions(rs, players[0], players)
        assert actions == []


class TestGetAvailableActionsMaxBet:
    """下注上限限制测试"""

    def test_raise_blocked_at_max_bet(self):
        """当前注额已达上限时不能加注"""
        config = GameConfig(max_bet=200)
        rs = _make_round_state(current_bet=200)  # 已达上限
        players = _make_players_3()
        actions = get_available_actions(rs, players[0], players, config)
        assert GameAction.RAISE not in actions
        # 但跟注仍然可以（如果筹码够）
        assert GameAction.CALL in actions

    def test_raise_allowed_below_max_bet(self):
        """当前注额未达上限时可以加注"""
        config = GameConfig(max_bet=200)
        rs = _make_round_state(current_bet=50)  # 加注后变为 100，未达上限
        players = _make_players_3()
        actions = get_available_actions(rs, players[0], players, config)
        assert GameAction.RAISE in actions

    def test_raise_blocked_when_next_bet_exceeds_max(self):
        """加注后注额会超过上限时不能加注"""
        config = GameConfig(max_bet=200)
        rs = _make_round_state(current_bet=150)  # 加注后 current_bet 变 300 > 200
        players = _make_players_3()
        actions = get_available_actions(rs, players[0], players, config)
        assert GameAction.RAISE not in actions

    def test_no_config_means_no_max_bet_limit(self):
        """不传 config 时没有下注上限限制"""
        rs = _make_round_state(current_bet=1000)
        players = _make_players_3()
        # 确保筹码足够加注（暗注加注 = 1000 × 2 = 2000）
        players[0].chips = 5000
        actions = get_available_actions(rs, players[0], players, config=None)
        assert GameAction.RAISE in actions


# ========== validate_action 测试 ==========


class TestValidateAction:
    """操作合法性校验测试"""

    def test_valid_fold(self):
        """弃牌始终合法"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        assert validate_action(rs, players[0], GameAction.FOLD, players) is True

    def test_valid_call_blind(self):
        """暗注玩家跟注合法"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        assert validate_action(rs, players[0], GameAction.CALL, players) is True

    def test_valid_raise_blind(self):
        """暗注玩家加注合法"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        assert validate_action(rs, players[0], GameAction.RAISE, players) is True

    def test_valid_check_cards_blind(self):
        """暗注玩家看牌合法"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        assert validate_action(rs, players[0], GameAction.CHECK_CARDS, players) is True

    def test_invalid_compare_blind(self):
        """暗注玩家不能比牌"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        assert (
            validate_action(rs, players[0], GameAction.COMPARE, players, target_id=players[1].id)
            is False
        )

    def test_valid_compare_seen(self):
        """明注玩家比牌合法（指定合法目标）"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        assert (
            validate_action(rs, players[0], GameAction.COMPARE, players, target_id=players[1].id)
            is True
        )

    def test_compare_without_target(self):
        """比牌但不指定目标，非法"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        assert validate_action(rs, players[0], GameAction.COMPARE, players, target_id=None) is False

    def test_compare_with_self(self):
        """不能和自己比牌"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        assert (
            validate_action(rs, players[0], GameAction.COMPARE, players, target_id=players[0].id)
            is False
        )

    def test_compare_with_folded_target(self):
        """不能和已弃牌的玩家比牌"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        players[1].status = PlayerStatus.FOLDED
        assert (
            validate_action(rs, players[0], GameAction.COMPARE, players, target_id=players[1].id)
            is False
        )

    def test_compare_with_out_target(self):
        """不能和出局玩家比牌"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        players[1].status = PlayerStatus.OUT
        assert (
            validate_action(rs, players[0], GameAction.COMPARE, players, target_id=players[1].id)
            is False
        )

    def test_compare_with_nonexistent_target(self):
        """比牌目标不存在，非法"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        assert (
            validate_action(rs, players[0], GameAction.COMPARE, players, target_id="nonexistent_id")
            is False
        )

    def test_invalid_check_cards_seen(self):
        """明注玩家不能再看牌"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.ACTIVE_SEEN
        assert validate_action(rs, players[0], GameAction.CHECK_CARDS, players) is False

    def test_invalid_action_folded_player(self):
        """已弃牌玩家不能执行任何操作"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.FOLDED
        for action in GameAction:
            assert validate_action(rs, players[0], action, players) is False

    def test_invalid_action_out_player(self):
        """出局玩家不能执行任何操作"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].status = PlayerStatus.OUT
        for action in GameAction:
            assert validate_action(rs, players[0], action, players) is False

    def test_invalid_raise_insufficient_chips(self):
        """筹码不足时加注非法"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].chips = 15  # 暗注加注需要 20
        assert validate_action(rs, players[0], GameAction.RAISE, players) is False

    def test_invalid_call_insufficient_chips(self):
        """筹码不足时跟注非法"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()
        players[0].chips = 5  # 暗注跟注需要 10
        assert validate_action(rs, players[0], GameAction.CALL, players) is False

    def test_validate_with_max_bet_config(self):
        """带下注上限配置的校验"""
        config = GameConfig(max_bet=200)
        rs = _make_round_state(current_bet=200)
        players = _make_players_3()
        # 已达上限，不能加注
        assert validate_action(rs, players[0], GameAction.RAISE, players, config) is False
        # 但跟注合法
        assert validate_action(rs, players[0], GameAction.CALL, players, config) is True


# ========== 综合场景测试 ==========


class TestComplexScenarios:
    """复杂游戏场景测试"""

    def test_two_player_game(self):
        """2 人游戏场景"""
        rs = _make_round_state(current_bet=10)
        players = [
            _make_player("p1", "玩家1", 1000, PlayerStatus.ACTIVE_SEEN),
            _make_player("p2", "AI-1", 1000, PlayerStatus.ACTIVE_BLIND),
        ]
        # 明注玩家应有比牌选项
        actions_p1 = get_available_actions(rs, players[0], players)
        assert GameAction.COMPARE in actions_p1

        # 暗注玩家不应有比牌选项
        actions_p2 = get_available_actions(rs, players[1], players)
        assert GameAction.COMPARE not in actions_p2

    def test_last_man_standing(self):
        """只剩一个活跃玩家（其他人都弃牌了）"""
        rs = _make_round_state(current_bet=10)
        players = [
            _make_player("p1", "玩家1", 1000, PlayerStatus.ACTIVE_SEEN),
            _make_player("p2", "AI-1", 500, PlayerStatus.FOLDED),
            _make_player("p3", "AI-2", 500, PlayerStatus.FOLDED),
        ]
        actions = get_available_actions(rs, players[0], players)
        # 没有比牌对象
        assert GameAction.COMPARE not in actions
        # 但其他操作仍可用
        assert GameAction.FOLD in actions
        assert GameAction.CALL in actions

    def test_multiple_raises_increase_cost(self):
        """多次加注后费用递增"""
        # 初始 current_bet = 10
        rs = _make_round_state(current_bet=10)
        player_blind = _make_player(status=PlayerStatus.ACTIVE_BLIND)
        player_seen = _make_player(status=PlayerStatus.ACTIVE_SEEN)

        # 第一轮
        assert get_call_cost(rs, player_blind) == 10
        assert get_raise_cost(rs, player_blind) == 20
        assert get_call_cost(rs, player_seen) == 20
        assert get_raise_cost(rs, player_seen) == 40

        # 假设有人加注后 current_bet 变为 20
        rs.current_bet = 20
        assert get_call_cost(rs, player_blind) == 20
        assert get_raise_cost(rs, player_blind) == 40
        assert get_call_cost(rs, player_seen) == 40
        assert get_raise_cost(rs, player_seen) == 80

        # 再次加注后 current_bet 变为 40
        rs.current_bet = 40
        assert get_call_cost(rs, player_blind) == 40
        assert get_raise_cost(rs, player_blind) == 80
        assert get_call_cost(rs, player_seen) == 80
        assert get_raise_cost(rs, player_seen) == 160

    def test_compare_cost_equals_call_cost(self):
        """比牌费用始终等于跟注费用"""
        for bet in [10, 20, 50, 100]:
            rs = _make_round_state(current_bet=bet)
            player = _make_player(status=PlayerStatus.ACTIVE_SEEN)
            assert get_compare_cost(rs, player) == get_call_cost(rs, player)

    def test_mixed_status_players(self):
        """混合状态玩家场景"""
        rs = _make_round_state(current_bet=10)
        players = [
            _make_player("p1", "玩家1", 1000, PlayerStatus.ACTIVE_SEEN),
            _make_player("p2", "AI-1", 500, PlayerStatus.ACTIVE_BLIND),
            _make_player("p3", "AI-2", 500, PlayerStatus.FOLDED),
            _make_player("p4", "AI-3", 0, PlayerStatus.OUT),
        ]
        # 明注玩家可以比牌（只能选 p2）
        actions = get_available_actions(rs, players[0], players)
        assert GameAction.COMPARE in actions

        # 验证比牌只能选活跃玩家
        assert (
            validate_action(rs, players[0], GameAction.COMPARE, players, target_id=players[1].id)
            is True
        )
        assert (
            validate_action(rs, players[0], GameAction.COMPARE, players, target_id=players[2].id)
            is False
        )
        assert (
            validate_action(rs, players[0], GameAction.COMPARE, players, target_id=players[3].id)
            is False
        )

    def test_exact_chips_for_action(self):
        """筹码刚好等于费用时应该可以操作"""
        rs = _make_round_state(current_bet=10)
        players = _make_players_3()

        # 暗注玩家刚好够跟注
        players[0].chips = 10
        assert GameAction.CALL in get_available_actions(rs, players[0], players)

        # 暗注玩家刚好够加注
        players[0].chips = 20
        assert GameAction.RAISE in get_available_actions(rs, players[0], players)

        # 明注玩家刚好够跟注
        players[1].status = PlayerStatus.ACTIVE_SEEN
        players[1].chips = 20
        assert GameAction.CALL in get_available_actions(rs, players[1], players)

        # 明注玩家刚好够加注
        players[1].chips = 40
        assert GameAction.RAISE in get_available_actions(rs, players[1], players)

    def test_six_player_game(self):
        """6 人游戏场景"""
        rs = _make_round_state(current_bet=10)
        players = [
            _make_player(f"p{i}", f"Player{i}", 1000, PlayerStatus.ACTIVE_BLIND) for i in range(6)
        ]
        players[0].status = PlayerStatus.ACTIVE_SEEN

        actions = get_available_actions(rs, players[0], players)
        # 有 5 个可比牌对手
        assert GameAction.COMPARE in actions

        # 弃牌 3 人后仍有比牌对象
        players[1].status = PlayerStatus.FOLDED
        players[2].status = PlayerStatus.FOLDED
        players[3].status = PlayerStatus.FOLDED
        actions = get_available_actions(rs, players[0], players)
        assert GameAction.COMPARE in actions  # 还有 p4, p5

    def test_high_stakes_scenario(self):
        """高注额场景下的费用计算"""
        rs = _make_round_state(current_bet=100)
        player_blind = _make_player(chips=500, status=PlayerStatus.ACTIVE_BLIND)
        player_seen = _make_player(chips=500, status=PlayerStatus.ACTIVE_SEEN)

        assert get_call_cost(rs, player_blind) == 100
        assert get_raise_cost(rs, player_blind) == 200
        assert get_call_cost(rs, player_seen) == 200
        assert get_raise_cost(rs, player_seen) == 400
        assert get_compare_cost(rs, player_seen) == 200

        # 明注玩家筹码 300，不够加注（需要 400），但够跟注和比牌（需要 200）
        player_seen_low = _make_player("ps", "明注穷", 300, PlayerStatus.ACTIVE_SEEN)
        players = [player_seen_low, _make_player("p2", "AI", 500, PlayerStatus.ACTIVE_BLIND)]
        actions = get_available_actions(rs, player_seen_low, players)
        assert GameAction.RAISE not in actions
        assert GameAction.CALL in actions
        assert GameAction.COMPARE in actions
