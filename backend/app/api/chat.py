"""聊天记录 REST API (T4.4)

提供聊天消息历史的查询端点：
- GET /{game_id}/chat                    所有聊天记录
- GET /{game_id}/chat/round/{round_num}  某局聊天记录
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.schemas import ChatMessageDB

router = APIRouter()


# ---- Response Models ----


class ChatMessageResponse(BaseModel):
    """单条聊天消息响应"""

    id: str
    game_id: str
    round_number: int
    player_id: str
    player_name: str
    message_type: str
    content: str
    timestamp: float = 0.0
    related_action: str | None = None
    trigger_event: str | None = None
    inner_thought: str | None = None
    created_at: str | None = None


class ChatListResponse(BaseModel):
    """聊天消息列表响应"""

    game_id: str
    round_number: int | None = None
    messages: list[ChatMessageResponse]
    count: int


# ---- Helper Functions ----


def _chat_db_to_response(record: ChatMessageDB) -> ChatMessageResponse:
    """将 ChatMessageDB 转为响应模型"""
    return ChatMessageResponse(
        id=str(record.id),
        game_id=record.game_id,
        round_number=record.round_number,
        player_id=record.sender_id,
        player_name=record.sender_name,
        message_type=record.message_type,
        content=record.content,
        timestamp=record.created_at.timestamp() if record.created_at else 0.0,
        related_action=record.related_action,
        trigger_event=record.trigger_event,
        inner_thought=record.inner_thought,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


# ---- Endpoints ----


@router.get(
    "/{game_id}/chat",
    response_model=ChatListResponse,
    summary="获取游戏的所有聊天记录",
)
async def get_game_chat(
    game_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取某场游戏的所有聊天消息

    按创建时间排序返回。
    """
    stmt = (
        select(ChatMessageDB)
        .where(ChatMessageDB.game_id == game_id)
        .order_by(ChatMessageDB.created_at)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    messages = [_chat_db_to_response(r) for r in records]
    return ChatListResponse(
        game_id=game_id,
        round_number=None,
        messages=messages,
        count=len(messages),
    )


@router.get(
    "/{game_id}/chat/round/{round_num}",
    response_model=ChatListResponse,
    summary="获取某局的聊天记录",
)
async def get_round_chat(
    game_id: str,
    round_num: int,
    db: AsyncSession = Depends(get_db),
):
    """获取某场游戏特定局的聊天消息

    按创建时间排序返回。
    """
    stmt = (
        select(ChatMessageDB)
        .where(
            ChatMessageDB.game_id == game_id,
            ChatMessageDB.round_number == round_num,
        )
        .order_by(ChatMessageDB.created_at)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    messages = [_chat_db_to_response(r) for r in records]
    return ChatListResponse(
        game_id=game_id,
        round_number=round_num,
        messages=messages,
        count=len(messages),
    )
