"""扑克牌数据模型

定义炸金花游戏中的扑克牌相关类型：花色、点数、卡牌。
"""

from __future__ import annotations

from enum import Enum
from functools import total_ordering

from pydantic import BaseModel


class Suit(str, Enum):
    """花色枚举"""

    HEARTS = "hearts"  # 红心 ♥
    DIAMONDS = "diamonds"  # 方块 ♦
    CLUBS = "clubs"  # 梅花 ♣
    SPADES = "spades"  # 黑桃 ♠

    @property
    def symbol(self) -> str:
        """返回花色的 Unicode 符号"""
        symbols = {
            Suit.HEARTS: "♥",
            Suit.DIAMONDS: "♦",
            Suit.CLUBS: "♣",
            Suit.SPADES: "♠",
        }
        return symbols[self]

    @property
    def chinese_name(self) -> str:
        """返回花色的中文名称"""
        names = {
            Suit.HEARTS: "红心",
            Suit.DIAMONDS: "方块",
            Suit.CLUBS: "梅花",
            Suit.SPADES: "黑桃",
        }
        return names[self]


@total_ordering
class Rank(int, Enum):
    """点数枚举

    数值用于比较大小，A 最大为 14。
    """

    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Rank):
            return self.value < other.value
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Rank):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)

    @property
    def display(self) -> str:
        """返回点数的显示文本"""
        display_map = {
            Rank.TWO: "2",
            Rank.THREE: "3",
            Rank.FOUR: "4",
            Rank.FIVE: "5",
            Rank.SIX: "6",
            Rank.SEVEN: "7",
            Rank.EIGHT: "8",
            Rank.NINE: "9",
            Rank.TEN: "10",
            Rank.JACK: "J",
            Rank.QUEEN: "Q",
            Rank.KING: "K",
            Rank.ACE: "A",
        }
        return display_map[self]

    @property
    def chinese_name(self) -> str:
        """返回点数的中文名称（用于牌型描述）"""
        names = {
            Rank.TWO: "2",
            Rank.THREE: "3",
            Rank.FOUR: "4",
            Rank.FIVE: "5",
            Rank.SIX: "6",
            Rank.SEVEN: "7",
            Rank.EIGHT: "8",
            Rank.NINE: "9",
            Rank.TEN: "10",
            Rank.JACK: "J",
            Rank.QUEEN: "Q",
            Rank.KING: "K",
            Rank.ACE: "A",
        }
        return names[self]


class Card(BaseModel):
    """单张扑克牌

    Attributes:
        suit: 花色
        rank: 点数
    """

    suit: Suit
    rank: Rank

    model_config = {"frozen": True}

    def __str__(self) -> str:
        return f"{self.suit.symbol}{self.rank.display}"

    def __repr__(self) -> str:
        return f"Card({self.suit.symbol}{self.rank.display})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Card):
            return self.suit == other.suit and self.rank == other.rank
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.suit, self.rank))

    def __lt__(self, other: object) -> bool:
        """比较两张牌大小，先按点数再按花色"""
        if isinstance(other, Card):
            if self.rank != other.rank:
                return self.rank < other.rank
            return self.suit.value < other.suit.value
        return NotImplemented

    @property
    def chinese_description(self) -> str:
        """返回中文描述，如 '黑桃A'"""
        return f"{self.suit.chinese_name}{self.rank.chinese_name}"


# 预生成完整的 52 张牌，方便使用
ALL_CARDS: list[Card] = [Card(suit=suit, rank=rank) for suit in Suit for rank in Rank]
