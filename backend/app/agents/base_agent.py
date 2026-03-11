"""AI Agent 基类

提供 LLM 调用封装、System Prompt 构建、决策响应解析等核心能力。
BaseAgent 是所有 AI 玩家的基础，后续的性格系统、聊天引擎等在此基础上扩展。
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import litellm

from app.config import AI_MODELS, get_settings
from app.models.game import GameAction

logger = logging.getLogger(__name__)


# ---- 数据结构 ----


@dataclass
class Decision:
    """AI 的决策结果

    Attributes:
        action: 选择的游戏操作
        target: 比牌对象 ID（仅比牌时有值）
        table_talk: 操作时附带的发言（None 表示沉默）
        thought: 结构化的思考记录
        raw_response: LLM 原始响应文本
    """

    action: GameAction
    target: str | None = None
    table_talk: str | None = None
    thought: ThoughtData | None = None
    raw_response: str = ""


@dataclass
class ThoughtData:
    """AI 单次决策的思考数据（从 LLM 响应中解析）

    Attributes:
        hand_evaluation: 手牌评估
        opponent_analysis: 对手分析
        chat_analysis: 对聊天内容的分析
        risk_assessment: 风险评估
        reasoning: 决策理由
        confidence: 信心值 0-1
        emotion: 情绪标签
    """

    hand_evaluation: str = ""
    opponent_analysis: str = ""
    chat_analysis: str = ""
    risk_assessment: str = ""
    reasoning: str = ""
    confidence: float = 0.5
    emotion: str = "平静"


@dataclass
class AgentMemory:
    """Agent 的上下文记忆

    存储历史行动、对手画像、经验回顾结论等信息，
    用于构建决策 prompt 的上下文。
    """

    # 经验回顾得出的策略摘要（注入后续决策）
    strategy_context: str = ""
    # 对各对手的行为模式记录
    opponent_profiles: dict[str, str] = field(default_factory=dict)
    # 历史决策记录（用于叙事生成）
    round_thoughts: dict[int, list[ThoughtData]] = field(default_factory=dict)


# ---- LLM 响应的 JSON Schema ----

DECISION_OUTPUT_SCHEMA = """\
{
    "action": "fold | call | raise | check_cards | compare",
    "target": "比牌对象的玩家ID（仅当 action 为 compare 时需要，否则为 null）",
    "table_talk": "你在操作时说的话（可以为 null 表示沉默）",
    "thought": {
        "hand_evaluation": "对自己手牌的评估",
        "opponent_analysis": "对对手行为的分析",
        "chat_analysis": "对近期牌桌聊天的分析（可选）",
        "risk_assessment": "风险评估",
        "reasoning": "最终决策理由",
        "confidence": 0.0到1.0之间的数字,
        "emotion": "当前情绪标签，如：紧张、自信、忐忑、兴奋、沮丧、平静"
    }
}"""

# 简化版的炸金花规则摘要，注入 system prompt
RULES_SUMMARY = """\
炸金花（三张牌扑克）规则：
1. 每人发 3 张牌，牌型从大到小：豹子 > 同花顺 > 同花 > 顺子 > 对子 > 散牌
2. 特殊规则：A-2-3 是最小的顺子
3. 开局每人交底注，然后从庄家下家开始轮流行动
4. 可用操作：
   - 看牌：查看自己的手牌（暗注变明注，下注费用翻倍）
   - 跟注：跟上当前注额（暗注 1 倍，明注 2 倍）
   - 加注：加倍当前注额（暗注 2 倍，明注 4 倍）
   - 弃牌：放弃本局
   - 比牌：与另一个玩家比牌（只有已看牌的玩家才能发起），输者出局
5. 达到最大轮数时，剩余玩家强制比牌
6. 最后留在牌桌的玩家赢得底池"""


class BaseAgent:
    """AI Agent 基类

    封装 LLM 调用、prompt 构建、响应解析等核心逻辑。
    每个 BaseAgent 实例对应游戏中的一个 AI 玩家。

    Attributes:
        agent_id: Agent 唯一标识（对应 Player.id）
        name: Agent 显示名称
        model_id: 使用的 LLM 模型标识（对应 AI_MODELS 中的 key）
        personality: 性格类型标识
        personality_description: 性格描述文本（用于 system prompt）
        memory: Agent 的上下文记忆
    """

    def __init__(
        self,
        agent_id: str | None = None,
        name: str = "AI Player",
        model_id: str = "openai-gpt4o-mini",
        personality: str = "analytical",
        personality_description: str = "",
    ) -> None:
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name
        self.model_id = model_id
        self.personality = personality
        self.personality_description = personality_description or f"{personality}型玩家"
        self.memory = AgentMemory()

        # 验证 model_id 有效
        if model_id not in AI_MODELS:
            logger.warning("Unknown model_id '%s', falling back to 'openai-gpt4o-mini'", model_id)
            self.model_id = "openai-gpt4o-mini"

    # ---- LLM 调用 ----

    async def call_llm(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> str:
        """封装 LiteLLM 调用，含重试、超时、错误处理

        Args:
            messages: OpenAI 格式的消息列表
            temperature: 生成温度，None 则使用默认配置
            response_format: 响应格式要求（如 {"type": "json_object"}）

        Returns:
            LLM 响应的文本内容

        Raises:
            LLMCallError: LLM 调用失败且重试耗尽时抛出
        """
        settings = get_settings()
        model_config = AI_MODELS[self.model_id]
        model_name = model_config["model"]

        # 设置 API keys（LiteLLM 会根据模型自动选择对应的 key）
        _configure_api_keys(settings)

        temp = temperature if temperature is not None else settings.llm_temperature
        fmt = response_format or {"type": "json_object"}

        last_error: Exception | None = None

        for attempt in range(1, settings.llm_max_retries + 1):
            try:
                logger.info(
                    "[%s] LLM call attempt %d/%d, model=%s",
                    self.name,
                    attempt,
                    settings.llm_max_retries,
                    model_name,
                )

                response = await litellm.acompletion(
                    model=model_name,
                    messages=messages,
                    temperature=temp,
                    response_format=fmt,
                    timeout=settings.llm_timeout,
                )

                content = response.choices[0].message.content
                if content is None:
                    raise LLMCallError("LLM returned empty content")

                logger.info("[%s] LLM call succeeded on attempt %d", self.name, attempt)
                return content

            except Exception as e:
                last_error = e
                logger.warning("[%s] LLM call attempt %d failed: %s", self.name, attempt, str(e))
                if attempt < settings.llm_max_retries:
                    # 简单的指数退避
                    import asyncio

                    wait_time = 2**attempt
                    logger.info("[%s] Retrying in %ds...", self.name, wait_time)
                    await asyncio.sleep(wait_time)

        raise LLMCallError(
            f"LLM call failed after {settings.llm_max_retries} retries: {last_error}"
        )

    # ---- Prompt 构建 ----

    def build_system_prompt(self) -> str:
        """构建 system prompt

        包含：角色身份 + 炸金花规则 + 决策原则 + 牌桌交流指导 + 输出格式。
        性格描述会注入到角色身份部分。

        Returns:
            完整的 system prompt 文本
        """
        return f"""\
你是一个正在玩炸金花（三张牌扑克）的玩家。

## 你的身份
- 名字: {self.name}
- 性格: {self.personality_description}

## 炸金花规则摘要
{RULES_SUMMARY}

## 你的决策原则
- 根据你的性格特征做出符合角色的决策
- 仔细分析对手的行为模式
- 权衡风险与收益
- 记录你的真实想法

## 牌桌交流
- 你可以在做出操作时说一句话（也可以选择沉默）
- 你的发言应该符合你的性格特征
- 你可以利用言语来施压、虚张声势、试探对手、回应挑衅
- 注意：你说的话对手能看到，不要泄露自己的真实策略
- 牌桌上的对话也是博弈的一部分，对手的话可能是真话也可能是烟雾弹

## 输出格式
你必须以 JSON 格式输出，包含以下字段:
{DECISION_OUTPUT_SCHEMA}"""

    # ---- 响应解析 ----

    def parse_decision_response(
        self,
        raw_response: str,
        available_actions: list[GameAction] | None = None,
    ) -> Decision:
        """解析 LLM 响应为结构化的 Decision

        具备多层容错：
        1. 尝试直接 JSON 解析
        2. 尝试从文本中提取 JSON 块
        3. 尝试从文本中提取关键信息
        4. 降级为最安全的合法操作

        Args:
            raw_response: LLM 原始响应文本
            available_actions: 当前可用的合法操作列表，用于验证

        Returns:
            解析后的 Decision 对象
        """
        if available_actions is None:
            available_actions = list(GameAction)

        parsed = self._try_parse_json(raw_response)

        if parsed is not None:
            decision = self._extract_decision(parsed, raw_response, available_actions)
        else:
            # JSON 解析失败，尝试从文本中提取
            logger.warning("[%s] Failed to parse JSON, attempting text extraction", self.name)
            decision = self._extract_from_text(raw_response, available_actions)

        # 最终验证：确保 action 合法
        if decision.action not in available_actions:
            logger.warning(
                "[%s] Action '%s' not in available actions %s, falling back",
                self.name,
                decision.action.value,
                [a.value for a in available_actions],
            )
            decision.action = self._get_fallback_action(available_actions)
            decision.target = None

        decision.raw_response = raw_response
        return decision

    # ---- 策略上下文 ----

    def get_strategy_context(self) -> str:
        """获取经验回顾生成的策略上下文

        Returns:
            策略摘要文本，空字符串表示暂无策略调整
        """
        return self.memory.strategy_context

    def set_strategy_context(self, context: str) -> None:
        """设置经验回顾生成的策略上下文"""
        self.memory.strategy_context = context

    def record_thought(self, round_number: int, thought: ThoughtData) -> None:
        """记录某一轮的思考数据"""
        if round_number not in self.memory.round_thoughts:
            self.memory.round_thoughts[round_number] = []
        self.memory.round_thoughts[round_number].append(thought)

    def get_round_thoughts(self, round_number: int) -> list[ThoughtData]:
        """获取某一轮的所有思考记录"""
        return self.memory.round_thoughts.get(round_number, [])

    def reset_for_new_game(self) -> None:
        """重置 Agent 状态，准备新游戏"""
        self.memory = AgentMemory()

    # ---- 内部方法 ----

    def _try_parse_json(self, text: str) -> dict | None:
        """尝试从文本中解析 JSON

        先直接解析，失败则尝试提取 ```json``` 代码块或花括号包裹的内容。
        """
        # 直接解析
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        # 尝试提取 markdown 代码块中的 JSON
        json_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
        match = re.search(json_block_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, TypeError):
                pass

        # 尝试提取最外层花括号包裹的内容
        brace_pattern = r"\{[\s\S]*\}"
        match = re.search(brace_pattern, text)
        if match:
            try:
                return json.loads(match.group(0))
            except (json.JSONDecodeError, TypeError):
                pass

        return None

    def _extract_decision(
        self,
        parsed: dict,
        raw_response: str,
        available_actions: list[GameAction],
    ) -> Decision:
        """从已解析的 JSON dict 中提取 Decision"""
        # 提取 action
        action_str = str(parsed.get("action", "")).lower().strip()
        action = self._parse_action(action_str, available_actions)

        # 提取 target
        target = parsed.get("target")
        if target is not None:
            target = str(target).strip()
            if target.lower() in ("null", "none", ""):
                target = None

        # 提取 table_talk
        table_talk = parsed.get("table_talk")
        if table_talk is not None:
            table_talk = str(table_talk).strip()
            if table_talk.lower() in ("null", "none", ""):
                table_talk = None

        # 提取 thought
        thought_data = parsed.get("thought", {})
        thought = self._parse_thought(thought_data)

        return Decision(
            action=action,
            target=target,
            table_talk=table_talk,
            thought=thought,
            raw_response=raw_response,
        )

    def _parse_action(self, action_str: str, available_actions: list[GameAction]) -> GameAction:
        """将字符串解析为 GameAction，含容错"""
        # 直接匹配
        for action in GameAction:
            if action.value == action_str:
                return action

        # 模糊匹配（处理中文或变体）
        action_aliases: dict[str, GameAction] = {
            "fold": GameAction.FOLD,
            "弃牌": GameAction.FOLD,
            "call": GameAction.CALL,
            "跟注": GameAction.CALL,
            "raise": GameAction.RAISE,
            "加注": GameAction.RAISE,
            "check_cards": GameAction.CHECK_CARDS,
            "check": GameAction.CHECK_CARDS,
            "看牌": GameAction.CHECK_CARDS,
            "compare": GameAction.COMPARE,
            "比牌": GameAction.COMPARE,
        }

        matched = action_aliases.get(action_str)
        if matched:
            return matched

        # 部分匹配
        for alias, act in action_aliases.items():
            if alias in action_str or action_str in alias:
                return act

        # 无法匹配，降级
        logger.warning("[%s] Cannot parse action '%s', using fallback", self.name, action_str)
        return self._get_fallback_action(available_actions)

    def _parse_thought(self, thought_data: Any) -> ThoughtData:
        """从 dict 中提取 ThoughtData，含容错"""
        if not isinstance(thought_data, dict):
            return ThoughtData()

        confidence = thought_data.get("confidence", 0.5)
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.5

        return ThoughtData(
            hand_evaluation=str(thought_data.get("hand_evaluation", "")),
            opponent_analysis=str(thought_data.get("opponent_analysis", "")),
            chat_analysis=str(thought_data.get("chat_analysis", "")),
            risk_assessment=str(thought_data.get("risk_assessment", "")),
            reasoning=str(thought_data.get("reasoning", "")),
            confidence=confidence,
            emotion=str(thought_data.get("emotion", "平静")),
        )

    def _extract_from_text(self, text: str, available_actions: list[GameAction]) -> Decision:
        """从非 JSON 文本中尽力提取决策信息"""
        text_lower = text.lower()

        # 尝试识别操作
        action_keywords = [
            ("fold", GameAction.FOLD),
            ("弃牌", GameAction.FOLD),
            ("compare", GameAction.COMPARE),
            ("比牌", GameAction.COMPARE),
            ("raise", GameAction.RAISE),
            ("加注", GameAction.RAISE),
            ("call", GameAction.CALL),
            ("跟注", GameAction.CALL),
            ("check", GameAction.CHECK_CARDS),
            ("看牌", GameAction.CHECK_CARDS),
        ]

        action = None
        for keyword, act in action_keywords:
            if keyword in text_lower:
                action = act
                break

        if action is None:
            action = self._get_fallback_action(available_actions)

        return Decision(
            action=action,
            thought=ThoughtData(reasoning=f"[文本解析] {text[:200]}"),
            raw_response=text,
        )

    @staticmethod
    def _get_fallback_action(available_actions: list[GameAction]) -> GameAction:
        """获取最安全的降级操作

        优先级：跟注 > 弃牌 > 列表中第一个
        """
        if GameAction.CALL in available_actions:
            return GameAction.CALL
        if GameAction.FOLD in available_actions:
            return GameAction.FOLD
        return available_actions[0] if available_actions else GameAction.FOLD

    def __repr__(self) -> str:
        return (
            f"BaseAgent(id={self.agent_id!r}, name={self.name!r}, "
            f"model={self.model_id!r}, personality={self.personality!r})"
        )


# ---- 异常 ----


class LLMCallError(Exception):
    """LLM 调用失败异常"""

    pass


# ---- 辅助函数 ----


def _configure_api_keys(settings: Any) -> None:
    """配置 LiteLLM 使用的 API keys

    LiteLLM 通过环境变量或直接设置来获取 API keys。
    这里通过设置 litellm 模块级变量来传递。
    """
    import os

    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    if settings.google_api_key:
        os.environ["GEMINI_API_KEY"] = settings.google_api_key
