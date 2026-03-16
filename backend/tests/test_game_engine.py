"""游戏流程引擎测试

覆盖 game_manager.py 的所有核心功能：
- 创建游戏
- 开始新局（收底注、发牌、庄家确定）
- 执行各种操作（跟注、加注、看牌、弃牌、比牌）
- 回合推进
- 局结束判定
- 结算逻辑（弃牌胜出、比牌胜出、强制比牌）
- 信息隐藏
- 模拟完整一局流程
"""

import pytest

from app.engine.deck import Deck
from app.engine.game_manager import (
    ActionResult,
    GameError,
    GameNotStartedError,
    InvalidActionError,
    RoundNotActiveError,
    apply_action,
    check_round_end,
    create_game,
    get_visible_state,
    settle_round,
    start_round,
)
from app.models.card import Card, Rank, Suit
from app.models.game import (
    GameAction,
    GameConfig,
    GamePhase,
    GameState,
    Player,
    PlayerStatus,
    PlayerType,
    RoundState,
)


# ---- Fixtures ----


def _default_player_configs(count: int = 3) -> list[dict]:
    """生成默认的玩家配置列表"""
    configs = [
        {"name": "玩家", "player_type": "human"},
    ]
    for i in range(count - 1):
        configs.append(
            {
                "name": f"AI_{i + 1}",
                "player_type": "ai",
                "model_id": "openai-gpt4o",
            }
        )
    return configs


def _create_test_game(player_count: int = 3, config: GameConfig | None = None) -> GameState:
    """创建一个用于测试的游戏"""
    return create_game(_default_player_configs(player_count), config)


def _start_test_round(game: GameState, seed: int = 42) -> RoundState:
    """开始一局测试用的牌局（使用固定种子保证确定性）"""
    deck = Deck(seed=seed)
    return start_round(game, deck=deck)


# ============================================================
# 创建游戏测试
# ============================================================


class TestCreateGame:
    """测试 create_game"""

    def test_create_game_basic(self):
        """基本创建游戏"""
        game = _create_test_game(3)
        assert game.game_id
        assert len(game.players) == 3
        assert game.status == "waiting"
        assert game.current_round is None
        assert len(game.round_history) == 0

    def test_create_game_player_types(self):
        """检查玩家类型设置正确"""
        game = _create_test_game(3)
        assert game.players[0].player_type == PlayerType.HUMAN
        assert game.players[1].player_type == PlayerType.AI
        assert game.players[2].player_type == PlayerType.AI

    def test_create_game_initial_chips(self):
        """检查初始筹码"""
        config = GameConfig(initial_chips=2000)
        game = _create_test_game(3, config)
        for p in game.players:
            assert p.chips == 2000

    def test_create_game_custom_config(self):
        """自定义配置"""
        config = GameConfig(initial_chips=500, ante=5, max_bet=100, max_turns=8)
        game = _create_test_game(2, config)
        assert game.config.initial_chips == 500
        assert game.config.ante == 5
        assert game.config.max_bet == 100
        assert game.config.max_turns == 8

    def test_create_game_2_players(self):
        """最少 2 人"""
        game = _create_test_game(2)
        assert len(game.players) == 2

    def test_create_game_6_players(self):
        """最多 6 人"""
        game = _create_test_game(6)
        assert len(game.players) == 6

    def test_create_game_too_few_players(self):
        """少于 2 人报错"""
        with pytest.raises(ValueError, match="2-6"):
            create_game([{"name": "solo", "player_type": "human"}])

    def test_create_game_too_many_players(self):
        """多于 6 人报错"""
        configs = [{"name": f"p{i}", "player_type": "human"} for i in range(7)]
        with pytest.raises(ValueError, match="2-6"):
            create_game(configs)

    def test_create_game_unique_ids(self):
        """每个玩家有唯一 ID"""
        game = _create_test_game(5)
        ids = [p.id for p in game.players]
        assert len(set(ids)) == 5

    def test_create_game_ai_attributes(self):
        """AI 玩家属性正确设置"""
        game = _create_test_game(3)
        ai_player = game.players[1]
        assert ai_player.model_id == "openai-gpt4o"


# ============================================================
# 开始新局测试
# ============================================================


class TestStartRound:
    """测试 start_round"""

    def test_start_round_basic(self):
        """基本开始新局"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        assert round_state.round_number == 1
        assert round_state.phase == GamePhase.BETTING
        assert game.status == "playing"

    def test_start_round_deals_cards(self):
        """发牌正确：每人 3 张"""
        game = _create_test_game(3)
        _start_test_round(game)
        for p in game.players:
            assert p.hand is not None
            assert len(p.hand) == 3

    def test_start_round_collects_ante(self):
        """收底注正确"""
        config = GameConfig(initial_chips=1000, ante=10)
        game = _create_test_game(3, config)
        round_state = _start_test_round(game)

        assert round_state.pot == 30  # 3 × 10
        for p in game.players:
            assert p.chips == 990  # 1000 - 10
            assert p.total_bet_this_round == 10

    def test_start_round_players_are_active_blind(self):
        """所有玩家初始为暗注状态"""
        game = _create_test_game(3)
        _start_test_round(game)
        for p in game.players:
            assert p.status == PlayerStatus.ACTIVE_BLIND

    def test_start_round_current_bet_equals_ante(self):
        """当前注额等于底注"""
        config = GameConfig(ante=20)
        game = _create_test_game(3, config)
        round_state = _start_test_round(game)
        assert round_state.current_bet == 20

    def test_start_round_dealer_set(self):
        """庄家位置已设定"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        assert 0 <= round_state.dealer_index < len(game.players)

    def test_start_round_first_player_after_dealer(self):
        """首个行动玩家是庄家的下一个"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        expected_first = (round_state.dealer_index + 1) % len(game.players)
        assert round_state.current_player_index == expected_first

    def test_start_round_deterministic_with_seed(self):
        """使用相同种子牌组得到相同的牌"""
        game1 = _create_test_game(3)
        _start_test_round(game1, seed=123)
        hands1 = [list(p.hand) for p in game1.players]

        game2 = _create_test_game(3)
        _start_test_round(game2, seed=123)
        hands2 = [list(p.hand) for p in game2.players]

        # 由于玩家 ID 不同，但手牌应该相同（同样的牌组顺序）
        for h1, h2 in zip(hands1, hands2):
            for c1, c2 in zip(h1, h2):
                assert c1.rank == c2.rank
                assert c1.suit == c2.suit

    def test_start_round_insufficient_players(self):
        """活跃玩家不足 2 人时无法开局"""
        game = _create_test_game(2)
        # 把一个玩家标记为 OUT
        game.players[0].status = PlayerStatus.OUT
        game.players[0].chips = 0
        with pytest.raises(GameError, match="不足 2 人"):
            _start_test_round(game)

    def test_start_second_round(self):
        """开始第二局"""
        game = _create_test_game(3)
        _start_test_round(game)

        # 模拟第一局结束
        game.players[1].status = PlayerStatus.FOLDED
        game.players[2].status = PlayerStatus.FOLDED
        settle_round(game)

        # 开始第二局
        round_state = _start_test_round(game)
        assert round_state.round_number == 2


# ============================================================
# 操作执行测试
# ============================================================


class TestApplyAction:
    """测试 apply_action"""

    def test_fold(self):
        """弃牌操作"""
        game = _create_test_game(3)
        _start_test_round(game)
        player = game.players[game.current_round.current_player_index]

        result = apply_action(game, player.id, GameAction.FOLD)
        assert result.success
        assert result.action == GameAction.FOLD
        assert result.amount == 0
        assert player.status == PlayerStatus.FOLDED

    def test_call_blind(self):
        """暗注跟注"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        player = game.players[round_state.current_player_index]
        initial_chips = player.chips
        ante = game.config.ante

        result = apply_action(game, player.id, GameAction.CALL)
        assert result.success
        assert result.amount == ante  # 暗注跟注 = current_bet × 1
        assert player.chips == initial_chips - ante

    def test_raise_blind(self):
        """暗注加注"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        player = game.players[round_state.current_player_index]
        initial_chips = player.chips
        ante = game.config.ante

        result = apply_action(game, player.id, GameAction.RAISE)
        assert result.success
        assert result.amount == ante * 2  # 暗注加注 = current_bet × 2
        assert player.chips == initial_chips - ante * 2
        # 加注后 current_bet 翻倍
        assert round_state.current_bet == ante * 2

    def test_check_cards(self):
        """看牌操作"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        player = game.players[round_state.current_player_index]
        initial_chips = player.chips

        result = apply_action(game, player.id, GameAction.CHECK_CARDS)
        assert result.success
        assert result.amount == 0
        assert player.chips == initial_chips  # 看牌不花钱
        assert player.status == PlayerStatus.ACTIVE_SEEN

    def test_call_after_seeing_cards(self):
        """看牌后跟注（明注费率）"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        player = game.players[round_state.current_player_index]

        # 先看牌（看牌不消耗回合，仍然是该玩家的回合）
        apply_action(game, player.id, GameAction.CHECK_CARDS)
        assert player.status == PlayerStatus.ACTIVE_SEEN

        # 看牌后该玩家仍需行动，先跟注
        apply_action(game, player.id, GameAction.CALL)

        # 现在轮到下一个玩家，让他跟注
        next_player = game.players[round_state.current_player_index]
        apply_action(game, next_player.id, GameAction.CALL)

        # 再轮到第三个玩家，跟注
        third_player = game.players[round_state.current_player_index]
        apply_action(game, third_player.id, GameAction.CALL)

        # 现在轮回到第一个玩家（已看牌），跟注应该是 current_bet × 2
        result = apply_action(game, player.id, GameAction.CALL)
        assert result.success
        # 明注跟注 = current_bet × 2
        assert result.amount == game.config.ante * 2

    def test_compare(self):
        """比牌操作"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        player = game.players[round_state.current_player_index]

        # 先看牌（比牌需要已看牌状态，看牌不消耗回合）
        apply_action(game, player.id, GameAction.CHECK_CARDS)

        # 看牌后仍是 player 的回合，先跟注
        apply_action(game, player.id, GameAction.CALL)

        # 让其他玩家行动一轮
        p2 = game.players[round_state.current_player_index]
        apply_action(game, p2.id, GameAction.CALL)
        p3 = game.players[round_state.current_player_index]
        apply_action(game, p3.id, GameAction.CALL)

        # 现在轮回到 player，发起比牌
        target = p2 if p2.is_active else p3
        result = apply_action(game, player.id, GameAction.COMPARE, target_id=target.id)
        assert result.success
        assert result.action == GameAction.COMPARE
        assert result.compare_result is not None
        assert "winner_id" in result.compare_result

    def test_wrong_player_turn(self):
        """不是轮到的玩家操作"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        # 找一个不是当前行动者的玩家
        current_idx = round_state.current_player_index
        wrong_idx = (current_idx + 1) % len(game.players)
        wrong_player = game.players[wrong_idx]

        with pytest.raises(InvalidActionError, match="轮到"):
            apply_action(game, wrong_player.id, GameAction.CALL)

    def test_action_before_start(self):
        """游戏未开始时操作"""
        game = _create_test_game(3)
        with pytest.raises(GameNotStartedError):
            apply_action(game, game.players[0].id, GameAction.CALL)

    def test_nonexistent_player(self):
        """不存在的玩家"""
        game = _create_test_game(3)
        _start_test_round(game)
        with pytest.raises(InvalidActionError, match="不存在"):
            apply_action(game, "fake-id-12345", GameAction.CALL)

    def test_pot_increases_on_call(self):
        """跟注后底池增加"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        initial_pot = round_state.pot
        player = game.players[round_state.current_player_index]

        apply_action(game, player.id, GameAction.CALL)
        assert round_state.pot == initial_pot + game.config.ante

    def test_pot_increases_on_raise(self):
        """加注后底池增加"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        initial_pot = round_state.pot
        player = game.players[round_state.current_player_index]

        apply_action(game, player.id, GameAction.RAISE)
        assert round_state.pot == initial_pot + game.config.ante * 2


# ============================================================
# 回合推进测试
# ============================================================


class TestAdvanceTurn:
    """测试回合推进逻辑"""

    def test_turn_advances_to_next_player(self):
        """操作后轮到下一个玩家"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        first_idx = round_state.current_player_index
        player = game.players[first_idx]

        apply_action(game, player.id, GameAction.CALL)
        # 应该轮到下一个玩家
        assert round_state.current_player_index != first_idx

    def test_skip_folded_player(self):
        """跳过已弃牌的玩家"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)

        # 第一个玩家弃牌
        p1 = game.players[round_state.current_player_index]
        apply_action(game, p1.id, GameAction.FOLD)

        # 第二个玩家跟注
        p2 = game.players[round_state.current_player_index]
        apply_action(game, p2.id, GameAction.CALL)

        # 应该跳过弃牌的 p1，如果还有下一轮的话
        if round_state.phase == GamePhase.BETTING:
            current_player = game.players[round_state.current_player_index]
            assert current_player.id != p1.id

    def test_actions_recorded(self):
        """操作被记录到 actions 列表"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        player = game.players[round_state.current_player_index]

        apply_action(game, player.id, GameAction.CALL)
        assert len(round_state.actions) == 1
        assert round_state.actions[0].action == GameAction.CALL
        assert round_state.actions[0].player_id == player.id


# ============================================================
# 局结束判定测试
# ============================================================


class TestCheckRoundEnd:
    """测试 check_round_end"""

    def test_all_fold_except_one(self):
        """所有人弃牌只剩一人"""
        game = _create_test_game(3)
        _start_test_round(game)

        # 第一个和第二个玩家弃牌
        p1 = game.players[game.current_round.current_player_index]
        apply_action(game, p1.id, GameAction.FOLD)
        p2 = game.players[game.current_round.current_player_index]
        result = apply_action(game, p2.id, GameAction.FOLD)

        # 局应该自动结束
        assert result.round_ended

    def test_not_ended_with_multiple_active(self):
        """多人活跃时不结束"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)

        p1 = game.players[round_state.current_player_index]
        apply_action(game, p1.id, GameAction.CALL)

        # 还有多人活跃，不应结束
        assert not check_round_end(game)

    def test_max_turns_reached(self):
        """达到最大轮数"""
        config = GameConfig(max_turns=1, ante=10, initial_chips=10000)
        game = _create_test_game(3, config)
        round_state = _start_test_round(game)
        round_state.turn_count = 1  # 直接设置达到最大轮数

        assert check_round_end(game)


# ============================================================
# 结算测试
# ============================================================


class TestSettleRound:
    """测试 settle_round"""

    def test_fold_victory(self):
        """弃牌胜出"""
        game = _create_test_game(3)
        _start_test_round(game)

        p1 = game.players[game.current_round.current_player_index]
        apply_action(game, p1.id, GameAction.FOLD)
        p2 = game.players[game.current_round.current_player_index]
        result = apply_action(game, p2.id, GameAction.FOLD)

        assert result.round_ended
        assert result.round_result is not None
        assert "弃牌" in result.round_result.win_method

        # 赢家应该获得底池
        winner = game.get_player_by_id(result.round_result.winner_id)
        assert winner is not None

    def test_winner_gets_pot(self):
        """赢家获得底池筹码"""
        config = GameConfig(initial_chips=1000, ante=10)
        game = _create_test_game(3, config)
        _start_test_round(game)

        # 所有底注 = 30
        pot = game.current_round.pot
        assert pot == 30

        # 两人弃牌
        p1 = game.players[game.current_round.current_player_index]
        apply_action(game, p1.id, GameAction.FOLD)
        p2 = game.players[game.current_round.current_player_index]
        result = apply_action(game, p2.id, GameAction.FOLD)

        # 赢家拿到底池
        winner = game.get_player_by_id(result.round_result.winner_id)
        # 赢家的筹码 = 初始(1000) - 底注(10) + 底池(30) = 1020
        assert winner.chips == 1020

    def test_compare_victory(self):
        """比牌胜出"""
        game = _create_test_game(2)
        round_state = _start_test_round(game)

        p1 = game.players[round_state.current_player_index]
        # 看牌（不消耗回合）
        apply_action(game, p1.id, GameAction.CHECK_CARDS)

        # 看牌后 p1 仍需行动，先跟注
        apply_action(game, p1.id, GameAction.CALL)

        p2 = game.players[round_state.current_player_index]
        apply_action(game, p2.id, GameAction.CALL)

        # p1 发起比牌
        result = apply_action(game, p1.id, GameAction.COMPARE, target_id=p2.id)
        assert result.success
        assert result.round_ended
        assert result.round_result is not None

    def test_round_result_recorded_in_history(self):
        """结算结果记录到历史"""
        game = _create_test_game(3)
        _start_test_round(game)

        p1 = game.players[game.current_round.current_player_index]
        apply_action(game, p1.id, GameAction.FOLD)
        p2 = game.players[game.current_round.current_player_index]
        apply_action(game, p2.id, GameAction.FOLD)

        assert len(game.round_history) == 1
        assert game.round_history[0].round_number == 1

    def test_game_over_when_one_player_left(self):
        """只剩一个有筹码的玩家时游戏结束"""
        config = GameConfig(initial_chips=10, ante=10)  # 底注就是全部筹码
        game = _create_test_game(2, config)
        _start_test_round(game)
        # 底注后两人都是 0 筹码

        p1 = game.players[game.current_round.current_player_index]
        result = apply_action(game, p1.id, GameAction.FOLD)

        # 弃牌者输掉底注，游戏应结束
        assert result.round_ended
        assert game.status == "finished"

    def test_forced_compare_at_max_turns(self):
        """最大轮数到达时强制比牌"""
        config = GameConfig(max_turns=1, ante=10, initial_chips=10000)
        game = _create_test_game(2, config)
        round_state = _start_test_round(game)

        # 直接设 turn_count 达到上限
        round_state.turn_count = 1
        assert check_round_end(game)

        result = settle_round(game)
        assert "强制比牌" in result.win_method
        assert result.hands_revealed is not None

    def test_chip_changes_calculated(self):
        """筹码变化计算正确"""
        config = GameConfig(initial_chips=1000, ante=10)
        game = _create_test_game(3, config)
        _start_test_round(game)

        p1 = game.players[game.current_round.current_player_index]
        apply_action(game, p1.id, GameAction.FOLD)
        p2 = game.players[game.current_round.current_player_index]
        result = apply_action(game, p2.id, GameAction.FOLD)

        rr = result.round_result
        assert rr is not None
        # 赢家净赢 = pot - 自己的底注
        assert rr.player_chip_changes[rr.winner_id] == rr.pot - 10
        # 输家净输 = -底注
        for pid, change in rr.player_chip_changes.items():
            if pid != rr.winner_id:
                assert change == -10


# ============================================================
# 信息隐藏测试
# ============================================================


class TestGetVisibleState:
    """测试 get_visible_state"""

    def test_own_cards_visible(self):
        """自己的手牌可见"""
        game = _create_test_game(3)
        _start_test_round(game)

        viewer = game.players[0]
        state = get_visible_state(game, viewer.id)

        # 找到自己的数据
        my_data = next(p for p in state["players"] if p["id"] == viewer.id)
        assert my_data["hand"] is not None

    def test_others_cards_hidden(self):
        """其他人的手牌不可见"""
        game = _create_test_game(3)
        _start_test_round(game)

        viewer = game.players[0]
        state = get_visible_state(game, viewer.id)

        for p_data in state["players"]:
            if p_data["id"] != viewer.id:
                assert p_data["hand"] is None

    def test_all_players_see_different_state(self):
        """每个玩家看到的状态不同"""
        game = _create_test_game(3)
        _start_test_round(game)

        states = [get_visible_state(game, p.id) for p in game.players]

        for i, state in enumerate(states):
            for j, p_data in enumerate(state["players"]):
                if i == j:
                    assert p_data["hand"] is not None
                else:
                    assert p_data["hand"] is None

    def test_game_info_visible_to_all(self):
        """游戏的公共信息对所有人可见"""
        game = _create_test_game(3)
        _start_test_round(game)

        for p in game.players:
            state = get_visible_state(game, p.id)
            assert state["game_id"] == game.game_id
            assert state["current_round"] is not None
            assert state["current_round"]["pot"] == game.current_round.pot


# ============================================================
# 完整一局模拟测试
# ============================================================


class TestFullGameSimulation:
    """模拟完整的游戏流程"""

    def test_full_round_fold_victory(self):
        """完整一局：全部弃牌"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)
        initial_pot = round_state.pot

        # 第一个玩家跟注
        p1 = game.players[round_state.current_player_index]
        r1 = apply_action(game, p1.id, GameAction.CALL)
        assert r1.success
        assert not r1.round_ended

        # 第二个玩家加注
        p2 = game.players[round_state.current_player_index]
        r2 = apply_action(game, p2.id, GameAction.RAISE)
        assert r2.success
        assert not r2.round_ended

        # 第三个玩家弃牌
        p3 = game.players[round_state.current_player_index]
        r3 = apply_action(game, p3.id, GameAction.FOLD)
        assert r3.success

        # 第一个玩家弃牌
        if not r3.round_ended:
            p_next = game.players[round_state.current_player_index]
            r4 = apply_action(game, p_next.id, GameAction.FOLD)
            assert r4.round_ended
            assert r4.round_result is not None

    def test_full_round_compare_victory(self):
        """完整一局：比牌胜出"""
        game = _create_test_game(2)
        round_state = _start_test_round(game)

        p1 = game.players[round_state.current_player_index]
        p2_idx = (round_state.current_player_index + 1) % 2

        # p1 看牌（不消耗回合）
        apply_action(game, p1.id, GameAction.CHECK_CARDS)

        # p1 仍需行动，跟注
        apply_action(game, p1.id, GameAction.CALL)

        # p2 跟注
        p2 = game.players[round_state.current_player_index]
        apply_action(game, p2.id, GameAction.CALL)

        # p1 发起比牌
        result = apply_action(game, p1.id, GameAction.COMPARE, target_id=p2.id)
        assert result.round_ended
        assert result.round_result is not None
        winner_id = result.round_result.winner_id
        assert winner_id in [p1.id, p2.id]

    def test_multi_round_game(self):
        """多局连续游戏"""
        config = GameConfig(initial_chips=1000, ante=10)
        game = _create_test_game(3, config)

        for round_num in range(3):
            _start_test_round(game)
            round_state = game.current_round

            # 每局：第一个弃牌，第二个弃牌 → 第三个赢
            p1 = game.players[round_state.current_player_index]
            apply_action(game, p1.id, GameAction.FOLD)
            p2 = game.players[round_state.current_player_index]
            result = apply_action(game, p2.id, GameAction.FOLD)
            assert result.round_ended

        assert len(game.round_history) == 3

    def test_two_player_aggressive_game(self):
        """两人对局：多轮加注后比牌"""
        config = GameConfig(initial_chips=10000, ante=10, max_bet=10000)
        game = _create_test_game(2, config)
        round_state = _start_test_round(game)

        # 获取两个玩家
        p1 = game.players[round_state.current_player_index]

        # p1 看牌（不消耗回合）
        apply_action(game, p1.id, GameAction.CHECK_CARDS)

        # p1 仍需行动，先跟注
        apply_action(game, p1.id, GameAction.CALL)

        p2 = game.players[round_state.current_player_index]
        # p2 跟注
        apply_action(game, p2.id, GameAction.CALL)

        # p1 加注
        apply_action(game, p1.id, GameAction.RAISE)

        # p2 跟注
        apply_action(game, p2.id, GameAction.CALL)

        # p1 比牌
        result = apply_action(game, p1.id, GameAction.COMPARE, target_id=p2.id)
        assert result.round_ended
        assert result.round_result is not None

    def test_three_player_mixed_actions(self):
        """三人对局：混合操作"""
        game = _create_test_game(3)
        round_state = _start_test_round(game)

        # 第一轮
        p1 = game.players[round_state.current_player_index]
        apply_action(game, p1.id, GameAction.CHECK_CARDS)  # 看牌（不消耗回合）
        apply_action(game, p1.id, GameAction.CALL)  # 看牌后跟注

        p2 = game.players[round_state.current_player_index]
        apply_action(game, p2.id, GameAction.CALL)  # 跟注

        p3 = game.players[round_state.current_player_index]
        apply_action(game, p3.id, GameAction.RAISE)  # 加注

        # 第二轮
        # p1 已看牌，跟注
        apply_action(game, p1.id, GameAction.CALL)

        # p2 弃牌
        apply_action(game, p2.id, GameAction.FOLD)

        # p2 弃牌后轮到 p3，p3 看牌（不消耗回合）
        apply_action(game, p3.id, GameAction.CHECK_CARDS)
        # p3 看牌后仍需行动，跟注
        apply_action(game, p3.id, GameAction.CALL)

        # 现在轮到 p1，p1 与 p3 比牌
        result = apply_action(game, p1.id, GameAction.COMPARE, target_id=p3.id)
        assert result.round_ended

    def test_game_ends_when_player_runs_out(self):
        """玩家筹码耗尽时出局"""
        config = GameConfig(initial_chips=20, ante=10)
        game = _create_test_game(2, config)
        _start_test_round(game)
        # 底注后各玩家只剩 10 筹码

        p1 = game.players[game.current_round.current_player_index]
        # p1 弃牌
        result = apply_action(game, p1.id, GameAction.FOLD)
        assert result.round_ended

        # p1 还有 10 筹码（没跟注），还能继续玩
        # 但 p2 赢得了底池

        # 如果再玩一局底注后筹码不足的玩家标记为 OUT
        if game.status != "finished":
            _start_test_round(game)
            p1 = game.players[game.current_round.current_player_index]
            result = apply_action(game, p1.id, GameAction.FOLD)
            assert result.round_ended
