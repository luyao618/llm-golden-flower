"""SQLAlchemy ORM 模型

定义 8 张数据库表，对应游戏的全部持久化数据：
- games: 游戏主表
- players: 玩家表
- rounds: 局记录表
- thought_records: AI 心路历程表
- chat_messages: 聊天记录表
- experience_reviews: 经验回顾表
- round_narratives: 局叙事表
- game_summaries: 游戏总结表
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class GameDB(Base):
    """游戏主表

    存储游戏的基本信息和配置。

    Columns:
        id: 游戏唯一标识（UUID 字符串）
        config: 游戏配置（JSON，包含 initial_chips, ante, max_bet, max_turns）
        status: 游戏状态 (waiting / playing / finished)
        created_at: 创建时间
        finished_at: 结束时间
    """

    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="waiting")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关系
    players: Mapped[list[PlayerDB]] = relationship(
        "PlayerDB", back_populates="game", cascade="all, delete-orphan"
    )
    rounds: Mapped[list[RoundDB]] = relationship(
        "RoundDB", back_populates="game", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list[ChatMessageDB]] = relationship(
        "ChatMessageDB", back_populates="game", cascade="all, delete-orphan"
    )


class PlayerDB(Base):
    """玩家表

    存储参与游戏的玩家信息（人类 + AI）。

    Columns:
        id: 玩家唯一标识（UUID 字符串）
        game_id: 所属游戏 ID（外键）
        name: 玩家名称
        avatar: 头像标识
        player_type: 类型 (human / ai)
        model_id: AI 使用的模型标识（人类玩家为 NULL）
        personality: AI 性格类型（人类玩家为 NULL）
        initial_chips: 初始筹码
        current_chips: 当前筹码
    """

    __tablename__ = "players"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar: Mapped[str] = mapped_column(String(50), nullable=True, default="")
    player_type: Mapped[str] = mapped_column(String(10), nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    personality: Mapped[str | None] = mapped_column(String(30), nullable=True)
    initial_chips: Mapped[int] = mapped_column(Integer, nullable=False)
    current_chips: Mapped[int] = mapped_column(Integer, nullable=False)

    # 关系
    game: Mapped[GameDB] = relationship("GameDB", back_populates="players")
    thought_records: Mapped[list[ThoughtRecordDB]] = relationship(
        "ThoughtRecordDB", back_populates="player", cascade="all, delete-orphan"
    )
    experience_reviews: Mapped[list[ExperienceReviewDB]] = relationship(
        "ExperienceReviewDB", back_populates="player", cascade="all, delete-orphan"
    )
    round_narratives: Mapped[list[RoundNarrativeDB]] = relationship(
        "RoundNarrativeDB", back_populates="player", cascade="all, delete-orphan"
    )
    game_summaries: Mapped[list[GameSummaryDB]] = relationship(
        "GameSummaryDB", back_populates="player", cascade="all, delete-orphan"
    )


class RoundDB(Base):
    """局记录表

    存储每局的完整行动记录和结果。

    Columns:
        id: 自增主键
        game_id: 所属游戏 ID（外键）
        round_number: 局号
        pot: 底池总额
        winner_id: 获胜者 ID
        win_method: 获胜方式描述
        actions: 完整行动记录（JSON 数组）
        hands: 各玩家手牌（JSON，局结束后记录）
        player_chip_changes: 各玩家筹码变化（JSON）
        created_at: 创建时间
    """

    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    win_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    actions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    hands: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    player_chip_changes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # 关系
    game: Mapped[GameDB] = relationship("GameDB", back_populates="rounds")


class ThoughtRecordDB(Base):
    """心路历程表

    存储 AI 每次决策的完整思考记录。

    Columns:
        id: 自增主键
        agent_id: Agent（玩家）ID（外键）
        game_id: 所属游戏 ID（外键）
        round_number: 局号
        turn_number: 该局中的第几次行动
        hand_evaluation: 手牌评估
        opponent_analysis: 对手分析
        chat_analysis: 对聊天内容的分析
        risk_assessment: 风险评估
        decision: 最终决策操作
        decision_target: 比牌对象 ID
        reasoning: 决策理由
        confidence: 信心值 0-1
        emotion: 情绪标签
        table_talk: 操作时的发言（NULL 表示沉默）
        raw_response: 原始 LLM 输出文本
        created_at: 创建时间
    """

    __tablename__ = "thought_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("players.id"), nullable=False)
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hand_evaluation: Mapped[str | None] = mapped_column(Text, nullable=True)
    opponent_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    chat_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    decision_target: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    emotion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    table_talk: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # 关系
    player: Mapped[PlayerDB] = relationship("PlayerDB", back_populates="thought_records")


class ChatMessageDB(Base):
    """聊天记录表

    存储游戏中的所有聊天消息（行动发言、旁观插嘴、玩家消息、系统消息）。

    Columns:
        id: 自增主键
        game_id: 所属游戏 ID（外键）
        round_number: 所属局号
        sender_id: 发送者 ID
        sender_name: 发送者名称
        message_type: 消息类型 (action_talk / bystander_react / player_message / system_message)
        content: 消息文本内容
        related_action: 关联的游戏操作（如有）
        trigger_event: 触发此消息的事件描述
        inner_thought: 发送者的内心想法（不公开展示）
        created_at: 创建时间
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sender_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sender_name: Mapped[str] = mapped_column(String(50), nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    related_action: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trigger_event: Mapped[str | None] = mapped_column(Text, nullable=True)
    inner_thought: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # 关系
    game: Mapped[GameDB] = relationship("GameDB", back_populates="chat_messages")


class ExperienceReviewDB(Base):
    """经验回顾表

    存储 AI 的经验回顾记录，包括触发原因、自我分析、对手模式和策略调整。

    Columns:
        id: 自增主键
        agent_id: Agent（玩家）ID（外键）
        game_id: 所属游戏 ID（外键）
        trigger: 触发原因 (consecutive_losses / big_loss / periodic / chip_crisis / opponent_shift)
        triggered_at_round: 在第几局前触发
        rounds_reviewed: 回顾了哪几局（JSON 数组）
        self_analysis: 自我分析文本
        opponent_patterns: 对各对手行为模式的总结（JSON）
        strategy_adjustment: 策略调整方向
        confidence_shift: 信心变化 (-1 到 1)
        strategy_context: 注入后续决策的策略摘要
        created_at: 创建时间
    """

    __tablename__ = "experience_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("players.id"), nullable=False)
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id"), nullable=False)
    trigger: Mapped[str] = mapped_column(String(30), nullable=False)
    triggered_at_round: Mapped[int] = mapped_column(Integer, nullable=False)
    rounds_reviewed: Mapped[list | None] = mapped_column(JSON, nullable=True)
    self_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    opponent_patterns: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    strategy_adjustment: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_shift: Mapped[float | None] = mapped_column(Float, nullable=True)
    strategy_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # 关系
    player: Mapped[PlayerDB] = relationship("PlayerDB", back_populates="experience_reviews")


class RoundNarrativeDB(Base):
    """局叙事表

    存储 AI 每局的第一人称叙事总结。

    Columns:
        id: 自增主键
        agent_id: Agent（玩家）ID（外键）
        game_id: 所属游戏 ID（外键）
        round_number: 局号
        narrative: 第一人称叙事文本
        outcome: 本局结果的一句话总结
        created_at: 创建时间
    """

    __tablename__ = "round_narratives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("players.id"), nullable=False)
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # 关系
    player: Mapped[PlayerDB] = relationship("PlayerDB", back_populates="round_narratives")


class GameSummaryDB(Base):
    """游戏总结表

    存储 AI 整场游戏的总结报告，包含统计数据和叙事内容。

    Columns:
        id: 自增主键
        agent_id: Agent（玩家）ID（外键）
        game_id: 所属游戏 ID（外键）
        stats: 统计数据（JSON，包含 rounds_played, rounds_won, fold_rate 等）
        key_moments: 关键时刻回顾（JSON 数组）
        opponent_impressions: 对各对手的印象（JSON 字典）
        self_reflection: 自我风格总结
        chat_strategy_summary: 聊天策略总结
        learning_journey: 学习历程总结
        narrative_summary: 完整叙事总结
        created_at: 创建时间
    """

    __tablename__ = "game_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("players.id"), nullable=False)
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id"), nullable=False)
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    key_moments: Mapped[list | None] = mapped_column(JSON, nullable=True)
    opponent_impressions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    self_reflection: Mapped[str | None] = mapped_column(Text, nullable=True)
    chat_strategy_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    learning_journey: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # 关系
    player: Mapped[PlayerDB] = relationship("PlayerDB", back_populates="game_summaries")
