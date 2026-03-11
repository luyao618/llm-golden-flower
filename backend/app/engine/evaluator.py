"""牌型评估器

提供炸金花手牌评估和比较功能：
- evaluate_hand: 判定 3 张牌的牌型（豹子、同花顺、同花、顺子、对子、散牌）
- compare_hands: 比较两手牌大小
"""

from __future__ import annotations

from app.models.card import Card, Rank
from app.models.game import HandResult, HandType


def evaluate_hand(cards: list[Card]) -> HandResult:
    """评估 3 张手牌的牌型

    Args:
        cards: 恰好 3 张牌的列表

    Returns:
        HandResult 包含牌型、排序后的点数列表和中文描述

    Raises:
        ValueError: 牌数量不为 3 时抛出
    """
    if len(cards) != 3:
        raise ValueError(f"手牌必须恰好 3 张，实际收到 {len(cards)} 张")

    ranks = sorted([c.rank for c in cards], reverse=True)
    suits = [c.suit for c in cards]

    is_flush = suits[0] == suits[1] == suits[2]
    is_straight, straight_ranks = _check_straight(ranks)
    is_three = ranks[0] == ranks[1] == ranks[2]
    is_pair, pair_ranks = _check_pair(ranks)

    # 按优先级判定牌型（从大到小）
    if is_three:
        return HandResult(
            hand_type=HandType.THREE_OF_A_KIND,
            ranks=list(ranks),
            description=f"豹子{ranks[0].chinese_name}",
        )

    if is_flush and is_straight:
        return HandResult(
            hand_type=HandType.STRAIGHT_FLUSH,
            ranks=straight_ranks,
            description=f"同花顺{_straight_description(straight_ranks)}",
        )

    if is_flush:
        return HandResult(
            hand_type=HandType.FLUSH,
            ranks=list(ranks),
            description=f"同花{_ranks_description(ranks)}",
        )

    if is_straight:
        return HandResult(
            hand_type=HandType.STRAIGHT,
            ranks=straight_ranks,
            description=f"顺子{_straight_description(straight_ranks)}",
        )

    if is_pair:
        return HandResult(
            hand_type=HandType.PAIR,
            ranks=pair_ranks,
            description=f"对{pair_ranks[0].chinese_name}",
        )

    return HandResult(
        hand_type=HandType.HIGH_CARD,
        ranks=list(ranks),
        description=f"散牌{_ranks_description(ranks)}",
    )


def compare_hands(hand_a: HandResult, hand_b: HandResult) -> int:
    """比较两手牌大小

    Args:
        hand_a: 第一手牌的评估结果
        hand_b: 第二手牌的评估结果

    Returns:
        正数表示 hand_a 更大，负数表示 hand_b 更大，0 表示相等
    """
    # 先比较牌型
    if hand_a.hand_type.value != hand_b.hand_type.value:
        return hand_a.hand_type.value - hand_b.hand_type.value

    # 同牌型时，逐一比较 ranks 列表中的点数
    for rank_a, rank_b in zip(hand_a.ranks, hand_b.ranks):
        if rank_a.value != rank_b.value:
            return rank_a.value - rank_b.value

    # 完全相同
    return 0


# ---- 内部辅助函数 ----


def _check_straight(ranks: list[Rank]) -> tuple[bool, list[Rank]]:
    """检查是否为顺子

    处理特殊情况：A-2-3 是最小顺子，此时 A 视为 1。

    Args:
        ranks: 从大到小排序的 3 个点数

    Returns:
        (是否为顺子, 用于比较的排序后点数列表)
        对于 A-2-3，返回的 ranks 为 [THREE, TWO, ACE]，使 A 成为最小。
    """
    r = ranks  # 已从大到小排序

    # 普通顺子：相邻差值都为 1
    if r[0].value - r[1].value == 1 and r[1].value - r[2].value == 1:
        return True, list(r)

    # 特殊顺子：A-2-3（排序后为 [ACE, THREE, TWO]）
    if r[0] == Rank.ACE and r[1] == Rank.THREE and r[2] == Rank.TWO:
        # A-2-3 中 A 当最小，排序为 [3, 2, A] 用于比较
        return True, [Rank.THREE, Rank.TWO, Rank.ACE]

    return False, []


def _check_pair(ranks: list[Rank]) -> tuple[bool, list[Rank]]:
    """检查是否为对子

    Args:
        ranks: 从大到小排序的 3 个点数

    Returns:
        (是否为对子, 用于比较的排序后点数列表)
        排列规则：对子的点数在前，单张在后。
    """
    # 前两张相同
    if ranks[0] == ranks[1] and ranks[1] != ranks[2]:
        return True, [ranks[0], ranks[1], ranks[2]]

    # 后两张相同
    if ranks[1] == ranks[2] and ranks[0] != ranks[1]:
        return True, [ranks[1], ranks[2], ranks[0]]

    return False, []


def _ranks_description(ranks: list[Rank]) -> str:
    """生成点数的中文描述，如 'K-J-7'"""
    return "-".join(r.chinese_name for r in ranks)


def _straight_description(straight_ranks: list[Rank]) -> str:
    """生成顺子的中文描述

    对于 A-2-3 特殊顺子，显示为 'A-2-3'。
    普通顺子按从大到小显示。
    """
    # A-2-3 特殊情况：straight_ranks 为 [THREE, TWO, ACE]
    if straight_ranks[-1] == Rank.ACE and straight_ranks[0] == Rank.THREE:
        return "A-2-3"
    return _ranks_description(straight_ranks)
