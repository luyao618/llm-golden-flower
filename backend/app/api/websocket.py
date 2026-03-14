"""WebSocket + AI 回合调度 (T4.3)

实现:
- WebSocketManager: 管理每场游戏的 WebSocket 连接
- 客户端事件处理: player_action, chat_message, start_round
- 服务端事件推送: 全部 11 种事件类型
- process_ai_turns(): AI 回合的完整调度循环
- handle_player_chat(): 玩家消息处理 + AI 回应调度

WebSocket 连接: ws://localhost:8000/ws/{game_id}?player_id={player_id}
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agent_manager import AgentManager, get_agent_manager
from app.agents.base_agent import BaseAgent, ThoughtData
from app.agents.base_agent import LLMCallError
from app.agents.chat_engine import (
    ChatEngine,
    TriggerEvent,
    TriggerEventType,
    create_player_message_event,
    create_trigger_event_from_action,
)
from app.api.game_store import GameStore, get_game_store
from app.api.persistence import persist_chat_message, persist_thought_record
from app.db.database import get_db
from app.db.schemas import PlayerDB, RoundDB
from app.engine.game_manager import (
    ActionResult,
    GameError,
    InvalidActionError,
    apply_action,
    get_visible_state,
    start_round,
)
from app.models.chat import ChatContext, ChatMessage, ChatMessageType
from app.models.game import (
    GameAction,
    GamePhase,
    GameState,
    Player,
    PlayerStatus,
    PlayerType,
)
from app.models.thought import ThoughtRecord

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_db_session():
    """获取一个独立的数据库 session（用于 WebSocket 上下文中的持久化）

    WebSocket 端点无法使用 FastAPI 的 Depends(get_db)，
    因此需要手动创建和管理 session。

    Returns:
        AsyncSession: 异步数据库会话（调用方负责 commit/close）
    """
    from app.db.database import _get_session_factory

    factory = _get_session_factory()
    return factory()


# ---- WebSocket Connection Manager ----


class WebSocketManager:
    """管理每场游戏的 WebSocket 连接

    维护 game_id -> {player_id -> WebSocket} 的两级映射。
    支持向单个玩家或整场游戏的所有玩家广播消息。
    """

    def __init__(self) -> None:
        # game_id -> {player_id -> WebSocket}
        self._connections: dict[str, dict[str, WebSocket]] = {}
        # game_id -> ChatContext (per-game chat context)
        self._chat_contexts: dict[str, ChatContext] = {}

    async def connect(self, game_id: str, player_id: str, websocket: WebSocket) -> None:
        """接受 WebSocket 连接并注册"""
        await websocket.accept()
        if game_id not in self._connections:
            self._connections[game_id] = {}
        self._connections[game_id][player_id] = websocket
        logger.info("WebSocket connected: game=%s, player=%s", game_id, player_id)

    def disconnect(self, game_id: str, player_id: str) -> None:
        """断开连接并清理"""
        if game_id in self._connections:
            self._connections[game_id].pop(player_id, None)
            if not self._connections[game_id]:
                del self._connections[game_id]
        logger.info("WebSocket disconnected: game=%s, player=%s", game_id, player_id)

    def get_connections(self, game_id: str) -> dict[str, WebSocket]:
        """获取某场游戏的所有连接"""
        return self._connections.get(game_id, {})

    def get_chat_context(self, game_id: str) -> ChatContext:
        """获取某场游戏的聊天上下文"""
        if game_id not in self._chat_contexts:
            self._chat_contexts[game_id] = ChatContext()
        return self._chat_contexts[game_id]

    def remove_game(self, game_id: str) -> None:
        """清除某场游戏的所有连接和聊天上下文"""
        self._connections.pop(game_id, None)
        self._chat_contexts.pop(game_id, None)

    async def send_to_player(self, game_id: str, player_id: str, event: dict[str, Any]) -> None:
        """向单个玩家发送事件"""
        connections = self._connections.get(game_id, {})
        ws = connections.get(player_id)
        if ws is not None:
            try:
                await ws.send_json(event)
            except Exception as e:
                logger.warning(
                    "Failed to send to player %s in game %s: %s",
                    player_id,
                    game_id,
                    e,
                )

    async def broadcast(
        self, game_id: str, event: dict[str, Any], exclude: str | None = None
    ) -> None:
        """向游戏中所有玩家广播事件

        Args:
            game_id: 游戏 ID
            event: 要发送的事件
            exclude: 要排除的玩家 ID（可选）
        """
        connections = self._connections.get(game_id, {})
        for player_id, ws in list(connections.items()):
            if exclude and player_id == exclude:
                continue
            try:
                await ws.send_json(event)
            except Exception as e:
                logger.warning(
                    "Failed to broadcast to player %s in game %s: %s",
                    player_id,
                    game_id,
                    e,
                )

    async def broadcast_game_state(self, game_id: str, game: GameState) -> None:
        """向每个连接的玩家发送各自视角的游戏状态"""
        connections = self._connections.get(game_id, {})
        for player_id in list(connections.keys()):
            visible = get_visible_state(game, player_id)
            await self.send_to_player(
                game_id,
                player_id,
                {
                    "type": "game_state",
                    "data": visible,
                },
            )

    @property
    def active_game_count(self) -> int:
        return len(self._connections)


# ---- Global Singleton ----

_ws_manager: WebSocketManager | None = None


def get_ws_manager() -> WebSocketManager:
    """获取全局 WebSocketManager 单例"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


def reset_ws_manager() -> None:
    """重置全局 WebSocketManager（仅用于测试）"""
    global _ws_manager
    _ws_manager = None


# ---- Server Event Builders ----


def event_game_started(game: GameState, viewer_id: str) -> dict[str, Any]:
    """game_started 事件"""
    return {
        "type": "game_started",
        "data": get_visible_state(game, viewer_id),
    }


def event_round_started(
    round_number: int,
    dealer_name: str,
    dealer_index: int = 0,
    pot: int = 0,
    current_bet: int = 0,
    max_turns: int = 10,
) -> dict[str, Any]:
    """round_started 事件"""
    return {
        "type": "round_started",
        "data": {
            "round_number": round_number,
            "dealer": dealer_name,
            "dealer_index": dealer_index,
            "pot": pot,
            "current_bet": current_bet,
            "max_turns": max_turns,
        },
    }


def event_cards_dealt(cards: list[dict] | None) -> dict[str, Any]:
    """cards_dealt 事件（发送给单个玩家的手牌）"""
    return {
        "type": "cards_dealt",
        "data": {"your_cards": cards},
    }


def event_turn_changed(
    current_player_name: str,
    current_player_id: str,
    available_actions: list[str],
) -> dict[str, Any]:
    """turn_changed 事件"""
    return {
        "type": "turn_changed",
        "data": {
            "current_player": current_player_name,
            "current_player_id": current_player_id,
            "available_actions": available_actions,
        },
    }


def event_player_acted(
    player_id: str,
    player_name: str,
    action: str,
    amount: int = 0,
    compare_result: dict | None = None,
) -> dict[str, Any]:
    """player_acted 事件"""
    return {
        "type": "player_acted",
        "data": {
            "player_id": player_id,
            "player_name": player_name,
            "action": action,
            "amount": amount,
            "compare_result": compare_result,
        },
    }


def event_chat_message(msg: ChatMessage) -> dict[str, Any]:
    """chat_message 事件"""
    return {
        "type": "chat_message",
        "data": {
            "id": msg.id,
            "player_id": msg.player_id,
            "player_name": msg.player_name,
            "message_type": msg.message_type.value,
            "content": msg.content,
            "timestamp": msg.timestamp,
        },
    }


def event_round_ended(round_result: dict) -> dict[str, Any]:
    """round_ended 事件"""
    return {
        "type": "round_ended",
        "data": round_result,
    }


def event_game_ended(game_result: dict) -> dict[str, Any]:
    """game_ended 事件"""
    return {
        "type": "game_ended",
        "data": game_result,
    }


def event_ai_thinking(player_id: str, player_name: str) -> dict[str, Any]:
    """ai_thinking 事件"""
    return {
        "type": "ai_thinking",
        "data": {"player_id": player_id, "player_name": player_name},
    }


def event_ai_reviewing(player_id: str, player_name: str, trigger: str) -> dict[str, Any]:
    """ai_reviewing 事件"""
    return {
        "type": "ai_reviewing",
        "data": {
            "player_id": player_id,
            "player_name": player_name,
            "trigger": trigger,
        },
    }


def event_error(message: str) -> dict[str, Any]:
    """error 事件"""
    return {
        "type": "error",
        "data": {"message": message},
    }


def event_copilot_error(
    message: str, error_code: str = "copilot_subscription_error"
) -> dict[str, Any]:
    """copilot_error 事件 — Copilot 订阅/授权错误

    前端收到此事件后应弹窗提示用户切换账号重新登录。
    """
    return {
        "type": "copilot_error",
        "data": {
            "message": message,
            "error_code": error_code,
        },
    }


# ---- AI Turn Processing ----


async def process_ai_turns(
    game_id: str,
    game: GameState,
    ws_manager: WebSocketManager,
    agent_manager: AgentManager,
    chat_engine: ChatEngine,
) -> None:
    """AI 回合的完整调度循环

    当轮到 AI 玩家行动时，自动处理：
    1. 经验回顾检查（如果有 ExperienceReviewer）
    2. AI 决策（make_decision）
    3. 执行操作（apply_action）
    4. 发言处理（table_talk）
    5. 旁观者反应收集
    6. 推送事件

    循环直到轮到人类玩家或本局结束。
    """
    round_state = game.current_round
    if round_state is None or round_state.phase != GamePhase.BETTING:
        return

    chat_context = ws_manager.get_chat_context(game_id)

    while True:
        round_state = game.current_round
        if round_state is None or round_state.phase != GamePhase.BETTING:
            break

        # 获取当前行动玩家
        current_player = game.players[round_state.current_player_index]

        # 如果是人类玩家，停止循环，等待 WebSocket 消息
        if current_player.player_type == PlayerType.HUMAN:
            # 通知人类玩家轮到他了
            from app.engine.rules import get_available_actions

            available = get_available_actions(
                round_state, current_player, game.players, game.config
            )
            await ws_manager.broadcast(
                game_id,
                event_turn_changed(
                    current_player.name,
                    current_player.id,
                    [a.value for a in available],
                ),
            )
            break

        # AI 玩家回合
        agent = agent_manager.get_agent(game_id, current_player.id)
        if agent is None:
            # Agent 不存在，降级为 fold
            logger.warning(
                "No agent found for AI player %s, auto-folding",
                current_player.name,
            )
            try:
                result = apply_action(game, current_player.id, GameAction.FOLD)
                await _broadcast_action_result(
                    game_id,
                    game,
                    current_player,
                    GameAction.FOLD,
                    result,
                    ws_manager,
                )
                if result.round_ended:
                    await _handle_round_end(game_id, game, result, ws_manager)
                    break
            except GameError:
                break
            continue

        # Step 1: 广播 "AI 正在思考"
        await ws_manager.broadcast(
            game_id,
            event_ai_thinking(current_player.id, current_player.name),
        )

        # Step 2: 经验回顾检查（T3.1 — 如果模块可用）
        await _maybe_experience_review(game_id, game, agent, current_player, ws_manager)

        # Step 3: AI 决策
        chat_msgs_for_prompt = _format_chat_for_agent(chat_context)
        try:
            decision = await agent.make_decision(game, current_player, chat_msgs_for_prompt)
        except LLMCallError as e:
            if e.error_code == "copilot_subscription_error":
                # Copilot 订阅错误 — 广播特殊事件通知前端弹窗
                logger.error(
                    "Copilot subscription error for %s: %s",
                    current_player.name,
                    e,
                )
                await ws_manager.broadcast(
                    game_id,
                    event_copilot_error(str(e), e.error_code),
                )
            else:
                logger.error(
                    "AI decision failed for %s: %s, auto-folding",
                    current_player.name,
                    e,
                )
            decision = None
        except Exception as e:
            logger.error(
                "AI decision failed for %s: %s, auto-folding",
                current_player.name,
                e,
            )
            decision = None

        if decision is None:
            action = GameAction.FOLD
            target_id = None
            table_talk = None
        else:
            action = decision.action
            target_id = decision.target
            table_talk = decision.table_talk

        # Step 4: 执行操作
        try:
            result = apply_action(game, current_player.id, action, target_id)
        except GameError as e:
            logger.error(
                "AI action failed for %s (%s): %s, trying fold",
                current_player.name,
                action.value,
                e,
            )
            try:
                result = apply_action(game, current_player.id, GameAction.FOLD)
                action = GameAction.FOLD
            except GameError:
                logger.error("Even fold failed for %s, breaking", current_player.name)
                break

        # Step 5: 持久化思考记录（T4.4）
        if decision is not None and decision.thought is not None:
            thought_record = ThoughtRecord(
                agent_id=current_player.id,
                round_number=round_state.round_number if round_state else 0,
                turn_number=len(round_state.actions) if round_state else 0,
                hand_evaluation=decision.thought.hand_evaluation,
                opponent_analysis=decision.thought.opponent_analysis,
                risk_assessment=decision.thought.risk_assessment,
                chat_analysis=decision.thought.chat_analysis or None,
                reasoning=decision.thought.reasoning,
                confidence=decision.thought.confidence,
                emotion=decision.thought.emotion,
                decision=action,
                decision_target=target_id,
                table_talk=table_talk,
                raw_response=decision.raw_response,
            )
            try:
                db = await _get_db_session()
                try:
                    await persist_thought_record(db, game_id, thought_record)
                    await db.commit()
                finally:
                    await db.close()
            except Exception as e:
                logger.warning("Failed to persist thought record: %s", e)

        # Step 6: 广播操作结果
        await _broadcast_action_result(game_id, game, current_player, action, result, ws_manager)

        # Step 7: 处理行动发言（table_talk）
        if table_talk:
            talk_msg = ChatMessage(
                game_id=game_id,
                round_number=round_state.round_number if round_state else 0,
                player_id=current_player.id,
                player_name=current_player.name,
                message_type=ChatMessageType.ACTION_TALK,
                content=table_talk,
            )
            chat_context.add_message(talk_msg)
            await ws_manager.broadcast(game_id, event_chat_message(talk_msg))
            # 持久化聊天消息（T4.4）
            try:
                db = await _get_db_session()
                try:
                    await persist_chat_message(db, talk_msg)
                    await db.commit()
                finally:
                    await db.close()
            except Exception as e:
                logger.warning("Failed to persist chat message: %s", e)

        # Step 8: 检查是否本局结束（在旁观反应之前检查，避免对已结束的局收集反应）
        if result.round_ended:
            await _handle_round_end(game_id, game, result, ws_manager)
            break

        # Step 9: 旁观者反应（仅在局未结束时收集）
        await _collect_and_broadcast_bystander_reactions(
            game_id=game_id,
            game=game,
            actor=current_player,
            action=action,
            result=result,
            agent_manager=agent_manager,
            chat_engine=chat_engine,
            chat_context=chat_context,
            ws_manager=ws_manager,
        )

        # 小延迟让前端动画有时间播放
        await asyncio.sleep(0.5)


async def handle_player_chat(
    game_id: str,
    game: GameState,
    player_id: str,
    content: str,
    ws_manager: WebSocketManager,
    agent_manager: AgentManager,
    chat_engine: ChatEngine,
) -> None:
    """处理人类玩家发送的聊天消息

    流程：
    1. 创建 ChatMessage 并广播
    2. 创建 must_respond 触发事件
    3. 收集 AI 旁观者反应
    4. 广播 AI 回应
    """
    player = game.get_player_by_id(player_id)
    if player is None:
        return

    round_number = 0
    if game.current_round:
        round_number = game.current_round.round_number

    # 创建并广播玩家消息
    player_msg = ChatMessage(
        game_id=game_id,
        round_number=round_number,
        player_id=player_id,
        player_name=player.name,
        message_type=ChatMessageType.PLAYER_MESSAGE,
        content=content,
    )
    chat_context = ws_manager.get_chat_context(game_id)
    chat_context.add_message(player_msg)
    await ws_manager.broadcast(game_id, event_chat_message(player_msg))

    # 持久化玩家聊天消息（T4.4）
    try:
        db = await _get_db_session()
        try:
            await persist_chat_message(db, player_msg)
            await db.commit()
        finally:
            await db.close()
    except Exception as e:
        logger.warning("Failed to persist player chat message: %s", e)

    # 创建触发事件并收集 AI 反应
    trigger = create_player_message_event(player_id, player.name, content)

    # 获取所有活跃的 AI Agent 作为旁观者（排除已弃牌的）
    all_agents = agent_manager.get_agents_for_game(game_id)
    bystanders = []
    for a in all_agents:
        p = game.get_player_by_id(a.agent_id)
        if p is not None and p.is_active:
            bystanders.append(a)
    if not bystanders:
        return

    # 构建各 Agent 的状态信息
    agent_states = _build_agent_states(game, bystanders)

    reactions = await chat_engine.collect_bystander_reactions(
        event=trigger,
        bystanders=bystanders,
        chat_context=chat_context,
        agent_states=agent_states,
    )

    # 广播 AI 回应
    for reaction in reactions:
        msg = reaction.to_chat_message(game_id=game_id, round_number=round_number)
        if msg is not None:
            chat_context.add_message(msg)
            await ws_manager.broadcast(game_id, event_chat_message(msg))
            # 持久化 AI 回应消息（T4.4）
            try:
                db = await _get_db_session()
                try:
                    await persist_chat_message(db, msg)
                    await db.commit()
                finally:
                    await db.close()
            except Exception as e:
                logger.warning("Failed to persist AI response chat message: %s", e)
            await asyncio.sleep(0.3)  # 间隔一小段时间，模拟打字


# ---- Internal Helpers ----


async def _broadcast_action_result(
    game_id: str,
    game: GameState,
    player: Player,
    action: GameAction,
    result: ActionResult,
    ws_manager: WebSocketManager,
) -> None:
    """广播操作结果事件 + 更新后的游戏状态"""
    await ws_manager.broadcast(
        game_id,
        event_player_acted(
            player_id=player.id,
            player_name=player.name,
            action=action.value,
            amount=result.amount,
            compare_result=result.compare_result,
        ),
    )
    # 广播更新后的游戏状态（筹码、底池、玩家状态等）
    await ws_manager.broadcast_game_state(game_id, game)


async def _handle_round_end(
    game_id: str,
    game: GameState,
    result: ActionResult,
    ws_manager: WebSocketManager,
) -> None:
    """处理局结束事件"""
    if result.round_result is not None:
        round_result_dict = result.round_result.model_dump(mode="json")
        await ws_manager.broadcast(game_id, event_round_ended(round_result_dict))

    # 广播更新后的游戏状态（含结算后的筹码）
    await ws_manager.broadcast_game_state(game_id, game)

    # 检查游戏是否整体结束
    if game.status == "finished":
        final_standings = [
            {"id": p.id, "name": p.name, "chips": p.chips}
            for p in sorted(game.players, key=lambda p: p.chips, reverse=True)
        ]
        await ws_manager.broadcast(
            game_id,
            event_game_ended({"final_standings": final_standings}),
        )


async def _maybe_experience_review(
    game_id: str,
    game: GameState,
    agent: BaseAgent,
    player: Player,
    ws_manager: WebSocketManager,
) -> None:
    """经验回顾检查（如果 T3.1 ExperienceReviewer 可用）

    目前 T3.1 尚未实现，此函数为占位。
    后续实现后会检查触发条件并执行回顾。
    """
    # TODO: T3.1 实现后补充
    # try:
    #     from app.agents.experience import ExperienceReviewer
    #     reviewer = ExperienceReviewer(agent)
    #     trigger = reviewer.check_trigger(game, ...)
    #     if trigger:
    #         await ws_manager.broadcast(
    #             game_id,
    #             event_ai_reviewing(player.id, player.name, trigger.reason),
    #         )
    #         review = await reviewer.perform_review(trigger, ...)
    #         agent.set_strategy_context(review.strategy_context)
    # except ImportError:
    #     pass
    pass


async def _collect_and_broadcast_bystander_reactions(
    game_id: str,
    game: GameState,
    actor: Player,
    action: GameAction,
    result: ActionResult,
    agent_manager: AgentManager,
    chat_engine: ChatEngine,
    chat_context: ChatContext,
    ws_manager: WebSocketManager,
) -> None:
    """收集并广播旁观者反应"""
    round_state = game.current_round
    current_bet = round_state.current_bet if round_state else 0

    # 构建触发事件
    compare_winner = None
    target_name = None
    if result.compare_result:
        compare_winner = result.compare_result.get("winner_id")
        target_name = result.compare_result.get("loser_name")
        if compare_winner == actor.id:
            target_name = result.compare_result.get("loser_name")
        else:
            target_name = result.compare_result.get("winner_name")

    trigger = create_trigger_event_from_action(
        action=action,
        actor_id=actor.id,
        actor_name=actor.name,
        amount=result.amount,
        current_bet=current_bet,
        target_name=target_name,
        compare_winner=compare_winner,
    )

    # 获取旁观者（排除行动者自己，排除已弃牌的玩家）
    all_agents = agent_manager.get_agents_for_game(game_id)
    bystanders = []
    for a in all_agents:
        if a.agent_id == actor.id:
            continue
        p = game.get_player_by_id(a.agent_id)
        if p is not None and p.is_active:
            bystanders.append(a)
    if not bystanders:
        return

    agent_states = _build_agent_states(game, bystanders)

    reactions = await chat_engine.collect_bystander_reactions(
        event=trigger,
        bystanders=bystanders,
        chat_context=chat_context,
        agent_states=agent_states,
    )

    for reaction in reactions:
        round_number = round_state.round_number if round_state else 0
        msg = reaction.to_chat_message(game_id=game_id, round_number=round_number)
        if msg is not None:
            chat_context.add_message(msg)
            await ws_manager.broadcast(game_id, event_chat_message(msg))
            # 持久化旁观者反应消息（T4.4）
            try:
                db = await _get_db_session()
                try:
                    await persist_chat_message(db, msg)
                    await db.commit()
                finally:
                    await db.close()
            except Exception as e:
                logger.warning("Failed to persist bystander reaction: %s", e)
            await asyncio.sleep(0.2)


def _format_chat_for_agent(chat_context: ChatContext) -> list[dict[str, str]]:
    """将 ChatContext 格式化为 agent.make_decision 需要的格式"""
    result: list[dict[str, str]] = []
    for msg in chat_context.get_recent(10):
        result.append({"sender": msg.player_name, "message": msg.content})
    return result


def _build_agent_states(
    game: GameState,
    agents: list[BaseAgent],
) -> dict[str, dict[str, Any]]:
    """构建各 Agent 的状态信息（用于旁观反应 prompt）"""
    states: dict[str, dict[str, Any]] = {}
    for agent in agents:
        player = game.get_player_by_id(agent.agent_id)
        if player is None:
            continue
        seen_status = "已看牌" if player.has_seen_cards else "未看牌"
        states[agent.agent_id] = {
            "seen_status": seen_status,
            "chips": player.chips,
            "actions_summary": f"筹码 {player.chips}, 本局已下注 {player.total_bet_this_round}",
        }
    return states


# ---- WebSocket Endpoint ----


@router.websocket("/ws/{game_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: str,
    player_id: str | None = None,
):
    """WebSocket 连接端点

    连接方式: ws://localhost:8000/ws/{game_id}?player_id={player_id}

    客户端事件:
    - {"type": "player_action", "data": {"action": "...", "target": "..."}}
    - {"type": "chat_message", "data": {"content": "..."}}
    - {"type": "start_round"}

    服务端事件: 参见 event_* 函数
    """
    # 获取依赖
    ws_manager = get_ws_manager()
    store = get_game_store()
    agent_mgr = get_agent_manager()
    chat_engine = ChatEngine()

    # 验证 player_id
    if not player_id:
        # 尝试从 query params 获取
        player_id = websocket.query_params.get("player_id")

    if not player_id:
        await websocket.close(code=4001, reason="Missing player_id")
        return

    # 验证游戏存在
    game = store.get(game_id)
    if game is None:
        await websocket.close(code=4004, reason=f"Game {game_id} not found")
        return

    # 验证玩家属于该游戏
    player = game.get_player_by_id(player_id)
    if player is None:
        await websocket.close(code=4003, reason=f"Player {player_id} not in game {game_id}")
        return

    # 接受连接
    await ws_manager.connect(game_id, player_id, websocket)

    try:
        # 发送当前游戏状态
        visible = get_visible_state(game, player_id)
        await ws_manager.send_to_player(
            game_id,
            player_id,
            {
                "type": "game_state",
                "data": visible,
            },
        )

        # 如果游戏正在进行且轮到人类玩家
        if game.current_round and game.current_round.phase == GamePhase.BETTING:
            current = game.players[game.current_round.current_player_index]
            if current.id == player_id:
                from app.engine.rules import get_available_actions

                available = get_available_actions(
                    game.current_round, current, game.players, game.config
                )
                await ws_manager.send_to_player(
                    game_id,
                    player_id,
                    event_turn_changed(current.name, current.id, [a.value for a in available]),
                )

        # 消息处理循环
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type", "")

            if event_type == "player_action":
                await _handle_player_action(
                    game_id=game_id,
                    player_id=player_id,
                    data=data.get("data", {}),
                    store=store,
                    ws_manager=ws_manager,
                    agent_mgr=agent_mgr,
                    chat_engine=chat_engine,
                )

            elif event_type == "chat_message":
                msg_data = data.get("data", {})
                content = msg_data.get("content", "").strip()
                if content:
                    game = store.get(game_id)
                    if game:
                        await handle_player_chat(
                            game_id=game_id,
                            game=game,
                            player_id=player_id,
                            content=content,
                            ws_manager=ws_manager,
                            agent_manager=agent_mgr,
                            chat_engine=chat_engine,
                        )

            elif event_type == "start_round":
                await _handle_start_round(
                    game_id=game_id,
                    player_id=player_id,
                    store=store,
                    ws_manager=ws_manager,
                    agent_mgr=agent_mgr,
                    chat_engine=chat_engine,
                )

            else:
                await ws_manager.send_to_player(
                    game_id,
                    player_id,
                    event_error(f"Unknown event type: {event_type}"),
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: game=%s, player=%s", game_id, player_id)
    except Exception as e:
        logger.error(
            "WebSocket error: game=%s, player=%s, error=%s",
            game_id,
            player_id,
            e,
        )
    finally:
        ws_manager.disconnect(game_id, player_id)


# ---- Client Event Handlers ----


async def _handle_player_action(
    game_id: str,
    player_id: str,
    data: dict,
    store: GameStore,
    ws_manager: WebSocketManager,
    agent_mgr: AgentManager,
    chat_engine: ChatEngine,
) -> None:
    """处理玩家操作事件"""
    game = store.get(game_id)
    if game is None:
        await ws_manager.send_to_player(game_id, player_id, event_error("游戏不存在"))
        return

    action_str = data.get("action", "")
    target_id = data.get("target")

    # 解析操作
    try:
        action = GameAction(action_str)
    except ValueError:
        await ws_manager.send_to_player(
            game_id,
            player_id,
            event_error(f"无效操作: {action_str}"),
        )
        return

    # 验证是否轮到该玩家（看牌操作可以在任何时候执行）
    round_state = game.current_round
    if round_state is None:
        await ws_manager.send_to_player(game_id, player_id, event_error("当前没有进行中的局"))
        return

    current_player = game.players[round_state.current_player_index]

    # 看牌操作不需要轮到自己
    if action == GameAction.CHECK_CARDS:
        player = game.get_player_by_id(player_id)
        if player is None:
            return
        if player.status != PlayerStatus.ACTIVE_BLIND:
            await ws_manager.send_to_player(game_id, player_id, event_error("已经看过牌了"))
            return
        # 直接更改玩家状态，不走 apply_action 流程（因为不是当前行动玩家）
        player.status = PlayerStatus.ACTIVE_SEEN
        # 广播看牌事件
        await _broadcast_action_result(
            game_id,
            game,
            player,
            action,
            ActionResult(
                success=True,
                action=action,
                player_id=player_id,
                amount=0,
                message=f"{player.name} 看牌",
            ),
            ws_manager,
        )
        # 如果恰好轮到自己，发送更新后的可用操作
        if current_player.id == player_id:
            from app.engine.rules import get_available_actions

            available = get_available_actions(round_state, player, game.players, game.config)
            await ws_manager.broadcast(
                game_id,
                event_turn_changed(
                    player.name,
                    player.id,
                    [a.value for a in available],
                ),
            )
        return

    if current_player.id != player_id:
        await ws_manager.send_to_player(
            game_id,
            player_id,
            event_error(f"当前轮到 {current_player.name} 行动"),
        )
        return

    # 执行操作
    try:
        result = apply_action(game, player_id, action, target_id)
    except InvalidActionError as e:
        await ws_manager.send_to_player(game_id, player_id, event_error(str(e)))
        return
    except GameError as e:
        await ws_manager.send_to_player(game_id, player_id, event_error(str(e)))
        return

    player = game.get_player_by_id(player_id)
    if player is None:
        return

    # 广播操作结果
    await _broadcast_action_result(game_id, game, player, action, result, ws_manager)

    if result.round_ended:
        await _handle_round_end(game_id, game, result, ws_manager)
        return

    # 启动 AI 回合循环（先发送 turn_changed / ai_thinking，避免 UI 卡顿）
    # 旁观反应在 AI 回合循环内部处理
    await process_ai_turns(
        game_id=game_id,
        game=game,
        ws_manager=ws_manager,
        agent_manager=agent_mgr,
        chat_engine=chat_engine,
    )

    # 收集人类行动的旁观反应（在 turn_changed 之后，不阻塞 UI）
    chat_context = ws_manager.get_chat_context(game_id)
    await _collect_and_broadcast_bystander_reactions(
        game_id=game_id,
        game=game,
        actor=player,
        action=action,
        result=result,
        agent_manager=agent_mgr,
        chat_engine=chat_engine,
        chat_context=chat_context,
        ws_manager=ws_manager,
    )


async def _handle_start_round(
    game_id: str,
    player_id: str,
    store: GameStore,
    ws_manager: WebSocketManager,
    agent_mgr: AgentManager,
    chat_engine: ChatEngine,
) -> None:
    """处理开始新局事件"""
    game = store.get(game_id)
    if game is None:
        await ws_manager.send_to_player(game_id, player_id, event_error("游戏不存在"))
        return

    if game.status == "finished":
        await ws_manager.send_to_player(game_id, player_id, event_error("游戏已结束"))
        return

    # 如果有进行中的局
    if game.current_round is not None and game.current_round.phase == GamePhase.BETTING:
        await ws_manager.send_to_player(game_id, player_id, event_error("当前局正在进行中"))
        return

    # 重置聊天上下文
    chat_context = ws_manager.get_chat_context(game_id)
    chat_context.clear()

    # 开始新一局
    try:
        round_state = start_round(game)
    except GameError as e:
        await ws_manager.send_to_player(game_id, player_id, event_error(str(e)))
        return

    dealer = game.players[round_state.dealer_index]

    # 广播 round_started（包含完整局面信息）
    await ws_manager.broadcast(
        game_id,
        event_round_started(
            round_number=round_state.round_number,
            dealer_name=dealer.name,
            dealer_index=round_state.dealer_index,
            pot=round_state.pot,
            current_bet=round_state.current_bet,
            max_turns=game.config.max_turns,
        ),
    )

    # 广播初始游戏状态（含筹码扣除后的数据）
    await ws_manager.broadcast_game_state(game_id, game)

    # 向每个连接的玩家发送各自的手牌
    connections = ws_manager.get_connections(game_id)
    for pid in connections:
        p = game.get_player_by_id(pid)
        if p and p.hand:
            cards_data = [c.model_dump(mode="json") for c in p.hand]
            await ws_manager.send_to_player(game_id, pid, event_cards_dealt(cards_data))

    # 启动 AI 回合（如果第一个行动者是 AI）
    await process_ai_turns(
        game_id=game_id,
        game=game,
        ws_manager=ws_manager,
        agent_manager=agent_mgr,
        chat_engine=chat_engine,
    )
