"""规则引擎

负责炸金花游戏的操作合法性校验和下注费用计算。

炸金花下注规则：
- 暗注玩家（未看牌）: 跟注 = current_bet × 1, 加注 = current_bet × 2
- 明注玩家（已看牌）: 跟注 = current_bet × 2, 加注 = current_bet × 4
- 加注后，current_bet 翻倍（即新的 current_bet = 原 current_bet × 2）
- 比牌费用 = 该玩家的跟注费用
- 单局下注上限由 GameConfig.max_bet 控制
"""

from __future__ import annotations

from app.models.game import (
    GameAction,
    GameConfig,
    GamePhase,
    Player,
    PlayerStatus,
    RoundState,
)


def get_call_cost(round_state: RoundState, player: Player) -> int:
    """计算玩家跟注所需的费用

    暗注玩家跟注费用 = current_bet × 1
    明注玩家跟注费用 = current_bet × 2

    Args:
        round_state: 当前局面状态
        player: 执行操作的玩家

    Returns:
        跟注所需筹码数
    """
    if player.status == PlayerStatus.ACTIVE_BLIND:
        return round_state.current_bet
    elif player.status == PlayerStatus.ACTIVE_SEEN:
        return round_state.current_bet * 2
    else:
        return 0


def get_raise_cost(round_state: RoundState, player: Player) -> int:
    """计算玩家加注所需的费用

    暗注玩家加注费用 = current_bet × 2
    明注玩家加注费用 = current_bet × 4

    加注后 current_bet 会翻倍（由 game_manager 处理）。

    Args:
        round_state: 当前局面状态
        player: 执行操作的玩家

    Returns:
        加注所需筹码数
    """
    if player.status == PlayerStatus.ACTIVE_BLIND:
        return round_state.current_bet * 2
    elif player.status == PlayerStatus.ACTIVE_SEEN:
        return round_state.current_bet * 4
    else:
        return 0


def get_compare_cost(round_state: RoundState, player: Player) -> int:
    """计算玩家比牌所需的费用

    比牌费用 = 该玩家的跟注费用（仅已看牌玩家可以比牌）。

    Args:
        round_state: 当前局面状态
        player: 发起比牌的玩家

    Returns:
        比牌所需筹码数。如果玩家不能比牌则返回 0。
    """
    if player.status != PlayerStatus.ACTIVE_SEEN:
        return 0
    return get_call_cost(round_state, player)


def _count_active_players(players: list[Player]) -> int:
    """统计当前局中仍然活跃的玩家数量"""
    return sum(1 for p in players if p.is_active)


def _get_compare_targets(players: list[Player], player: Player) -> list[Player]:
    """获取可以被比牌的对手列表

    可比牌的对手：仍活跃（未弃牌、未出局）且不是自己的玩家。

    Args:
        players: 所有玩家列表
        player: 发起比牌的玩家

    Returns:
        可以作为比牌对象的玩家列表
    """
    return [p for p in players if p.id != player.id and p.is_active]


def get_available_actions(
    round_state: RoundState,
    player: Player,
    players: list[Player],
    config: GameConfig | None = None,
) -> list[GameAction]:
    """获取玩家当前可用的操作列表

    规则：
    - 弃牌永远可用
    - 暗注状态（未看牌）: 跟注、加注、看牌、弃牌
    - 明注状态（已看牌）: 跟注、加注、比牌、弃牌
    - 筹码不足以支付加注费用时，不可加注
    - 筹码不足以支付跟注费用时，不可跟注
    - 筹码不足以支付比牌费用时，不可比牌
    - 如果设置了单局下注上限（max_bet），当前注额达到上限时不可加注
    - 只有已看牌的玩家才能比牌
    - 比牌需要至少有 1 个可比的对手（即至少 2 个活跃玩家）

    Args:
        round_state: 当前局面状态
        player: 当前行动玩家
        players: 所有玩家列表
        config: 游戏配置（用于判断下注上限），可选

    Returns:
        可用操作列表
    """
    # 不活跃的玩家没有任何操作
    if not player.is_active:
        return []

    # 非下注阶段不允许操作
    if round_state.phase != GamePhase.BETTING:
        return []

    actions: list[GameAction] = [GameAction.FOLD]

    call_cost = get_call_cost(round_state, player)
    raise_cost = get_raise_cost(round_state, player)

    if player.status == PlayerStatus.ACTIVE_BLIND:
        # 暗注状态可用操作：跟注、加注、看牌、弃牌
        if player.chips >= call_cost:
            actions.append(GameAction.CALL)

        # 看牌操作不需要花费筹码
        actions.append(GameAction.CHECK_CARDS)

        if player.chips >= raise_cost:
            # 检查是否达到下注上限
            if config is None or round_state.current_bet * 2 <= config.max_bet:
                actions.append(GameAction.RAISE)

    elif player.status == PlayerStatus.ACTIVE_SEEN:
        # 明注状态可用操作：跟注、加注、比牌、弃牌
        if player.chips >= call_cost:
            actions.append(GameAction.CALL)

        if player.chips >= raise_cost:
            # 检查是否达到下注上限
            if config is None or round_state.current_bet * 2 <= config.max_bet:
                actions.append(GameAction.RAISE)

        # 比牌条件：有可比的对手 + 筹码足够
        compare_cost = get_compare_cost(round_state, player)
        compare_targets = _get_compare_targets(players, player)
        if len(compare_targets) > 0 and player.chips >= compare_cost:
            actions.append(GameAction.COMPARE)

    return actions


def validate_action(
    round_state: RoundState,
    player: Player,
    action: GameAction,
    players: list[Player],
    config: GameConfig | None = None,
    target_id: str | None = None,
) -> bool:
    """校验玩家的操作是否合法

    Args:
        round_state: 当前局面状态
        player: 执行操作的玩家
        action: 要执行的操作
        players: 所有玩家列表
        config: 游戏配置（用于判断下注上限），可选
        target_id: 比牌目标的玩家 ID（仅 COMPARE 时需要）

    Returns:
        操作是否合法
    """
    available = get_available_actions(round_state, player, players, config)

    # 操作不在可用列表中
    if action not in available:
        return False

    # 比牌的额外校验：目标合法性
    if action == GameAction.COMPARE:
        if target_id is None:
            return False

        # 检查目标玩家存在且仍然活跃
        target_player = None
        for p in players:
            if p.id == target_id:
                target_player = p
                break

        if target_player is None:
            return False

        if not target_player.is_active:
            return False

        # 不能和自己比牌
        if target_id == player.id:
            return False

    return True


def get_action_cost(
    round_state: RoundState,
    player: Player,
    action: GameAction,
) -> int:
    """获取指定操作需要的筹码费用

    Args:
        round_state: 当前局面状态
        player: 执行操作的玩家
        action: 要执行的操作

    Returns:
        操作所需的筹码费用。弃牌和看牌返回 0。
    """
    if action == GameAction.FOLD:
        return 0
    elif action == GameAction.CHECK_CARDS:
        return 0
    elif action == GameAction.CALL:
        return get_call_cost(round_state, player)
    elif action == GameAction.RAISE:
        return get_raise_cost(round_state, player)
    elif action == GameAction.COMPARE:
        return get_compare_cost(round_state, player)
    else:
        return 0
