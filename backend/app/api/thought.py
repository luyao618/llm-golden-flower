"""心路历程 REST API (T4.4)

提供 AI 心路历程、叙事、总结、经验回顾的查询端点：
- GET /{game_id}/thoughts/{agent_id}                    所有思考记录
- GET /{game_id}/thoughts/{agent_id}/round/{round_num}  某局思考记录
- GET /{game_id}/narrative/{agent_id}/round/{round_num}  局叙事
- GET /{game_id}/summary/{agent_id}                     游戏总结
- GET /{game_id}/reviews/{agent_id}                     经验回顾列表
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.schemas import (
    ExperienceReviewDB,
    GameSummaryDB,
    RoundNarrativeDB,
    ThoughtRecordDB,
)

router = APIRouter()


# ---- Response Models ----


class ThoughtRecordResponse(BaseModel):
    """单条思考记录响应"""

    id: int
    agent_id: str
    game_id: str
    round_number: int
    turn_number: int
    hand_evaluation: str | None = None
    opponent_analysis: str | None = None
    chat_analysis: str | None = None
    risk_assessment: str | None = None
    decision: str
    decision_target: str | None = None
    reasoning: str | None = None
    confidence: float | None = None
    emotion: str | None = None
    table_talk: str | None = None
    raw_response: str | None = None
    created_at: str | None = None


class ThoughtListResponse(BaseModel):
    """思考记录列表响应"""

    game_id: str
    agent_id: str
    round_number: int | None = None
    thoughts: list[ThoughtRecordResponse]
    count: int


class RoundNarrativeResponse(BaseModel):
    """局叙事响应"""

    id: int
    agent_id: str
    game_id: str
    round_number: int
    narrative: str
    outcome: str | None = None
    created_at: str | None = None


class GameSummaryResponse(BaseModel):
    """游戏总结响应"""

    id: int
    agent_id: str
    game_id: str
    stats: dict | None = None
    key_moments: list | None = None
    opponent_impressions: dict | None = None
    self_reflection: str | None = None
    chat_strategy_summary: str | None = None
    learning_journey: str | None = None
    narrative_summary: str | None = None
    created_at: str | None = None


class ExperienceReviewResponse(BaseModel):
    """经验回顾响应"""

    id: int
    agent_id: str
    game_id: str
    trigger: str
    triggered_at_round: int
    rounds_reviewed: list | None = None
    self_analysis: str | None = None
    opponent_patterns: dict | None = None
    strategy_adjustment: str | None = None
    confidence_shift: float | None = None
    strategy_context: str | None = None
    created_at: str | None = None


class ReviewListResponse(BaseModel):
    """经验回顾列表响应"""

    game_id: str
    agent_id: str
    reviews: list[ExperienceReviewResponse]
    count: int


# ---- Helper Functions ----


def _thought_db_to_response(record: ThoughtRecordDB) -> ThoughtRecordResponse:
    """将 ThoughtRecordDB 转为响应模型"""
    return ThoughtRecordResponse(
        id=record.id,
        agent_id=record.agent_id,
        game_id=record.game_id,
        round_number=record.round_number,
        turn_number=record.turn_number,
        hand_evaluation=record.hand_evaluation,
        opponent_analysis=record.opponent_analysis,
        chat_analysis=record.chat_analysis,
        risk_assessment=record.risk_assessment,
        decision=record.decision,
        decision_target=record.decision_target,
        reasoning=record.reasoning,
        confidence=record.confidence,
        emotion=record.emotion,
        table_talk=record.table_talk,
        raw_response=record.raw_response,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


def _narrative_db_to_response(record: RoundNarrativeDB) -> RoundNarrativeResponse:
    """将 RoundNarrativeDB 转为响应模型"""
    return RoundNarrativeResponse(
        id=record.id,
        agent_id=record.agent_id,
        game_id=record.game_id,
        round_number=record.round_number,
        narrative=record.narrative,
        outcome=record.outcome,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


def _summary_db_to_response(record: GameSummaryDB) -> GameSummaryResponse:
    """将 GameSummaryDB 转为响应模型"""
    return GameSummaryResponse(
        id=record.id,
        agent_id=record.agent_id,
        game_id=record.game_id,
        stats=record.stats,
        key_moments=record.key_moments,
        opponent_impressions=record.opponent_impressions,
        self_reflection=record.self_reflection,
        chat_strategy_summary=record.chat_strategy_summary,
        learning_journey=record.learning_journey,
        narrative_summary=record.narrative_summary,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


def _review_db_to_response(record: ExperienceReviewDB) -> ExperienceReviewResponse:
    """将 ExperienceReviewDB 转为响应模型"""
    return ExperienceReviewResponse(
        id=record.id,
        agent_id=record.agent_id,
        game_id=record.game_id,
        trigger=record.trigger,
        triggered_at_round=record.triggered_at_round,
        rounds_reviewed=record.rounds_reviewed,
        self_analysis=record.self_analysis,
        opponent_patterns=record.opponent_patterns,
        strategy_adjustment=record.strategy_adjustment,
        confidence_shift=record.confidence_shift,
        strategy_context=record.strategy_context,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


# ---- Endpoints ----


@router.get(
    "/{game_id}/thoughts/{agent_id}",
    response_model=ThoughtListResponse,
    summary="获取 AI 的所有思考记录",
)
async def get_agent_thoughts(
    game_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取某个 AI 在某场游戏中的所有思考记录

    按局号和 turn_number 排序返回。
    """
    stmt = (
        select(ThoughtRecordDB)
        .where(ThoughtRecordDB.game_id == game_id, ThoughtRecordDB.agent_id == agent_id)
        .order_by(ThoughtRecordDB.round_number, ThoughtRecordDB.turn_number)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    thoughts = [_thought_db_to_response(r) for r in records]
    return ThoughtListResponse(
        game_id=game_id,
        agent_id=agent_id,
        round_number=None,
        thoughts=thoughts,
        count=len(thoughts),
    )


@router.get(
    "/{game_id}/thoughts/{agent_id}/round/{round_num}",
    response_model=ThoughtListResponse,
    summary="获取 AI 某局的思考记录",
)
async def get_agent_round_thoughts(
    game_id: str,
    agent_id: str,
    round_num: int,
    db: AsyncSession = Depends(get_db),
):
    """获取某个 AI 在某场游戏的特定局中的思考记录

    按 turn_number 排序返回。
    """
    stmt = (
        select(ThoughtRecordDB)
        .where(
            ThoughtRecordDB.game_id == game_id,
            ThoughtRecordDB.agent_id == agent_id,
            ThoughtRecordDB.round_number == round_num,
        )
        .order_by(ThoughtRecordDB.turn_number)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    thoughts = [_thought_db_to_response(r) for r in records]
    return ThoughtListResponse(
        game_id=game_id,
        agent_id=agent_id,
        round_number=round_num,
        thoughts=thoughts,
        count=len(thoughts),
    )


@router.get(
    "/{game_id}/narrative/{agent_id}/round/{round_num}",
    response_model=RoundNarrativeResponse,
    summary="获取 AI 某局的叙事",
)
async def get_round_narrative(
    game_id: str,
    agent_id: str,
    round_num: int,
    db: AsyncSession = Depends(get_db),
):
    """获取某个 AI 在某局的第一人称叙事总结"""
    stmt = select(RoundNarrativeDB).where(
        RoundNarrativeDB.game_id == game_id,
        RoundNarrativeDB.agent_id == agent_id,
        RoundNarrativeDB.round_number == round_num,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"未找到游戏 {game_id} 中 Agent {agent_id} 第 {round_num} 局的叙事记录",
        )

    return _narrative_db_to_response(record)


@router.get(
    "/{game_id}/summary/{agent_id}",
    response_model=GameSummaryResponse,
    summary="获取 AI 的游戏总结",
)
async def get_game_summary(
    game_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取某个 AI 对整场游戏的总结报告"""
    stmt = select(GameSummaryDB).where(
        GameSummaryDB.game_id == game_id,
        GameSummaryDB.agent_id == agent_id,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"未找到游戏 {game_id} 中 Agent {agent_id} 的游戏总结",
        )

    return _summary_db_to_response(record)


@router.get(
    "/{game_id}/reviews/{agent_id}",
    response_model=ReviewListResponse,
    summary="获取 AI 的经验回顾列表",
)
async def get_experience_reviews(
    game_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取某个 AI 在某场游戏中的所有经验回顾记录

    按触发局号排序返回。
    """
    stmt = (
        select(ExperienceReviewDB)
        .where(
            ExperienceReviewDB.game_id == game_id,
            ExperienceReviewDB.agent_id == agent_id,
        )
        .order_by(ExperienceReviewDB.triggered_at_round)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    reviews = [_review_db_to_response(r) for r in records]
    return ReviewListResponse(
        game_id=game_id,
        agent_id=agent_id,
        reviews=reviews,
        count=len(reviews),
    )
