"""游戏数据持久化辅助模块 (T4.4)

提供将内存中的游戏数据写入数据库的异步函数：
- persist_thought_record: 持久化单条思考记录
- persist_chat_message: 持久化单条聊天消息
- persist_round_narrative: 持久化局叙事
- persist_game_summary: 持久化游戏总结
- persist_experience_review: 持久化经验回顾

所有函数接受 AsyncSession 作为参数，由调用方负责事务管理。
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.schemas import (
    ChatMessageDB,
    ExperienceReviewDB,
    GameSummaryDB,
    RoundNarrativeDB,
    ThoughtRecordDB,
)
from app.models.chat import ChatMessage
from app.models.thought import ExperienceReview, GameSummary, RoundNarrative, ThoughtRecord

logger = logging.getLogger(__name__)


async def persist_thought_record(
    db: AsyncSession,
    game_id: str,
    record: ThoughtRecord,
) -> None:
    """将一条思考记录写入数据库

    Args:
        db: 异步数据库会话
        game_id: 游戏 ID
        record: ThoughtRecord 实例
    """
    db_record = ThoughtRecordDB(
        agent_id=record.agent_id,
        game_id=game_id,
        round_number=record.round_number,
        turn_number=record.turn_number,
        hand_evaluation=record.hand_evaluation or None,
        opponent_analysis=record.opponent_analysis or None,
        chat_analysis=record.chat_analysis,
        risk_assessment=record.risk_assessment or None,
        decision=record.decision.value,
        decision_target=record.decision_target,
        reasoning=record.reasoning or None,
        confidence=record.confidence,
        emotion=record.emotion or None,
        table_talk=record.table_talk,
        raw_response=record.raw_response or None,
    )
    db.add(db_record)
    logger.debug(
        "Persisted thought record: game=%s, agent=%s, round=%d, turn=%d",
        game_id,
        record.agent_id,
        record.round_number,
        record.turn_number,
    )


async def persist_chat_message(
    db: AsyncSession,
    msg: ChatMessage,
) -> None:
    """将一条聊天消息写入数据库

    Args:
        db: 异步数据库会话
        msg: ChatMessage 实例
    """
    db_record = ChatMessageDB(
        game_id=msg.game_id,
        round_number=msg.round_number,
        sender_id=msg.player_id,
        sender_name=msg.player_name,
        message_type=msg.message_type.value,
        content=msg.content,
        related_action=None,
        trigger_event=msg.trigger_event or None,
        inner_thought=msg.inner_thought or None,
    )
    db.add(db_record)
    logger.debug(
        "Persisted chat message: game=%s, sender=%s, type=%s",
        msg.game_id,
        msg.player_name,
        msg.message_type.value,
    )


async def persist_round_narrative(
    db: AsyncSession,
    game_id: str,
    narrative: RoundNarrative,
) -> None:
    """将一条局叙事写入数据库

    Args:
        db: 异步数据库会话
        game_id: 游戏 ID
        narrative: RoundNarrative 实例
    """
    db_record = RoundNarrativeDB(
        agent_id=narrative.agent_id,
        game_id=game_id,
        round_number=narrative.round_number,
        narrative=narrative.narrative,
        outcome=narrative.outcome or None,
    )
    db.add(db_record)
    logger.debug(
        "Persisted round narrative: game=%s, agent=%s, round=%d",
        game_id,
        narrative.agent_id,
        narrative.round_number,
    )


async def persist_game_summary(
    db: AsyncSession,
    game_id: str,
    summary: GameSummary,
) -> None:
    """将游戏总结写入数据库

    Args:
        db: 异步数据库会话
        game_id: 游戏 ID
        summary: GameSummary 实例
    """
    db_record = GameSummaryDB(
        agent_id=summary.agent_id,
        game_id=game_id,
        stats={
            "rounds_played": summary.rounds_played,
            "rounds_won": summary.rounds_won,
            "total_chips_won": summary.total_chips_won,
            "total_chips_lost": summary.total_chips_lost,
            "biggest_win": summary.biggest_win,
            "biggest_loss": summary.biggest_loss,
            "fold_rate": summary.fold_rate,
        },
        key_moments=summary.key_moments,
        opponent_impressions=summary.opponent_impressions,
        self_reflection=summary.self_reflection or None,
        chat_strategy_summary=summary.chat_strategy_summary or None,
        learning_journey=summary.learning_journey or None,
        narrative_summary=summary.narrative_summary or None,
    )
    db.add(db_record)
    logger.debug(
        "Persisted game summary: game=%s, agent=%s",
        game_id,
        summary.agent_id,
    )


async def persist_experience_review(
    db: AsyncSession,
    game_id: str,
    review: ExperienceReview,
) -> None:
    """将经验回顾记录写入数据库

    Args:
        db: 异步数据库会话
        game_id: 游戏 ID
        review: ExperienceReview 实例
    """
    db_record = ExperienceReviewDB(
        agent_id=review.agent_id,
        game_id=game_id,
        trigger=review.trigger.value,
        triggered_at_round=review.triggered_at_round,
        rounds_reviewed=review.rounds_reviewed,
        self_analysis=review.self_analysis or None,
        opponent_patterns=review.opponent_patterns if review.opponent_patterns else None,
        strategy_adjustment=review.strategy_adjustment or None,
        confidence_shift=review.confidence_shift,
        strategy_context=review.strategy_context or None,
    )
    db.add(db_record)
    logger.debug(
        "Persisted experience review: game=%s, agent=%s, trigger=%s, round=%d",
        game_id,
        review.agent_id,
        review.trigger.value,
        review.triggered_at_round,
    )
