"""聊天引擎

负责管理 AI 在牌桌上的聊天行为，包括：
1. 行动发言（Decision 中的 table_talk，在 make_decision 时生成）
2. 旁观插嘴（其他玩家操作后，旁观 AI 可能发表评论）
3. 玩家消息回应（人类玩家发消息时，确保至少一个 AI 回应）

触发规则：
- 关键操作（大幅加注、弃牌、比牌）提高触发概率
- 性格影响基础概率（激进型 talk_frequency=0.8，保守型=0.25）
- 玩家消息 must_respond=True 确保至少一个 AI 回应
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.agents.base_agent import BaseAgent
from app.agents.prompts import render_bystander_react_prompt
from app.models.chat import (
    BystanderReaction,
    ChatContext,
    ChatMessage,
    ChatMessageType,
)
from app.models.game import GameAction

logger = logging.getLogger(__name__)


# ---- 触发事件类型 ----


class TriggerEventType(str, Enum):
    """触发旁观反应的事件类型"""

    RAISE = "raise"  # 加注
    BIG_RAISE = "big_raise"  # 大幅加注（当前注额显著增长）
    FOLD = "fold"  # 弃牌
    COMPARE = "compare"  # 比牌
    COMPARE_WIN = "compare_win"  # 比牌赢
    COMPARE_LOSE = "compare_lose"  # 比牌输
    CHECK_CARDS = "check_cards"  # 看牌
    CALL = "call"  # 跟注
    PLAYER_MESSAGE = "player_message"  # 人类玩家发消息
    ROUND_START = "round_start"  # 新一局开始
    ROUND_END = "round_end"  # 一局结束


@dataclass
class TriggerEvent:
    """触发旁观反应的事件

    Attributes:
        event_type: 事件类型
        actor_id: 触发事件的玩家 ID
        actor_name: 触发事件的玩家名称
        description: 事件的人类可读描述
        details: 额外信息（如下注金额、比牌结果等）
        must_respond: 是否要求至少一个 AI 回应
    """

    event_type: TriggerEventType
    actor_id: str = ""
    actor_name: str = ""
    description: str = ""
    details: dict[str, Any] | None = None
    must_respond: bool = False


# ---- 事件概率配置 ----

# 各事件类型的基础触发概率（在性格 talk_frequency 之前）
EVENT_BASE_PROBABILITIES: dict[TriggerEventType, float] = {
    TriggerEventType.BIG_RAISE: 0.6,  # 大幅加注 - 高概率触发
    TriggerEventType.COMPARE: 0.55,  # 比牌 - 较高概率
    TriggerEventType.COMPARE_WIN: 0.5,  # 比牌赢 - 较高概率
    TriggerEventType.COMPARE_LOSE: 0.5,  # 比牌输 - 较高概率
    TriggerEventType.RAISE: 0.35,  # 普通加注
    TriggerEventType.FOLD: 0.3,  # 弃牌
    TriggerEventType.CHECK_CARDS: 0.15,  # 看牌 - 低概率
    TriggerEventType.CALL: 0.1,  # 跟注 - 低概率
    TriggerEventType.ROUND_START: 0.2,  # 新一局 - 中低概率
    TriggerEventType.ROUND_END: 0.4,  # 一局结束 - 中概率
    TriggerEventType.PLAYER_MESSAGE: 1.0,  # 玩家消息 - 必定处理（由 must_respond 控制）
}


class ChatEngine:
    """聊天引擎

    管理旁观 AI 的反应调度。在游戏流程中，当发生特定事件时，
    ChatEngine 会决定哪些旁观 AI 应该做出反应，并调用 LLM 生成回应。

    Usage:
        engine = ChatEngine()

        # 玩家操作后触发旁观反应
        event = TriggerEvent(
            event_type=TriggerEventType.RAISE,
            actor_id="player-1",
            actor_name="张三",
            description="张三 加注到 40 筹码",
        )
        reactions = await engine.collect_bystander_reactions(
            event=event,
            bystanders=[agent_a, agent_b],
            chat_context=chat_ctx,
        )
    """

    def __init__(self) -> None:
        pass

    def should_respond(
        self,
        trigger_event: TriggerEvent,
        agent: BaseAgent,
    ) -> bool:
        """判断某个旁观 AI 是否应该对事件做出反应

        计算方式：最终概率 = 事件基础概率 * 性格发言频率系数
        然后掷骰子决定是否触发。

        Args:
            trigger_event: 触发事件
            agent: 旁观 AI Agent

        Returns:
            是否应该回应
        """
        # must_respond 的事件总是需要处理（但不一定每个 AI 都回应）
        if trigger_event.must_respond:
            # must_respond 场景下，用较高的基础概率
            base_prob = 0.7
        else:
            base_prob = EVENT_BASE_PROBABILITIES.get(trigger_event.event_type, 0.2)

        # 获取性格的发言频率参数
        behavior = agent.get_behavior_params()
        talk_frequency = behavior.get("talk_frequency", 0.5)

        # 最终概率 = 基础概率 * 性格系数
        # 性格系数范围 [0.3, 1.7]，使低 talk_frequency 的 AI 仍有小概率说话
        personality_factor = 0.3 + talk_frequency * 1.4
        final_prob = min(1.0, base_prob * personality_factor)

        # 不要让自己对自己的行动做出旁观反应
        if trigger_event.actor_id == agent.agent_id:
            return False

        roll = random.random()
        should = roll < final_prob
        logger.debug(
            "[ChatEngine] should_respond: agent=%s, event=%s, "
            "base=%.2f, talk_freq=%.2f, factor=%.2f, final=%.2f, roll=%.2f -> %s",
            agent.name,
            trigger_event.event_type.value,
            base_prob,
            talk_frequency,
            personality_factor,
            final_prob,
            roll,
            should,
        )
        return should

    async def maybe_react_as_bystander(
        self,
        trigger_event: TriggerEvent,
        agent: BaseAgent,
        chat_context: ChatContext,
        agent_state: dict[str, Any] | None = None,
        must_respond: bool = False,
    ) -> BystanderReaction | None:
        """让一个旁观 AI 对事件做出反应

        先通过 should_respond 判断是否回应，
        如果 must_respond=True 则跳过概率判断直接生成回应。
        然后调用 LLM 生成反应内容。

        Args:
            trigger_event: 触发事件
            agent: 旁观 AI Agent
            chat_context: 当前聊天上下文
            agent_state: Agent 当前状态信息（看牌状态、筹码等）
            must_respond: 是否强制回应（跳过概率判断）

        Returns:
            BystanderReaction 实例，或 None（选择不回应时）
        """
        # 决定是否回应
        if not must_respond and not self.should_respond(trigger_event, agent):
            return None

        # 构建状态信息
        state = agent_state or {}
        seen_status = state.get("seen_status", "未看牌")
        your_chips = state.get("chips", 0)
        your_actions = state.get("actions_summary", "暂无操作")

        # 构建 bystander prompt
        prompt = render_bystander_react_prompt(
            trigger_event_description=trigger_event.description,
            recent_chat=chat_context.format_for_prompt(count=8),
            seen_status=seen_status,
            your_chips=your_chips,
            your_actions_so_far=your_actions,
        )

        system_prompt = agent.build_system_prompt()

        try:
            raw_response = await agent.call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,  # 聊天场景用稍高的温度
            )
            reaction = self._parse_bystander_response(
                raw_response=raw_response,
                agent=agent,
                trigger_event=trigger_event,
            )
            return reaction

        except Exception as e:
            logger.warning(
                "[ChatEngine] Failed to get bystander reaction from %s: %s",
                agent.name,
                str(e),
            )
            # LLM 调用失败时，如果是 must_respond 则返回一个默认反应
            if must_respond:
                return BystanderReaction(
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    should_respond=True,
                    message=_get_fallback_reaction(trigger_event, agent),
                    inner_thought="（LLM 调用失败，使用默认回应）",
                    trigger_event=trigger_event.description,
                )
            return None

    async def collect_bystander_reactions(
        self,
        event: TriggerEvent,
        bystanders: list[BaseAgent],
        chat_context: ChatContext,
        agent_states: dict[str, dict[str, Any]] | None = None,
    ) -> list[BystanderReaction]:
        """收集所有旁观 AI 对某事件的反应

        遍历所有旁观 AI，根据概率决定谁回应，
        并确保 must_respond 事件至少有一个回应。

        Args:
            event: 触发事件
            bystanders: 旁观 AI Agent 列表（不含事件发起者）
            chat_context: 聊天上下文
            agent_states: 各 Agent 的状态信息 {agent_id: state_dict}

        Returns:
            所有选择回应的 BystanderReaction 列表
        """
        if not bystanders:
            return []

        states = agent_states or {}
        reactions: list[BystanderReaction] = []

        # 先让所有 AI 各自判断是否回应
        for agent in bystanders:
            # 跳过事件发起者
            if agent.agent_id == event.actor_id:
                continue

            state = states.get(agent.agent_id)
            reaction = await self.maybe_react_as_bystander(
                trigger_event=event,
                agent=agent,
                chat_context=chat_context,
                agent_state=state,
            )
            if reaction is not None and reaction.should_respond:
                reactions.append(reaction)

        # must_respond 保证：如果需要至少一个回应但没有任何 AI 回应
        if event.must_respond and not reactions and bystanders:
            # 选一个最可能回应的 AI（talk_frequency 最高的）
            best_candidate = self._pick_most_talkative(bystanders, event.actor_id)
            if best_candidate:
                state = states.get(best_candidate.agent_id)
                reaction = await self.maybe_react_as_bystander(
                    trigger_event=event,
                    agent=best_candidate,
                    chat_context=chat_context,
                    agent_state=state,
                    must_respond=True,
                )
                if reaction is not None:
                    reactions.append(reaction)

        return reactions

    def calculate_response_probability(
        self,
        trigger_event: TriggerEvent,
        agent: BaseAgent,
    ) -> float:
        """计算某个 AI 对事件的回应概率（暴露给测试用）

        Args:
            trigger_event: 触发事件
            agent: AI Agent

        Returns:
            最终回应概率 [0, 1]
        """
        if trigger_event.actor_id == agent.agent_id:
            return 0.0

        if trigger_event.must_respond:
            base_prob = 0.7
        else:
            base_prob = EVENT_BASE_PROBABILITIES.get(trigger_event.event_type, 0.2)

        behavior = agent.get_behavior_params()
        talk_frequency = behavior.get("talk_frequency", 0.5)
        personality_factor = 0.3 + talk_frequency * 1.4
        return min(1.0, base_prob * personality_factor)

    # ---- 内部方法 ----

    def _parse_bystander_response(
        self,
        raw_response: str,
        agent: BaseAgent,
        trigger_event: TriggerEvent,
    ) -> BystanderReaction:
        """解析 LLM 的旁观反应响应

        与 BaseAgent._try_parse_json 类似的多层容错逻辑。
        """
        parsed = agent._try_parse_json(raw_response)

        if parsed is not None:
            should_respond = bool(parsed.get("should_respond", False))
            message = str(parsed.get("message", "")).strip()
            inner_thought = str(parsed.get("inner_thought", "")).strip()

            # 如果 should_respond 为 true 但 message 为空，改为不回应
            if should_respond and not message:
                should_respond = False

            return BystanderReaction(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                should_respond=should_respond,
                message=message,
                inner_thought=inner_thought,
                trigger_event=trigger_event.description,
            )

        # JSON 解析失败，尝试从文本中提取
        logger.warning(
            "[ChatEngine] Failed to parse bystander JSON from %s, extracting from text",
            agent.name,
        )
        return self._extract_reaction_from_text(raw_response, agent, trigger_event)

    def _extract_reaction_from_text(
        self,
        text: str,
        agent: BaseAgent,
        trigger_event: TriggerEvent,
    ) -> BystanderReaction:
        """从非 JSON 文本中提取旁观反应"""
        # 如果文本较短且不像是拒绝回应，直接用作回应内容
        text = text.strip()
        if len(text) > 0 and len(text) <= 200:
            # 检查是否是拒绝类文本
            reject_keywords = ["不回应", "沉默", "不说话", "不做回应", "选择沉默"]
            if any(kw in text for kw in reject_keywords):
                return BystanderReaction(
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    should_respond=False,
                    inner_thought=text,
                    trigger_event=trigger_event.description,
                )
            return BystanderReaction(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                should_respond=True,
                message=text[:150],
                trigger_event=trigger_event.description,
            )

        # 长文本 or 空文本，当作不回应
        return BystanderReaction(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            should_respond=False,
            inner_thought=text[:200] if text else "",
            trigger_event=trigger_event.description,
        )

    @staticmethod
    def _pick_most_talkative(
        agents: list[BaseAgent],
        exclude_id: str = "",
    ) -> BaseAgent | None:
        """选出最健谈的 AI（talk_frequency 最高的，排除指定 ID）"""
        candidates = [a for a in agents if a.agent_id != exclude_id]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda a: a.get_behavior_params().get("talk_frequency", 0.5),
        )


# ---- 辅助函数 ----


def create_trigger_event_from_action(
    action: GameAction,
    actor_id: str,
    actor_name: str,
    amount: int | None = None,
    current_bet: int | None = None,
    target_name: str | None = None,
    compare_winner: str | None = None,
) -> TriggerEvent:
    """根据游戏操作创建触发事件

    工厂函数，将 GameAction 转换为 TriggerEvent。

    Args:
        action: 游戏操作
        actor_id: 操作者 ID
        actor_name: 操作者名称
        amount: 下注金额
        current_bet: 当前注额
        target_name: 比牌对象名称
        compare_winner: 比牌赢家 ID（仅比牌时有值）

    Returns:
        对应的 TriggerEvent
    """
    if action == GameAction.RAISE:
        # 判断是否为大幅加注（金额 > 当前注额的 2 倍）
        is_big = amount is not None and current_bet is not None and amount > current_bet * 2
        event_type = TriggerEventType.BIG_RAISE if is_big else TriggerEventType.RAISE
        desc = f"{actor_name} 加注到 {amount} 筹码" if amount else f"{actor_name} 加注"
        return TriggerEvent(
            event_type=event_type,
            actor_id=actor_id,
            actor_name=actor_name,
            description=desc,
            details={"amount": amount, "current_bet": current_bet},
        )

    if action == GameAction.FOLD:
        return TriggerEvent(
            event_type=TriggerEventType.FOLD,
            actor_id=actor_id,
            actor_name=actor_name,
            description=f"{actor_name} 弃牌了",
        )

    if action == GameAction.COMPARE:
        if compare_winner:
            is_winner = compare_winner == actor_id
            event_type = (
                TriggerEventType.COMPARE_WIN if is_winner else TriggerEventType.COMPARE_LOSE
            )
            result_text = "赢了" if is_winner else "输了"
            desc = f"{actor_name} 与 {target_name or '对手'} 比牌，{result_text}"
        else:
            event_type = TriggerEventType.COMPARE
            desc = f"{actor_name} 发起与 {target_name or '对手'} 的比牌"
        return TriggerEvent(
            event_type=event_type,
            actor_id=actor_id,
            actor_name=actor_name,
            description=desc,
            details={"target_name": target_name, "winner": compare_winner},
        )

    if action == GameAction.CHECK_CARDS:
        return TriggerEvent(
            event_type=TriggerEventType.CHECK_CARDS,
            actor_id=actor_id,
            actor_name=actor_name,
            description=f"{actor_name} 看了自己的牌",
        )

    if action == GameAction.CALL:
        desc = f"{actor_name} 跟注 {amount} 筹码" if amount else f"{actor_name} 跟注"
        return TriggerEvent(
            event_type=TriggerEventType.CALL,
            actor_id=actor_id,
            actor_name=actor_name,
            description=desc,
            details={"amount": amount},
        )

    # 未知操作，用通用描述
    return TriggerEvent(
        event_type=TriggerEventType.CALL,
        actor_id=actor_id,
        actor_name=actor_name,
        description=f"{actor_name} 执行了操作 {action.value}",
    )


def create_player_message_event(
    player_id: str,
    player_name: str,
    message: str,
) -> TriggerEvent:
    """创建玩家消息触发事件

    玩家发消息时使用，must_respond=True 确保至少一个 AI 回应。

    Args:
        player_id: 玩家 ID
        player_name: 玩家名称
        message: 消息内容

    Returns:
        must_respond=True 的 TriggerEvent
    """
    return TriggerEvent(
        event_type=TriggerEventType.PLAYER_MESSAGE,
        actor_id=player_id,
        actor_name=player_name,
        description=f'{player_name} 说: "{message}"',
        must_respond=True,
    )


def _get_fallback_reaction(
    trigger_event: TriggerEvent,
    agent: BaseAgent,
) -> str:
    """获取降级反应文本（LLM 调用失败时使用）

    根据事件类型和性格返回一个简短的默认回应。
    """
    personality = agent.personality

    # 根据事件类型和性格生成默认回应
    fallback_responses: dict[str, list[str]] = {
        "aggressive": [
            "哼，有意思。",
            "来吧，谁怕谁。",
            "就这？",
        ],
        "conservative": [
            "嗯...",
            "我再看看。",
            "有意思。",
        ],
        "analytical": [
            "有趣的选择。",
            "值得关注。",
            "数据在变化。",
        ],
        "intuitive": [
            "感觉有什么要发生了。",
            "直觉告诉我...",
            "嗯，有点意思。",
        ],
        "bluffer": [
            "哦？真的吗？",
            "呵呵，好戏开场了。",
            "这可不一定哦。",
        ],
    }

    responses = fallback_responses.get(personality, ["..."])
    return random.choice(responses)
