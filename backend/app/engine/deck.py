"""牌组管理

提供 Deck 类，负责洗牌和发牌。
"""

from __future__ import annotations

import random

from app.models.card import ALL_CARDS, Card


class Deck:
    """一副 52 张扑克牌的牌组

    Attributes:
        _cards: 当前剩余的牌
    """

    def __init__(self, seed: int | None = None) -> None:
        """初始化牌组并洗牌

        Args:
            seed: 随机种子，用于测试时获得确定性结果。None 表示随机。
        """
        self._rng = random.Random(seed)
        self._cards: list[Card] = []
        self.reset()

    def reset(self) -> None:
        """重置牌组为完整的 52 张牌并洗牌"""
        self._cards = list(ALL_CARDS)
        self.shuffle()

    def shuffle(self) -> None:
        """洗牌"""
        self._rng.shuffle(self._cards)

    def deal(self, count: int = 1) -> list[Card]:
        """从牌组顶部发牌

        Args:
            count: 发牌数量

        Returns:
            发出的牌列表

        Raises:
            ValueError: 牌组中剩余牌不够时抛出
        """
        if count < 0:
            raise ValueError(f"发牌数量不能为负数: {count}")
        if count > len(self._cards):
            raise ValueError(f"牌组中仅剩 {len(self._cards)} 张牌，无法发出 {count} 张")
        dealt = self._cards[:count]
        self._cards = self._cards[count:]
        return dealt

    def deal_one(self) -> Card:
        """发一张牌

        Returns:
            一张牌

        Raises:
            ValueError: 牌组为空时抛出
        """
        return self.deal(1)[0]

    @property
    def remaining(self) -> int:
        """返回牌组中剩余的牌数"""
        return len(self._cards)

    def __len__(self) -> int:
        return len(self._cards)

    def __repr__(self) -> str:
        return f"Deck(remaining={self.remaining})"
