"""游戏管理 REST API (T4.2)

提供游戏生命周期管理的 HTTP 端点：
- POST /create       创建新游戏
- GET  /{game_id}    获取游戏状态
- POST /{game_id}/start  开始游戏（开始第一局）
- POST /{game_id}/end    结束游戏
- POST /{game_id}/action 玩家执行操作
"""

from __future__ import annotations

import logging
import random
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.game_store import GameStore, get_game_store
from app.agents.agent_manager import get_agent_manager
from app.config import AI_AVATARS, AI_NAMES, get_available_models
from app.db.database import get_db
from app.db.schemas import GameDB, PlayerDB, RoundDB
from app.engine.game_manager import (
    ActionResult,
    GameError,
    GameNotStartedError,
    InvalidActionError,
    RoundNotActiveError,
    apply_action,
    create_game,
    get_visible_state,
    start_round,
)
from app.models.game import GameAction, GameConfig

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Request / Response Models ----


class AIPlayerConfig(BaseModel):
    """单个 AI 对手的配置"""

    model_id: str = Field(..., description="AI 模型标识，如 'openai-gpt4o'")
    name: str | None = Field(None, description="自定义名称（留空自动分配）")


class CreateGameRequest(BaseModel):
    """创建游戏请求"""

    player_name: str = Field("玩家", description="人类玩家名称")
    ai_opponents: list[AIPlayerConfig] = Field(
        ..., min_length=1, max_length=5, description="AI 对手配置（1-5 个）"
    )
    initial_chips: int = Field(1000, ge=100, le=100000, description="初始筹码")
    ante: int = Field(10, ge=1, le=1000, description="底注")
    max_bet: int = Field(200, ge=10, le=10000, description="单局下注上限")
    max_turns: int = Field(10, ge=3, le=50, description="每局最大轮数")


class CreateGameResponse(BaseModel):
    """创建游戏响应"""

    game_id: str
    message: str
    players: list[dict]


class PlayerActionRequest(BaseModel):
    """玩家操作请求"""

    player_id: str = Field(..., description="执行操作的玩家 ID")
    action: str = Field(..., description="操作类型: fold/call/raise/check_cards/compare")
    target_id: str | None = Field(None, description="比牌目标 ID（仅 compare 时需要）")


class ActionResponse(BaseModel):
    """操作响应"""

    success: bool
    action: str
    player_id: str
    amount: int = 0
    message: str = ""
    compare_result: dict | None = None
    round_ended: bool = False
    round_result: dict | None = None
    game_state: dict | None = None


class GameStateResponse(BaseModel):
    """游戏状态响应"""

    game_id: str
    status: str
    players: list[dict]
    current_round: dict | None
    round_history: list[dict]
    config: dict


# ---- Helper Functions ----


def _assign_ai_identity(ai_config: AIPlayerConfig, index: int, used_names: set[str]) -> dict:
    """为 AI 玩家分配名字、头像

    Args:
        ai_config: AI 配置
        index: AI 在列表中的索引
        used_names: 已使用的名字集合（避免重复）

    Returns:
        完整的 player_config 字典
    """
    # 名字
    name = ai_config.name
    if name is None:
        available = [n for n in AI_NAMES if n not in used_names]
        name = available[0] if available else f"AI-{index + 1}"
    used_names.add(name)

    # 头像
    avatar = AI_AVATARS[index % len(AI_AVATARS)]

    return {
        "name": name,
        "player_type": "ai",
        "model_id": ai_config.model_id,
        "avatar": avatar,
    }


def _action_result_to_dict(result: ActionResult) -> dict:
    """将 ActionResult 转为可序列化字典"""
    data = {
        "success": result.success,
        "action": result.action.value,
        "player_id": result.player_id,
        "amount": result.amount,
        "message": result.message,
        "compare_result": result.compare_result,
        "round_ended": result.round_ended,
    }
    if result.round_result is not None:
        data["round_result"] = result.round_result.model_dump(mode="json")
    else:
        data["round_result"] = None
    return data


# ---- Endpoints ----


@router.post("/create", response_model=CreateGameResponse)
async def create_game_endpoint(
    request: CreateGameRequest,
    db: AsyncSession = Depends(get_db),
    store: GameStore = Depends(get_game_store),
):
    """创建新游戏

    创建一个人类玩家 + N 个 AI 对手的游戏。
    游戏状态同时保存在内存（用于快速访问）和数据库（用于持久化）。
    """
    # 校验 AI 模型是否有效
    valid_models = {m["id"] for m in get_available_models()}
    for ai in request.ai_opponents:
        if ai.model_id not in valid_models:
            logger.warning("创建游戏失败 — 无效 AI 模型: %s", ai.model_id)
            raise HTTPException(
                status_code=400,
                detail=f"无效的 AI 模型: {ai.model_id}。可用模型: {sorted(valid_models)}",
            )

    # 构建玩家配置列表
    used_names: set[str] = {request.player_name}
    player_configs = [
        {
            "name": request.player_name,
            "player_type": "human",
            "avatar": "avatar_human",
        }
    ]
    for i, ai_config in enumerate(request.ai_opponents):
        player_configs.append(_assign_ai_identity(ai_config, i, used_names))

    # 创建游戏配置
    game_config = GameConfig(
        initial_chips=request.initial_chips,
        ante=request.ante,
        max_bet=request.max_bet,
        max_turns=request.max_turns,
    )

    # 调用引擎创建游戏
    game_state = create_game(player_configs, game_config)

    # 存入内存
    store.put(game_state)

    # 为 AI 玩家创建 Agent 实例（用于 WebSocket 中的 AI 决策）
    agent_mgr = get_agent_manager()
    ai_players = [p for p in game_state.players if p.player_type.value == "ai"]
    agent_configs = [
        {
            "agent_id": p.id,
            "name": p.name,
            "model_id": p.model_id or "openai-gpt4o-mini",
        }
        for p in ai_players
    ]
    agent_mgr.create_agents_for_game(game_state.game_id, agent_configs)

    # 持久化到数据库
    game_db = GameDB(
        id=game_state.game_id,
        config=game_config.model_dump(),
        status=game_state.status,
    )
    db.add(game_db)

    for player in game_state.players:
        player_db = PlayerDB(
            id=player.id,
            game_id=game_state.game_id,
            name=player.name,
            avatar=player.avatar,
            player_type=player.player_type.value,
            model_id=player.model_id,
            initial_chips=player.chips,
            current_chips=player.chips,
        )
        db.add(player_db)

    await db.commit()

    # 构建响应
    players_info = [
        {
            "id": p.id,
            "name": p.name,
            "player_type": p.player_type.value,
            "chips": p.chips,
            "model_id": p.model_id,
            "avatar": p.avatar,
        }
        for p in game_state.players
    ]

    ai_names = [p.name for p in game_state.players if p.player_type.value == "ai"]
    logger.info(
        "游戏创建成功 — game_id=%s, 玩家=%s, AI对手=%s, 初始筹码=%d",
        game_state.game_id,
        request.player_name,
        ai_names,
        request.initial_chips,
    )

    return CreateGameResponse(
        game_id=game_state.game_id,
        message=f"游戏已创建，共 {len(game_state.players)} 名玩家",
        players=players_info,
    )


@router.get("/{game_id}", response_model=GameStateResponse)
async def get_game_state_endpoint(
    game_id: str,
    player_id: str | None = None,
    store: GameStore = Depends(get_game_store),
):
    """获取游戏状态

    如果提供了 player_id，则应用信息隐藏（隐藏其他玩家手牌）。
    否则返回完整状态（仅用于调试）。
    """
    game = store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"游戏 {game_id} 不存在")

    if player_id:
        state_dict = get_visible_state(game, player_id)
    else:
        state_dict = game.model_dump(mode="json")

    return GameStateResponse(
        game_id=state_dict["game_id"],
        status=state_dict["status"],
        players=state_dict["players"],
        current_round=state_dict.get("current_round"),
        round_history=state_dict.get("round_history", []),
        config=state_dict.get("config", {}),
    )


@router.post("/{game_id}/start")
async def start_game_endpoint(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    store: GameStore = Depends(get_game_store),
):
    """开始游戏（开始第一局）

    调用引擎的 start_round 开始新一局：收底注、发牌、确定庄家。
    """
    game = store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"游戏 {game_id} 不存在")

    if game.status == "finished":
        raise HTTPException(status_code=400, detail="游戏已结束，无法开始新局")

    # 如果有进行中的局且在下注阶段，不允许重复开始
    if game.current_round is not None and game.current_round.phase.value == "betting":
        raise HTTPException(status_code=400, detail="当前局正在进行中")

    try:
        round_state = start_round(game)
    except GameError as e:
        logger.warning("开始游戏失败 — game_id=%s: %s", game_id, e)
        raise HTTPException(status_code=400, detail=str(e))

    logger.info(
        "游戏开始 — game_id=%s, 第%d局, 庄家=%s",
        game_id,
        round_state.round_number,
        game.players[round_state.dealer_index].name,
    )

    # 更新数据库中的游戏状态
    game_db = await db.get(GameDB, game_id)
    if game_db is not None:
        game_db.status = game.status

    # 更新各玩家当前筹码
    for player in game.players:
        player_db = await db.get(PlayerDB, player.id)
        if player_db is not None:
            player_db.current_chips = player.chips

    await db.commit()

    # 返回人类玩家视角的状态
    human_player = next((p for p in game.players if p.player_type.value == "human"), None)
    viewer_id = human_player.id if human_player else game.players[0].id
    visible_state = get_visible_state(game, viewer_id)

    return {
        "message": f"第 {round_state.round_number} 局开始",
        "round_number": round_state.round_number,
        "dealer_index": round_state.dealer_index,
        "pot": round_state.pot,
        "current_player_index": round_state.current_player_index,
        "game_state": visible_state,
    }


@router.post("/{game_id}/end")
async def end_game_endpoint(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    store: GameStore = Depends(get_game_store),
):
    """结束游戏

    将游戏状态标记为 finished，清理内存中的游戏状态。
    """
    game = store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"游戏 {game_id} 不存在")

    if game.status == "finished":
        raise HTTPException(status_code=400, detail="游戏已经结束")

    game.status = "finished"

    logger.info(
        "游戏结束 — game_id=%s, 最终排名: %s",
        game_id,
        [(p.name, p.chips) for p in sorted(game.players, key=lambda p: p.chips, reverse=True)],
    )

    # 更新数据库
    game_db = await db.get(GameDB, game_id)
    if game_db is not None:
        game_db.status = "finished"
        from datetime import datetime

        game_db.finished_at = datetime.now()

    # 更新各玩家最终筹码
    for player in game.players:
        player_db = await db.get(PlayerDB, player.id)
        if player_db is not None:
            player_db.current_chips = player.chips

    await db.commit()

    # 从内存中移除（可选，也可以保留一段时间）
    store.remove(game_id)

    return {
        "message": "游戏已结束",
        "game_id": game_id,
        "final_standings": [
            {"id": p.id, "name": p.name, "chips": p.chips}
            for p in sorted(game.players, key=lambda p: p.chips, reverse=True)
        ],
    }


@router.post("/{game_id}/action", response_model=ActionResponse)
async def player_action_endpoint(
    game_id: str,
    request: PlayerActionRequest,
    db: AsyncSession = Depends(get_db),
    store: GameStore = Depends(get_game_store),
):
    """玩家执行操作

    支持的操作: fold（弃牌）、call（跟注）、raise（加注）、check_cards（看牌）、compare（比牌）。
    """
    game = store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"游戏 {game_id} 不存在")

    # 解析操作类型
    try:
        action = GameAction(request.action)
    except ValueError:
        valid_actions = [a.value for a in GameAction]
        raise HTTPException(
            status_code=400,
            detail=f"无效的操作: {request.action}。有效操作: {valid_actions}",
        )

    # 执行操作
    try:
        result = apply_action(game, request.player_id, action, request.target_id)
    except GameNotStartedError as e:
        logger.warning(
            "玩家操作失败(未开始) — game=%s, player=%s: %s", game_id, request.player_id, e
        )
        raise HTTPException(status_code=400, detail=str(e))
    except RoundNotActiveError as e:
        logger.warning(
            "玩家操作失败(非活跃) — game=%s, player=%s: %s", game_id, request.player_id, e
        )
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidActionError as e:
        logger.warning(
            "玩家操作非法 — game=%s, player=%s, action=%s: %s",
            game_id,
            request.player_id,
            request.action,
            e,
        )
        raise HTTPException(status_code=422, detail=str(e))
    except GameError as e:
        logger.error("玩家操作错误 — game=%s, player=%s: %s", game_id, request.player_id, e)
        raise HTTPException(status_code=400, detail=str(e))

    # 如果本局结束，持久化局记录
    if result.round_ended and result.round_result is not None:
        rr = result.round_result
        round_db = RoundDB(
            game_id=game_id,
            round_number=rr.round_number,
            pot=rr.pot,
            winner_id=rr.winner_id,
            win_method=rr.win_method,
            actions=[a.model_dump(mode="json") for a in game.current_round.actions]
            if game.current_round
            else [],
            hands={
                pid: [c.model_dump(mode="json") for c in cards]
                for pid, cards in rr.hands_revealed.items()
            }
            if rr.hands_revealed
            else None,
            player_chip_changes=rr.player_chip_changes,
        )
        db.add(round_db)

        # 更新玩家筹码
        for player in game.players:
            player_db = await db.get(PlayerDB, player.id)
            if player_db is not None:
                player_db.current_chips = player.chips

        # 更新游戏状态
        game_db = await db.get(GameDB, game_id)
        if game_db is not None:
            game_db.status = game.status

        await db.commit()

    # 获取人类玩家视角的状态
    human_player = next((p for p in game.players if p.player_type.value == "human"), None)
    viewer_id = human_player.id if human_player else request.player_id
    visible_state = get_visible_state(game, viewer_id)

    result_dict = _action_result_to_dict(result)
    result_dict["game_state"] = visible_state

    return ActionResponse(**result_dict)
