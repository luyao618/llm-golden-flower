"""聊天数据模型

定义聊天引擎使用的核心数据类型：
- ChatMessageType: 聊天消息类型枚举
- ChatMessage: 单条聊天消息
- ChatContext: 聊天上下文（近期消息列表）
- BystanderReaction: 旁观者反应结果
"""

from __future__ import annotations

import time
import uuid
from enum import Enum

from pydantic import BaseModel, Field


class ChatMessageType(str, Enum):
    """聊天消息类型

    区分不同来源和用途的消息，前端可据此展示不同样式。
    """

    ACTION_TALK = "action_talk"  # 行动时附带的发言
    BYSTANDER_REACT = "bystander_react"  # 旁观者插嘴
    PLAYER_MESSAGE = "player_message"  # 人类玩家主动发送的消息
    SYSTEM_MESSAGE = "system_message"  # 系统消息（如 "XX 弃牌了"）


class ChatMessage(BaseModel):
    """单条聊天消息

    Attributes:
        id: 消息唯一标识
        game_id: 所属游戏 ID
        round_number: 所属局号
        player_id: 发送者 ID（系统消息为 "system"）
        player_name: 发送者名称
        message_type: 消息类型
        content: 消息文本内容
        timestamp: 消息时间戳
        trigger_event: 触发此消息的事件描述（旁观反应时记录）
        inner_thought: 发送者的内心想法（仅用于记录，不公开展示）
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    game_id: str = ""
    round_number: int = 0
    player_id: str = ""
    player_name: str = ""
    message_type: ChatMessageType = ChatMessageType.ACTION_TALK
    content: str = ""
    timestamp: float = Field(default_factory=time.time)
    trigger_event: str = ""
    inner_thought: str = ""


class ChatContext(BaseModel):
    """聊天上下文

    保存当前局的近期聊天消息，用于构建 prompt。

    Attributes:
        messages: 近期聊天消息列表（按时间排序）
        max_messages: 上下文窗口中保留的最大消息数
    """

    messages: list[ChatMessage] = Field(default_factory=list)
    max_messages: int = 20

    def add_message(self, message: ChatMessage) -> None:
        """添加一条消息，超出窗口时移除最旧的"""
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def get_recent(self, count: int | None = None) -> list[ChatMessage]:
        """获取最近 N 条消息

        Args:
            count: 返回的消息数量，None 则返回全部

        Returns:
            消息列表（按时间排序）
        """
        if count is None:
            return list(self.messages)
        return self.messages[-count:]

    def format_for_prompt(self, count: int = 10) -> str:
        """将近期聊天格式化为 prompt 文本

        Args:
            count: 包含的最近消息数

        Returns:
            格式化的聊天文本，无消息时返回 "（暂无聊天记录）"
        """
        recent = self.get_recent(count)
        if not recent:
            return "（暂无聊天记录）"

        lines: list[str] = []
        for msg in recent:
            type_label = _message_type_label(msg.message_type)
            lines.append(f"[{type_label}] {msg.player_name}: {msg.content}")
        return "\n".join(lines)

    def clear(self) -> None:
        """清空聊天上下文"""
        self.messages.clear()


class BystanderReaction(BaseModel):
    """旁观者反应结果

    由 ChatEngine.maybe_react_as_bystander() 返回，
    表示一个旁观 AI 对某事件的反应。

    Attributes:
        agent_id: 反应者 Agent ID
        agent_name: 反应者名称
        should_respond: 是否选择回应
        message: 回应内容（should_respond=True 时有值）
        inner_thought: 内心真实想法（不公开）
        trigger_event: 触发反应的事件描述
    """

    agent_id: str = ""
    agent_name: str = ""
    should_respond: bool = False
    message: str = ""
    inner_thought: str = ""
    trigger_event: str = ""

    def to_chat_message(
        self,
        game_id: str = "",
        round_number: int = 0,
    ) -> ChatMessage | None:
        """将旁观反应转换为 ChatMessage

        仅当 should_respond=True 且 message 非空时生成消息。

        Returns:
            ChatMessage 实例，或 None（不需要回应时）
        """
        if not self.should_respond or not self.message:
            return None

        return ChatMessage(
            game_id=game_id,
            round_number=round_number,
            player_id=self.agent_id,
            player_name=self.agent_name,
            message_type=ChatMessageType.BYSTANDER_REACT,
            content=self.message,
            trigger_event=self.trigger_event,
            inner_thought=self.inner_thought,
        )


# ---- 辅助函数 ----


def _message_type_label(message_type: ChatMessageType) -> str:
    """获取消息类型的中文标签（用于 prompt 展示）"""
    labels = {
        ChatMessageType.ACTION_TALK: "行动发言",
        ChatMessageType.BYSTANDER_REACT: "插嘴",
        ChatMessageType.PLAYER_MESSAGE: "玩家消息",
        ChatMessageType.SYSTEM_MESSAGE: "系统",
    }
    return labels.get(message_type, "消息")
