"""游戏流程引擎

负责炸金花游戏的完整生命周期管理：
- 创建游戏
- 开始新局（收底注、发牌、确定庄家）
- 执行操作（下注、看牌、弃牌、比牌）
- 推进回合（轮转到下一个行动玩家）
- 判断局结束条件
- 结算（弃牌胜出、比牌胜出、最大轮数强制比牌）
- 信息隐藏（玩家只能看到自己的手牌）
"""

from __future__ import annotations

import time
import uuid

from app.engine.deck import Deck
from app.engine.evaluator import compare_hands, evaluate_hand
from app.engine.rules import (
    get_action_cost,
    get_available_actions,
    validate_action,
)
from app.models.card import Card
from app.models.game import (
    ActionRecord,
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


class GameError(Exception):
    """游戏流程错误基类"""


class InvalidActionError(GameError):
    """非法操作错误"""


class GameNotStartedError(GameError):
    """游戏尚未开始错误"""


class RoundNotActiveError(GameError):
    """当前局非活跃状态错误"""


class ActionResult:
    """操作执行结果

    Attributes:
        success: 操作是否成功
        action: 执行的操作
        player_id: 执行者 ID
        amount: 消耗的筹码
        message: 结果描述
        compare_result: 比牌结果（仅比牌操作有值）
        round_ended: 本局是否因此操作结束
        round_result: 本局结算结果（仅当 round_ended=True 时有值）
    """

    def __init__(
        self,
        success: bool,
        action: GameAction,
        player_id: str,
        amount: int = 0,
        message: str = "",
        compare_result: dict | None = None,
        round_ended: bool = False,
        round_result: RoundResult | None = None,
    ):
        self.success = success
        self.action = action
        self.player_id = player_id
        self.amount = amount
        self.message = message
        self.compare_result = compare_result
        self.round_ended = round_ended
        self.round_result = round_result


def create_game(
    player_configs: list[dict],
    config: GameConfig | None = None,
) -> GameState:
    """创建新游戏

    Args:
        player_configs: 玩家配置列表，每项包含:
            - name: 玩家名称
            - player_type: "human" 或 "ai"
            - model_id: AI 模型标识（AI 玩家必填）
            - avatar: 头像标识（可选）
        config: 游戏配置，None 使用默认配置

    Returns:
        初始化好的 GameState

    Raises:
        ValueError: 玩家数量不在 2-6 范围内
    """
    if len(player_configs) < 2 or len(player_configs) > 6:
        raise ValueError(f"玩家数量必须在 2-6 之间，当前为 {len(player_configs)}")

    game_config = config or GameConfig()

    players = []
    for pc in player_configs:
        player = Player(
            id=str(uuid.uuid4()),
            name=pc["name"],
            avatar=pc.get("avatar", ""),
            player_type=PlayerType(pc["player_type"]),
            chips=game_config.initial_chips,
            status=PlayerStatus.ACTIVE_BLIND,
            model_id=pc.get("model_id"),
        )
        players.append(player)

    return GameState(
        game_id=str(uuid.uuid4()),
        players=players,
        config=game_config,
        status="waiting",
    )


def start_round(game: GameState, deck: Deck | None = None) -> RoundState:
    """开始新一局

    流程：
    1. 重置所有有筹码玩家的状态为 ACTIVE_BLIND
    2. 确定庄家（首局随机，后续顺延）
    3. 收底注
    4. 洗牌发牌
    5. 设定行动顺序（庄家下一位开始）

    Args:
        game: 当前游戏状态
        deck: 可选的牌组实例（用于测试时注入确定性牌组）

    Returns:
        新局的 RoundState

    Raises:
        GameError: 活跃玩家不足 2 人时抛出
    """
    # 确定可参与本局的玩家（有筹码的）
    alive_players = [p for p in game.players if p.status != PlayerStatus.OUT and p.chips > 0]
    if len(alive_players) < 2:
        raise GameError("活跃玩家不足 2 人，无法开始新局")

    # 标记无筹码的玩家为 OUT
    for p in game.players:
        if p.chips <= 0 and p.status != PlayerStatus.OUT:
            p.status = PlayerStatus.OUT

    # 重置有筹码玩家的状态
    for p in alive_players:
        p.status = PlayerStatus.ACTIVE_BLIND
        p.hand = None
        p.total_bet_this_round = 0

    # 确定庄家位置
    round_number = len(game.round_history) + 1
    if round_number == 1:
        # 首局：找到第一个活跃玩家的索引作为庄家
        dealer_index = _find_first_alive_index(game.players, 0)
    else:
        # 后续局：上一局庄家的下一个活跃玩家
        prev_dealer = game.current_round.dealer_index if game.current_round else 0
        dealer_index = _find_next_alive_index(game.players, prev_dealer)

    # 创建新局状态
    round_state = RoundState(
        round_number=round_number,
        pot=0,
        current_bet=game.config.ante,
        dealer_index=dealer_index,
        current_player_index=0,  # 临时，下面会设置
        phase=GamePhase.DEALING,
        turn_count=0,
        max_turns=game.config.max_turns,
    )
    game.current_round = round_state
    game.status = "playing"

    # 收底注
    for p in alive_players:
        ante = min(game.config.ante, p.chips)
        p.chips -= ante
        p.total_bet_this_round += ante
        round_state.pot += ante

    # 发牌
    if deck is None:
        deck = Deck()
    else:
        deck.reset()

    for p in alive_players:
        p.hand = deck.deal(3)

    # 设定行动起始玩家（庄家的下一个活跃玩家）
    first_player_index = _find_next_alive_index(game.players, dealer_index)
    round_state.current_player_index = first_player_index

    # 进入下注阶段
    round_state.phase = GamePhase.BETTING

    return round_state


def apply_action(
    game: GameState,
    player_id: str,
    action: GameAction,
    target_id: str | None = None,
) -> ActionResult:
    """执行玩家操作

    Args:
        game: 当前游戏状态
        player_id: 执行操作的玩家 ID
        action: 要执行的操作
        target_id: 比牌目标 ID（仅 COMPARE 时需要）

    Returns:
        ActionResult 操作结果

    Raises:
        GameNotStartedError: 游戏尚未开始
        RoundNotActiveError: 当前局不在下注阶段
        InvalidActionError: 操作不合法
    """
    round_state = game.current_round
    if round_state is None:
        raise GameNotStartedError("当前没有进行中的局")

    if round_state.phase != GamePhase.BETTING:
        raise RoundNotActiveError(f"当前阶段 {round_state.phase.value} 不允许操作")

    # 查找执行者
    player = game.get_player_by_id(player_id)
    if player is None:
        raise InvalidActionError(f"玩家 {player_id} 不存在")

    # 检查是否轮到该玩家
    current_player = game.players[round_state.current_player_index]
    if current_player.id != player_id:
        raise InvalidActionError(f"当前轮到 {current_player.name} 行动，而非 {player.name}")

    # 校验操作合法性
    if not validate_action(round_state, player, action, game.players, game.config, target_id):
        raise InvalidActionError(
            f"玩家 {player.name} 不能执行操作 {action.value}"
            + (f" (目标: {target_id})" if target_id else "")
        )

    # 执行操作
    result = _execute_action(game, player, action, target_id)

    # 记录操作
    record = ActionRecord(
        player_id=player.id,
        player_name=player.name,
        action=action,
        amount=result.amount,
        target_id=target_id,
        timestamp=time.time(),
    )
    round_state.actions.append(record)

    # 检查局是否结束
    if check_round_end(game):
        round_result = settle_round(game)
        result.round_ended = True
        result.round_result = round_result
    elif not result.round_ended:
        # 看牌不消耗回合 — 看牌后玩家仍需选择跟注/加注/弃牌等操作
        if action != GameAction.CHECK_CARDS:
            # 推进到下一个行动玩家（比牌导致局结束的情况已经在上面处理了）
            advance_turn(game)

    return result


def _execute_action(
    game: GameState,
    player: Player,
    action: GameAction,
    target_id: str | None,
) -> ActionResult:
    """执行具体操作逻辑（内部方法）"""
    round_state = game.current_round
    assert round_state is not None

    if action == GameAction.FOLD:
        player.status = PlayerStatus.FOLDED
        return ActionResult(
            success=True,
            action=action,
            player_id=player.id,
            amount=0,
            message=f"{player.name} 弃牌",
        )

    elif action == GameAction.CHECK_CARDS:
        player.status = PlayerStatus.ACTIVE_SEEN
        return ActionResult(
            success=True,
            action=action,
            player_id=player.id,
            amount=0,
            message=f"{player.name} 看牌",
        )

    elif action == GameAction.CALL:
        cost = get_action_cost(round_state, player, action)
        player.chips -= cost
        player.total_bet_this_round += cost
        round_state.pot += cost
        return ActionResult(
            success=True,
            action=action,
            player_id=player.id,
            amount=cost,
            message=f"{player.name} 跟注 {cost} 筹码",
        )

    elif action == GameAction.RAISE:
        cost = get_action_cost(round_state, player, action)
        player.chips -= cost
        player.total_bet_this_round += cost
        round_state.pot += cost
        # 加注后 current_bet 翻倍
        round_state.current_bet *= 2
        return ActionResult(
            success=True,
            action=action,
            player_id=player.id,
            amount=cost,
            message=f"{player.name} 加注 {cost} 筹码，当前注额升至 {round_state.current_bet}",
        )

    elif action == GameAction.COMPARE:
        cost = get_action_cost(round_state, player, action)
        player.chips -= cost
        player.total_bet_this_round += cost
        round_state.pot += cost

        # 执行比牌
        assert target_id is not None
        target = game.get_player_by_id(target_id)
        assert target is not None
        assert player.hand is not None
        assert target.hand is not None

        hand_a = evaluate_hand(player.hand)
        hand_b = evaluate_hand(target.hand)
        cmp_result = compare_hands(hand_a, hand_b)

        # 比牌结果：正数表示发起方更大，负数或0表示发起方输（相同时发起方输）
        if cmp_result > 0:
            # 发起方赢
            target.status = PlayerStatus.FOLDED
            winner = player
            loser = target
        else:
            # 发起方输（包括相同时）
            player.status = PlayerStatus.FOLDED
            winner = target
            loser = player

        compare_result = {
            "winner_id": winner.id,
            "winner_name": winner.name,
            "loser_id": loser.id,
            "loser_name": loser.name,
            "winner_hand": _hand_description(winner.hand),
            "loser_hand": _hand_description(loser.hand),
        }

        return ActionResult(
            success=True,
            action=action,
            player_id=player.id,
            amount=cost,
            message=f"{player.name} 与 {target.name} 比牌，{winner.name} 获胜",
            compare_result=compare_result,
        )

    # 不应到达这里
    raise InvalidActionError(f"未知操作: {action}")


def advance_turn(game: GameState) -> None:
    """推进到下一个行动玩家

    跳过已弃牌和出局的玩家。
    当走完一圈时 turn_count +1。

    Args:
        game: 当前游戏状态
    """
    round_state = game.current_round
    if round_state is None:
        return

    active_players = game.get_active_players()
    if len(active_players) <= 1:
        return

    start_index = round_state.current_player_index
    next_index = _find_next_alive_index(game.players, start_index)
    round_state.current_player_index = next_index

    # 如果绕回到或超过了庄家后第一个位置，说明完成了一圈
    # 通过计算 action 数量来判断是否完成一圈
    active_count = len(active_players)
    actions_in_current_turn = _count_actions_in_current_turn(round_state, active_count)
    if actions_in_current_turn >= active_count:
        round_state.turn_count += 1


def _count_actions_in_current_turn(round_state: RoundState, active_count: int) -> int:
    """计算当前轮次中已执行的有效操作数（不含看牌）

    看牌操作不算一次行动回合（不消耗下注机会）。
    """
    if active_count == 0:
        return 0

    # 从最后的操作向前数，找到本轮的操作
    # 排除 CHECK_CARDS（看牌不算一次轮次行动）
    betting_actions = [
        a
        for a in round_state.actions
        if a.action in (GameAction.CALL, GameAction.RAISE, GameAction.FOLD, GameAction.COMPARE)
    ]
    # 一轮完成当操作数是 active_count 的倍数
    return len(betting_actions) % active_count


def check_round_end(game: GameState) -> bool:
    """检查当前局是否应该结束

    结束条件:
    1. 仅剩 1 个活跃玩家（其余全部弃牌）
    2. 达到最大轮数

    注：比牌导致一方弃牌后也可能触发条件 1。

    Args:
        game: 当前游戏状态

    Returns:
        是否应该结束本局
    """
    round_state = game.current_round
    if round_state is None:
        return False

    active_players = game.get_active_players()

    # 条件 1：仅剩 1 个活跃玩家
    if len(active_players) <= 1:
        return True

    # 条件 2：达到最大轮数
    if round_state.turn_count >= round_state.max_turns:
        return True

    return False


def settle_round(game: GameState) -> RoundResult:
    """结算当前局

    处理三种结局：
    1. 弃牌胜出：仅剩一人未弃牌
    2. 比牌胜出：通过比牌决出胜者（已在 apply_action 中处理弃牌）
    3. 最大轮数强制比牌：剩余玩家两两比较，取最大者

    Args:
        game: 当前游戏状态

    Returns:
        RoundResult 结算结果
    """
    round_state = game.current_round
    assert round_state is not None

    round_state.phase = GamePhase.SETTLEMENT
    active_players = game.get_active_players()

    if len(active_players) == 0:
        # 不应发生，但作为安全措施
        raise GameError("没有活跃玩家，无法结算")

    if len(active_players) == 1:
        # 仅剩一人 → 直接获胜
        winner = active_players[0]
        win_method = "其他玩家全部弃牌"
        hands_revealed = None
    else:
        # 多人存活 → 强制比牌（最大轮数到达）
        winner = _find_best_hand_player(active_players)
        win_method = "最大轮数到达，强制比牌"
        hands_revealed = {p.id: p.hand for p in active_players if p.hand is not None}

    # 计算筹码变化
    pot = round_state.pot
    player_chip_changes: dict[str, int] = {}
    for p in game.players:
        if p.id == winner.id:
            player_chip_changes[p.id] = pot - p.total_bet_this_round
        else:
            player_chip_changes[p.id] = -p.total_bet_this_round

    # 把底池给赢家
    winner.chips += pot

    # 构建结果
    result = RoundResult(
        round_number=round_state.round_number,
        winner_id=winner.id,
        winner_name=winner.name,
        pot=pot,
        win_method=win_method,
        hands_revealed=hands_revealed,
        player_chip_changes=player_chip_changes,
    )

    # 记录到历史
    game.round_history.append(result)

    # 标记筹码为 0 的玩家出局
    for p in game.players:
        if p.chips <= 0 and p.status != PlayerStatus.OUT:
            p.status = PlayerStatus.OUT

    # 检查游戏是否结束（只剩 1 个有筹码的玩家）
    alive_players = [p for p in game.players if p.status != PlayerStatus.OUT and p.chips > 0]
    if len(alive_players) <= 1:
        game.status = "finished"
        round_state.phase = GamePhase.GAME_OVER
    else:
        round_state.phase = GamePhase.SETTLEMENT

    return result


def get_visible_state(game: GameState, viewer_id: str) -> dict:
    """获取对特定玩家可见的游戏状态

    核心的信息隐藏逻辑：其他玩家的手牌不可见。

    Args:
        game: 完整游戏状态
        viewer_id: 查看者的玩家 ID

    Returns:
        过滤后的游戏状态字典
    """
    state = game.model_dump(mode="json")

    for player_data in state["players"]:
        if player_data["id"] != viewer_id:
            # 隐藏其他玩家的手牌
            player_data["hand"] = None

    return state


# ---- 内部辅助函数 ----


def _find_first_alive_index(players: list[Player], start: int) -> int:
    """从 start 位置开始找到第一个活跃玩家的索引"""
    n = len(players)
    for i in range(n):
        idx = (start + i) % n
        if players[idx].is_active or (
            players[idx].status != PlayerStatus.OUT and players[idx].chips > 0
        ):
            return idx
    return start


def _find_next_alive_index(players: list[Player], current: int) -> int:
    """从 current 的下一个位置找到第一个活跃玩家的索引"""
    n = len(players)
    for i in range(1, n + 1):
        idx = (current + i) % n
        if players[idx].is_active:
            return idx
    return current


def _find_best_hand_player(players: list[Player]) -> Player:
    """在多个玩家中找出手牌最大的（用于强制比牌）

    Args:
        players: 参与比较的玩家列表（都应有手牌）

    Returns:
        手牌最大的玩家
    """
    best_index = 0
    first_hand = players[0].hand
    assert first_hand is not None
    best_hand = evaluate_hand(first_hand)

    for i, p in enumerate(players[1:], start=1):
        p_hand_cards = p.hand
        assert p_hand_cards is not None
        p_hand = evaluate_hand(p_hand_cards)
        if compare_hands(p_hand, best_hand) > 0:
            best_index = i
            best_hand = p_hand

    return players[best_index]


def _hand_description(hand: list[Card] | None) -> str:
    """生成手牌的可读描述"""
    if hand is None:
        return "未知"
    result = evaluate_hand(hand)
    cards_str = " ".join(str(c) for c in hand)
    return f"{cards_str} ({result.description})"
