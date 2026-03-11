"""牌型评估器和牌组管理的单元测试

覆盖：
- Deck 类：洗牌、发牌、边界情况
- evaluate_hand：6 种牌型识别
- compare_hands：同牌型和跨牌型比较
- 边界情况：A-2-3 最小顺子、Q-K-A 最大顺子
"""

from __future__ import annotations

import pytest

from app.engine.deck import Deck
from app.engine.evaluator import compare_hands, evaluate_hand
from app.models.card import Card, Rank, Suit
from app.models.game import HandType


# ---- 辅助函数 ----


def make_card(rank: Rank, suit: Suit = Suit.SPADES) -> Card:
    """快速创建一张牌"""
    return Card(suit=suit, rank=rank)


def make_hand(r1: Rank, s1: Suit, r2: Rank, s2: Suit, r3: Rank, s3: Suit) -> list[Card]:
    """快速创建一手 3 张牌"""
    return [Card(suit=s1, rank=r1), Card(suit=s2, rank=r2), Card(suit=s3, rank=r3)]


# ============================================================
# Deck 测试
# ============================================================


class TestDeck:
    """Deck 类测试"""

    def test_initial_deck_has_52_cards(self) -> None:
        deck = Deck()
        assert deck.remaining == 52
        assert len(deck) == 52

    def test_deal_reduces_remaining(self) -> None:
        deck = Deck(seed=42)
        cards = deck.deal(3)
        assert len(cards) == 3
        assert deck.remaining == 49

    def test_deal_one(self) -> None:
        deck = Deck(seed=42)
        card = deck.deal_one()
        assert isinstance(card, Card)
        assert deck.remaining == 51

    def test_deal_all_cards(self) -> None:
        deck = Deck(seed=42)
        all_dealt: list[Card] = []
        for _ in range(52):
            all_dealt.append(deck.deal_one())
        assert deck.remaining == 0
        # 52 张牌应该互不重复
        assert len(set((c.suit, c.rank) for c in all_dealt)) == 52

    def test_deal_too_many_raises_error(self) -> None:
        deck = Deck(seed=42)
        with pytest.raises(ValueError, match="无法发出"):
            deck.deal(53)

    def test_deal_from_empty_raises_error(self) -> None:
        deck = Deck(seed=42)
        deck.deal(52)
        with pytest.raises(ValueError, match="无法发出"):
            deck.deal_one()

    def test_deal_negative_raises_error(self) -> None:
        deck = Deck(seed=42)
        with pytest.raises(ValueError, match="不能为负数"):
            deck.deal(-1)

    def test_reset_restores_full_deck(self) -> None:
        deck = Deck(seed=42)
        deck.deal(10)
        assert deck.remaining == 42
        deck.reset()
        assert deck.remaining == 52

    def test_seed_produces_deterministic_results(self) -> None:
        deck1 = Deck(seed=123)
        deck2 = Deck(seed=123)
        cards1 = deck1.deal(10)
        cards2 = deck2.deal(10)
        assert cards1 == cards2

    def test_different_seeds_produce_different_results(self) -> None:
        deck1 = Deck(seed=1)
        deck2 = Deck(seed=2)
        cards1 = deck1.deal(10)
        cards2 = deck2.deal(10)
        assert cards1 != cards2

    def test_repr(self) -> None:
        deck = Deck(seed=42)
        assert "52" in repr(deck)
        deck.deal(5)
        assert "47" in repr(deck)


# ============================================================
# evaluate_hand 牌型识别测试
# ============================================================


class TestEvaluateHandType:
    """测试 6 种牌型的正确识别"""

    # ---- 豹子 (Three of a Kind) ----

    def test_three_of_a_kind_aces(self) -> None:
        cards = make_hand(Rank.ACE, Suit.SPADES, Rank.ACE, Suit.HEARTS, Rank.ACE, Suit.DIAMONDS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.THREE_OF_A_KIND
        assert "豹子" in result.description

    def test_three_of_a_kind_twos(self) -> None:
        cards = make_hand(Rank.TWO, Suit.SPADES, Rank.TWO, Suit.HEARTS, Rank.TWO, Suit.CLUBS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.THREE_OF_A_KIND

    # ---- 同花顺 (Straight Flush) ----

    def test_straight_flush_high(self) -> None:
        cards = make_hand(Rank.QUEEN, Suit.HEARTS, Rank.KING, Suit.HEARTS, Rank.ACE, Suit.HEARTS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.STRAIGHT_FLUSH

    def test_straight_flush_low(self) -> None:
        cards = make_hand(Rank.ACE, Suit.SPADES, Rank.TWO, Suit.SPADES, Rank.THREE, Suit.SPADES)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.STRAIGHT_FLUSH
        assert "A-2-3" in result.description

    def test_straight_flush_middle(self) -> None:
        cards = make_hand(Rank.FIVE, Suit.CLUBS, Rank.SIX, Suit.CLUBS, Rank.SEVEN, Suit.CLUBS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.STRAIGHT_FLUSH

    # ---- 同花 (Flush) ----

    def test_flush(self) -> None:
        cards = make_hand(Rank.THREE, Suit.HEARTS, Rank.SEVEN, Suit.HEARTS, Rank.JACK, Suit.HEARTS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.FLUSH
        assert "同花" in result.description

    def test_flush_all_high(self) -> None:
        cards = make_hand(
            Rank.ACE, Suit.DIAMONDS, Rank.KING, Suit.DIAMONDS, Rank.QUEEN, Suit.DIAMONDS
        )
        result = evaluate_hand(cards)
        # Q-K-A 同花色 → 同花顺，不是单纯同花
        assert result.hand_type == HandType.STRAIGHT_FLUSH

    def test_flush_not_straight(self) -> None:
        cards = make_hand(
            Rank.ACE, Suit.DIAMONDS, Rank.KING, Suit.DIAMONDS, Rank.JACK, Suit.DIAMONDS
        )
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.FLUSH

    # ---- 顺子 (Straight) ----

    def test_straight_normal(self) -> None:
        cards = make_hand(Rank.FIVE, Suit.HEARTS, Rank.SIX, Suit.SPADES, Rank.SEVEN, Suit.CLUBS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.STRAIGHT

    def test_straight_a23(self) -> None:
        """A-2-3 是最小的顺子"""
        cards = make_hand(Rank.ACE, Suit.HEARTS, Rank.TWO, Suit.SPADES, Rank.THREE, Suit.CLUBS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.STRAIGHT
        assert "A-2-3" in result.description

    def test_straight_qka(self) -> None:
        """Q-K-A 是最大的顺子"""
        cards = make_hand(Rank.QUEEN, Suit.HEARTS, Rank.KING, Suit.SPADES, Rank.ACE, Suit.CLUBS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.STRAIGHT

    def test_not_straight_kaa(self) -> None:
        """K-A-2 不是顺子（A 不做环形衔接）"""
        cards = make_hand(Rank.KING, Suit.HEARTS, Rank.ACE, Suit.SPADES, Rank.TWO, Suit.CLUBS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.HIGH_CARD

    # ---- 对子 (Pair) ----

    def test_pair_high(self) -> None:
        cards = make_hand(Rank.KING, Suit.HEARTS, Rank.KING, Suit.SPADES, Rank.SEVEN, Suit.CLUBS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.PAIR
        assert "对K" in result.description

    def test_pair_low(self) -> None:
        cards = make_hand(Rank.TWO, Suit.HEARTS, Rank.TWO, Suit.SPADES, Rank.ACE, Suit.CLUBS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.PAIR
        assert "对2" in result.description

    def test_pair_middle_card_matches(self) -> None:
        """后两张相同的对子"""
        cards = make_hand(Rank.ACE, Suit.HEARTS, Rank.FIVE, Suit.SPADES, Rank.FIVE, Suit.CLUBS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.PAIR
        assert "对5" in result.description

    # ---- 散牌 (High Card) ----

    def test_high_card(self) -> None:
        cards = make_hand(Rank.TWO, Suit.HEARTS, Rank.SEVEN, Suit.SPADES, Rank.JACK, Suit.CLUBS)
        result = evaluate_hand(cards)
        assert result.hand_type == HandType.HIGH_CARD
        assert "散牌" in result.description

    # ---- 异常输入 ----

    def test_wrong_card_count_raises_error(self) -> None:
        with pytest.raises(ValueError, match="3 张"):
            evaluate_hand([make_card(Rank.ACE), make_card(Rank.KING)])

    def test_empty_hand_raises_error(self) -> None:
        with pytest.raises(ValueError, match="3 张"):
            evaluate_hand([])

    def test_four_cards_raises_error(self) -> None:
        with pytest.raises(ValueError, match="3 张"):
            evaluate_hand(
                [
                    make_card(Rank.ACE),
                    make_card(Rank.KING),
                    make_card(Rank.QUEEN),
                    make_card(Rank.JACK),
                ]
            )


# ============================================================
# compare_hands 手牌比较测试
# ============================================================


class TestCompareHands:
    """测试手牌大小比较"""

    # ---- 跨牌型比较 ----

    def test_three_of_a_kind_beats_straight_flush(self) -> None:
        three = evaluate_hand(
            make_hand(Rank.TWO, Suit.SPADES, Rank.TWO, Suit.HEARTS, Rank.TWO, Suit.CLUBS)
        )
        sf = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.KING, Suit.HEARTS, Rank.QUEEN, Suit.HEARTS)
        )
        assert compare_hands(three, sf) > 0

    def test_straight_flush_beats_flush(self) -> None:
        sf = evaluate_hand(
            make_hand(Rank.FIVE, Suit.CLUBS, Rank.SIX, Suit.CLUBS, Rank.SEVEN, Suit.CLUBS)
        )
        flush = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.KING, Suit.HEARTS, Rank.JACK, Suit.HEARTS)
        )
        assert compare_hands(sf, flush) > 0

    def test_flush_beats_straight(self) -> None:
        flush = evaluate_hand(
            make_hand(Rank.TWO, Suit.DIAMONDS, Rank.FIVE, Suit.DIAMONDS, Rank.NINE, Suit.DIAMONDS)
        )
        straight = evaluate_hand(
            make_hand(Rank.QUEEN, Suit.HEARTS, Rank.KING, Suit.SPADES, Rank.ACE, Suit.CLUBS)
        )
        assert compare_hands(flush, straight) > 0

    def test_straight_beats_pair(self) -> None:
        straight = evaluate_hand(
            make_hand(Rank.THREE, Suit.HEARTS, Rank.FOUR, Suit.SPADES, Rank.FIVE, Suit.CLUBS)
        )
        pair = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.ACE, Suit.SPADES, Rank.KING, Suit.CLUBS)
        )
        assert compare_hands(straight, pair) > 0

    def test_pair_beats_high_card(self) -> None:
        pair = evaluate_hand(
            make_hand(Rank.TWO, Suit.HEARTS, Rank.TWO, Suit.SPADES, Rank.FIVE, Suit.CLUBS)
        )
        high = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.KING, Suit.SPADES, Rank.TEN, Suit.CLUBS)
        )
        assert compare_hands(pair, high) > 0

    # ---- 完整牌型排序链 ----

    def test_full_hand_type_ordering(self) -> None:
        """验证完整的牌型大小顺序：豹子 > 同花顺 > 同花 > 顺子 > 对子 > 散牌"""
        three_kind = evaluate_hand(
            make_hand(Rank.SEVEN, Suit.SPADES, Rank.SEVEN, Suit.HEARTS, Rank.SEVEN, Suit.CLUBS)
        )
        straight_flush = evaluate_hand(
            make_hand(Rank.EIGHT, Suit.HEARTS, Rank.NINE, Suit.HEARTS, Rank.TEN, Suit.HEARTS)
        )
        flush = evaluate_hand(
            make_hand(Rank.TWO, Suit.CLUBS, Rank.FIVE, Suit.CLUBS, Rank.NINE, Suit.CLUBS)
        )
        straight = evaluate_hand(
            make_hand(Rank.NINE, Suit.HEARTS, Rank.TEN, Suit.SPADES, Rank.JACK, Suit.CLUBS)
        )
        pair = evaluate_hand(
            make_hand(Rank.QUEEN, Suit.HEARTS, Rank.QUEEN, Suit.SPADES, Rank.THREE, Suit.CLUBS)
        )
        high_card = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.KING, Suit.SPADES, Rank.TWO, Suit.CLUBS)
        )

        hands = [three_kind, straight_flush, flush, straight, pair, high_card]
        for i in range(len(hands) - 1):
            assert compare_hands(hands[i], hands[i + 1]) > 0, (
                f"{hands[i].description} 应大于 {hands[i + 1].description}"
            )

    # ---- 同牌型内部比较 ----

    def test_higher_three_of_a_kind_wins(self) -> None:
        aaa = evaluate_hand(
            make_hand(Rank.ACE, Suit.SPADES, Rank.ACE, Suit.HEARTS, Rank.ACE, Suit.CLUBS)
        )
        kkk = evaluate_hand(
            make_hand(Rank.KING, Suit.SPADES, Rank.KING, Suit.HEARTS, Rank.KING, Suit.CLUBS)
        )
        assert compare_hands(aaa, kkk) > 0

    def test_higher_straight_flush_wins(self) -> None:
        high_sf = evaluate_hand(
            make_hand(Rank.JACK, Suit.HEARTS, Rank.QUEEN, Suit.HEARTS, Rank.KING, Suit.HEARTS)
        )
        low_sf = evaluate_hand(
            make_hand(Rank.FIVE, Suit.SPADES, Rank.SIX, Suit.SPADES, Rank.SEVEN, Suit.SPADES)
        )
        assert compare_hands(high_sf, low_sf) > 0

    def test_higher_flush_wins(self) -> None:
        high_flush = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.KING, Suit.HEARTS, Rank.TWO, Suit.HEARTS)
        )
        low_flush = evaluate_hand(
            make_hand(Rank.ACE, Suit.CLUBS, Rank.QUEEN, Suit.CLUBS, Rank.TWO, Suit.CLUBS)
        )
        assert compare_hands(high_flush, low_flush) > 0

    def test_higher_straight_wins(self) -> None:
        high_straight = evaluate_hand(
            make_hand(Rank.QUEEN, Suit.HEARTS, Rank.KING, Suit.SPADES, Rank.ACE, Suit.CLUBS)
        )
        low_straight = evaluate_hand(
            make_hand(Rank.FIVE, Suit.HEARTS, Rank.SIX, Suit.SPADES, Rank.SEVEN, Suit.CLUBS)
        )
        assert compare_hands(high_straight, low_straight) > 0

    def test_higher_pair_wins(self) -> None:
        high_pair = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.ACE, Suit.SPADES, Rank.TWO, Suit.CLUBS)
        )
        low_pair = evaluate_hand(
            make_hand(Rank.KING, Suit.HEARTS, Rank.KING, Suit.SPADES, Rank.ACE, Suit.CLUBS)
        )
        assert compare_hands(high_pair, low_pair) > 0

    def test_same_pair_compare_kicker(self) -> None:
        """相同对子时，比较单张大小"""
        pair_k = evaluate_hand(
            make_hand(Rank.FIVE, Suit.HEARTS, Rank.FIVE, Suit.SPADES, Rank.KING, Suit.CLUBS)
        )
        pair_j = evaluate_hand(
            make_hand(Rank.FIVE, Suit.DIAMONDS, Rank.FIVE, Suit.CLUBS, Rank.JACK, Suit.HEARTS)
        )
        assert compare_hands(pair_k, pair_j) > 0

    def test_higher_high_card_wins(self) -> None:
        high = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.KING, Suit.SPADES, Rank.JACK, Suit.CLUBS)
        )
        low = evaluate_hand(
            make_hand(Rank.ACE, Suit.DIAMONDS, Rank.KING, Suit.CLUBS, Rank.TEN, Suit.HEARTS)
        )
        assert compare_hands(high, low) > 0

    def test_high_card_first_rank_decides(self) -> None:
        """散牌最大牌不同时，直接比最大牌"""
        higher = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.FIVE, Suit.SPADES, Rank.TWO, Suit.CLUBS)
        )
        lower = evaluate_hand(
            make_hand(Rank.KING, Suit.DIAMONDS, Rank.TEN, Suit.CLUBS, Rank.SEVEN, Suit.HEARTS)
        )
        assert compare_hands(higher, lower) > 0

    # ---- 相等情况 ----

    def test_equal_hands(self) -> None:
        """完全相同的手牌（不同花色）应返回 0"""
        hand_a = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.KING, Suit.SPADES, Rank.JACK, Suit.CLUBS)
        )
        hand_b = evaluate_hand(
            make_hand(Rank.ACE, Suit.DIAMONDS, Rank.KING, Suit.CLUBS, Rank.JACK, Suit.HEARTS)
        )
        assert compare_hands(hand_a, hand_b) == 0

    def test_equal_pairs(self) -> None:
        hand_a = evaluate_hand(
            make_hand(Rank.KING, Suit.HEARTS, Rank.KING, Suit.SPADES, Rank.FIVE, Suit.CLUBS)
        )
        hand_b = evaluate_hand(
            make_hand(Rank.KING, Suit.DIAMONDS, Rank.KING, Suit.CLUBS, Rank.FIVE, Suit.HEARTS)
        )
        assert compare_hands(hand_a, hand_b) == 0

    # ---- 对称性 ----

    def test_compare_symmetry(self) -> None:
        """如果 A > B，则 B < A"""
        hand_a = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.ACE, Suit.SPADES, Rank.ACE, Suit.CLUBS)
        )
        hand_b = evaluate_hand(
            make_hand(Rank.KING, Suit.HEARTS, Rank.KING, Suit.SPADES, Rank.KING, Suit.CLUBS)
        )
        assert compare_hands(hand_a, hand_b) > 0
        assert compare_hands(hand_b, hand_a) < 0


# ============================================================
# A-2-3 特殊顺子边界测试
# ============================================================


class TestA23SpecialStraight:
    """A-2-3 最小顺子相关的边界测试"""

    def test_a23_is_smallest_straight(self) -> None:
        """A-2-3 是最小的顺子"""
        a23 = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.TWO, Suit.SPADES, Rank.THREE, Suit.CLUBS)
        )
        s345 = evaluate_hand(
            make_hand(Rank.THREE, Suit.HEARTS, Rank.FOUR, Suit.SPADES, Rank.FIVE, Suit.CLUBS)
        )
        assert a23.hand_type == HandType.STRAIGHT
        assert s345.hand_type == HandType.STRAIGHT
        assert compare_hands(s345, a23) > 0

    def test_a23_straight_flush_is_smallest_straight_flush(self) -> None:
        """A-2-3 同花顺是最小的同花顺"""
        a23_sf = evaluate_hand(
            make_hand(Rank.ACE, Suit.SPADES, Rank.TWO, Suit.SPADES, Rank.THREE, Suit.SPADES)
        )
        s345_sf = evaluate_hand(
            make_hand(Rank.THREE, Suit.HEARTS, Rank.FOUR, Suit.HEARTS, Rank.FIVE, Suit.HEARTS)
        )
        assert a23_sf.hand_type == HandType.STRAIGHT_FLUSH
        assert s345_sf.hand_type == HandType.STRAIGHT_FLUSH
        assert compare_hands(s345_sf, a23_sf) > 0

    def test_qka_is_largest_straight(self) -> None:
        """Q-K-A 是最大的顺子"""
        qka = evaluate_hand(
            make_hand(Rank.QUEEN, Suit.HEARTS, Rank.KING, Suit.SPADES, Rank.ACE, Suit.CLUBS)
        )
        jqk = evaluate_hand(
            make_hand(Rank.JACK, Suit.HEARTS, Rank.QUEEN, Suit.SPADES, Rank.KING, Suit.CLUBS)
        )
        assert compare_hands(qka, jqk) > 0

    def test_a23_loses_to_qka_straight(self) -> None:
        """A-2-3 应该输给 Q-K-A"""
        a23 = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.TWO, Suit.SPADES, Rank.THREE, Suit.CLUBS)
        )
        qka = evaluate_hand(
            make_hand(Rank.QUEEN, Suit.DIAMONDS, Rank.KING, Suit.CLUBS, Rank.ACE, Suit.HEARTS)
        )
        assert compare_hands(qka, a23) > 0
        assert compare_hands(a23, qka) < 0


# ============================================================
# ranks 排序正确性测试
# ============================================================


class TestHandResultRanks:
    """测试 HandResult.ranks 的排序正确性（影响同牌型比较）"""

    def test_pair_ranks_pair_first(self) -> None:
        """对子的 ranks 中，对子点数应在前"""
        result = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.FIVE, Suit.SPADES, Rank.FIVE, Suit.CLUBS)
        )
        assert result.hand_type == HandType.PAIR
        # ranks 应为 [5, 5, A]（对子在前，单张在后）
        assert result.ranks[0] == Rank.FIVE
        assert result.ranks[1] == Rank.FIVE
        assert result.ranks[2] == Rank.ACE

    def test_high_card_ranks_descending(self) -> None:
        """散牌的 ranks 应从大到小排列"""
        result = evaluate_hand(
            make_hand(Rank.TWO, Suit.HEARTS, Rank.JACK, Suit.SPADES, Rank.SEVEN, Suit.CLUBS)
        )
        assert result.ranks == [Rank.JACK, Rank.SEVEN, Rank.TWO]

    def test_a23_straight_ranks(self) -> None:
        """A-2-3 顺子的 ranks 中 A 应排最后（视为 1）"""
        result = evaluate_hand(
            make_hand(Rank.ACE, Suit.HEARTS, Rank.TWO, Suit.SPADES, Rank.THREE, Suit.CLUBS)
        )
        assert result.ranks == [Rank.THREE, Rank.TWO, Rank.ACE]

    def test_normal_straight_ranks_descending(self) -> None:
        """普通顺子的 ranks 应从大到小排列"""
        result = evaluate_hand(
            make_hand(Rank.NINE, Suit.HEARTS, Rank.TEN, Suit.SPADES, Rank.JACK, Suit.CLUBS)
        )
        assert result.ranks == [Rank.JACK, Rank.TEN, Rank.NINE]
