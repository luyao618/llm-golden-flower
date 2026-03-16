"""游戏状态数据模型

定义炸金花游戏中的核心游戏状态类型：牌型、玩家、游戏阶段、操作、局面状态等。
"""

from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, Field

from app.models.card import Card, Rank


# ---- 牌型相关 ----


class HandType(int, Enum):
    """牌型枚举（值越大牌型越大）"""

    HIGH_CARD = 1  # 散牌
    PAIR = 2  # 对子
    STRAIGHT = 3  # 顺子
    FLUSH = 4  # 同花
    STRAIGHT_FLUSH = 5  # 同花顺
    THREE_OF_A_KIND = 6  # 豹子

    @property
    def chinese_name(self) -> str:
        """返回牌型的中文名称"""
        names = {
            HandType.HIGH_CARD: "散牌",
            HandType.PAIR: "对子",
            HandType.STRAIGHT: "顺子",
            HandType.FLUSH: "同花",
            HandType.STRAIGHT_FLUSH: "同花顺",
            HandType.THREE_OF_A_KIND: "豹子",
        }
        return names[self]


class HandResult(BaseModel):
    """手牌评估结果

    Attributes:
        hand_type: 牌型
        ranks: 用于同牌型比较的排序后点数列表（从大到小）
        description: 人类可读描述，如 "一对K"
    """

    hand_type: HandType
    ranks: list[Rank]
    description: str


# ---- 玩家相关 ----


class PlayerType(str, Enum):
    """玩家类型"""

    HUMAN = "human"
    AI = "ai"


class PlayerStatus(str, Enum):
    """玩家状态"""

    ACTIVE_BLIND = "active_blind"  # 未看牌（暗注）
    ACTIVE_SEEN = "active_seen"  # 已看牌（明注）
    FOLDED = "folded"  # 已弃牌
    OUT = "out"  # 筹码用完，出局


class Player(BaseModel):
    """玩家信息

    Attributes:
        id: 唯一标识符
        name: 显示名称
        avatar: 头像标识
        player_type: 人类或 AI
        chips: 当前筹码
        status: 当前状态
        hand: 手牌（3 张牌），对前端隐藏 AI 的牌
        total_bet_this_round: 本局累计下注金额
        model_id: AI 使用的模型标识（人类玩家为 None）
        personality: AI 性格类型（人类玩家为 None）
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    avatar: str = ""
    player_type: PlayerType
    chips: int = 1000
    status: PlayerStatus = PlayerStatus.ACTIVE_BLIND
    hand: list[Card] | None = None
    total_bet_this_round: int = 0
    model_id: str | None = None

    @property
    def is_active(self) -> bool:
        """判断玩家是否仍在本局中"""
        return self.status in (PlayerStatus.ACTIVE_BLIND, PlayerStatus.ACTIVE_SEEN)

    @property
    def has_seen_cards(self) -> bool:
        """判断玩家是否已看牌"""
        return self.status == PlayerStatus.ACTIVE_SEEN

    @property
    def is_ai(self) -> bool:
        """判断是否为 AI 玩家"""
        return self.player_type == PlayerType.AI


# ---- 游戏操作相关 ----


class GamePhase(str, Enum):
    """游戏阶段"""

    WAITING = "waiting"  # 等待开始
    DEALING = "dealing"  # 发牌中
    BETTING = "betting"  # 下注阶段
    COMPARING = "comparing"  # 比牌中
    SETTLEMENT = "settlement"  # 结算中
    GAME_OVER = "game_over"  # 游戏结束


class GameAction(str, Enum):
    """游戏操作"""

    FOLD = "fold"  # 弃牌
    CALL = "call"  # 跟注
    RAISE = "raise"  # 加注
    CHECK_CARDS = "check_cards"  # 看牌
    COMPARE = "compare"  # 比牌


class ActionRecord(BaseModel):
    """操作记录

    Attributes:
        player_id: 执行操作的玩家 ID
        player_name: 玩家名称（方便显示）
        action: 操作类型
        amount: 下注金额（弃牌和看牌时为 None）
        target_id: 比牌对象 ID（仅比牌时有值）
        timestamp: 操作时间戳
    """

    player_id: str
    player_name: str = ""
    action: GameAction
    amount: int | None = None
    target_id: str | None = None
    timestamp: float = 0.0


# ---- 局面状态 ----


class RoundResult(BaseModel):
    """单局结算结果

    Attributes:
        round_number: 局号
        winner_id: 获胜者 ID
        winner_name: 获胜者名称
        pot: 底池总额
        win_method: 获胜方式描述（如 "弃牌胜出"、"比牌获胜"）
        hands_revealed: 亮牌信息（比牌时才有）
        player_chip_changes: 各玩家筹码变化
    """

    round_number: int
    winner_id: str
    winner_name: str = ""
    pot: int
    win_method: str = ""
    hands_revealed: dict[str, list[Card]] | None = None
    player_chip_changes: dict[str, int] = Field(default_factory=dict)


class RoundState(BaseModel):
    """当前局的状态

    Attributes:
        round_number: 当前是第几局
        pot: 底池筹码
        current_bet: 当前注额基数
        dealer_index: 庄家位置（players 列表中的索引）
        current_player_index: 当前行动玩家（players 列表中的索引）
        actions: 本局行动历史
        phase: 当前游戏阶段
        turn_count: 当前轮次（一圈为一轮）
        max_turns: 最大轮次
    """

    round_number: int
    pot: int = 0
    current_bet: int = 10
    dealer_index: int = 0
    current_player_index: int = 0
    actions: list[ActionRecord] = Field(default_factory=list)
    phase: GamePhase = GamePhase.DEALING
    turn_count: int = 0
    max_turns: int = 10


class GameConfig(BaseModel):
    """游戏配置

    Attributes:
        initial_chips: 初始筹码
        ante: 底注
        max_bet: 单局下注上限
        max_turns: 每局最大轮数
    """

    initial_chips: int = 1000
    ante: int = 10
    max_bet: int = 200
    max_turns: int = 10


class GameState(BaseModel):
    """完整游戏状态

    Attributes:
        game_id: 游戏唯一标识符
        players: 所有玩家列表
        current_round: 当前局的状态（None 表示尚未开局）
        round_history: 历史局结果
        config: 游戏配置
        status: 游戏整体状态
    """

    game_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    players: list[Player] = Field(default_factory=list)
    current_round: RoundState | None = None
    round_history: list[RoundResult] = Field(default_factory=list)
    config: GameConfig = Field(default_factory=GameConfig)
    status: str = "waiting"  # waiting / playing / finished

    def get_player_by_id(self, player_id: str) -> Player | None:
        """根据 ID 查找玩家"""
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    def get_active_players(self) -> list[Player]:
        """获取当前局中仍在牌桌上的玩家"""
        return [p for p in self.players if p.is_active]

    def get_alive_players(self) -> list[Player]:
        """获取未出局的玩家（包括已弃牌但筹码 > 0 的玩家）"""
        return [p for p in self.players if p.status != PlayerStatus.OUT]
