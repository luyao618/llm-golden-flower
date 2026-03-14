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

from app.config import ALL_MODELS, _get_all_models, get_settings
from app.models.game import (
    ActionRecord,
    GameAction,
    GameConfig,
    GameState,
    Player,
    PlayerStatus,
    RoundState,
)
from app.models.card import Card
from app.engine.evaluator import evaluate_hand
from app.engine.rules import (
    get_available_actions,
    get_call_cost,
    get_raise_cost,
    get_compare_cost,
    validate_action,
)
from app.agents.personalities import (
    PersonalityProfile,
    get_personality,
    get_personality_description_for_prompt,
    PERSONALITY_PROFILES,
)
from app.agents.prompts import render_system_prompt, render_decision_prompt

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
        self.memory = AgentMemory()

        # 加载性格配置
        self.personality_profile: PersonalityProfile | None = PERSONALITY_PROFILES.get(personality)

        # 性格描述优先级：显式传入 > 从性格配置自动生成 > 默认占位
        if personality_description:
            self.personality_description = personality_description
        elif self.personality_profile:
            self.personality_description = get_personality_description_for_prompt(personality)
        else:
            self.personality_description = f"{personality}型玩家"

        # 验证 model_id 有效（使用动态注册表，包含 OpenRouter 模型）
        if model_id not in _get_all_models():
            logger.warning("Unknown model_id '%s', falling back to 'openai-gpt4o-mini'", model_id)
            self.model_id = "openai-gpt4o-mini"

    # ---- LLM 调用 ----

    async def call_llm(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> str:
        """封装 LLM 调用，含重试、超时、错误处理

        根据 model_id 对应的 provider 自动路由:
        - provider == "github_copilot": 绕过 LiteLLM，直接调用 Copilot API
        - 其他 Provider: 走原有 LiteLLM 路径

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
        model_config = _get_all_models().get(self.model_id)
        if not model_config:
            raise LLMCallError(f"Unknown model_id: {self.model_id}")

        model_name = model_config["model"]
        provider = model_config.get("provider", "")
        temp = temperature if temperature is not None else settings.llm_temperature
        fmt = response_format or {"type": "json_object"}

        # ---- Copilot 路径 ----
        if provider == "github_copilot":
            return await self._call_copilot(model_name, messages, temp, fmt)

        # ---- LiteLLM 路径 ----
        # 设置 API keys（LiteLLM 会根据模型自动选择对应的 key）
        _configure_api_keys(settings)

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
                    max_tokens=40960,
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

    async def _call_copilot(
        self,
        model_name: str,
        messages: list[dict[str, str]],
        temperature: float,
        response_format: dict | None = None,
    ) -> str:
        """通过 Copilot API 调用 LLM

        绕过 LiteLLM，直接使用 CopilotAuthManager 调用 Copilot Chat API。
        包含重试逻辑。
        """
        from app.services.copilot_auth import (
            get_copilot_auth,
            CopilotAuthError,
            CopilotAPIError,
            CopilotSubscriptionError,
        )

        settings = get_settings()
        copilot = get_copilot_auth()
        last_error: Exception | None = None

        for attempt in range(1, settings.llm_max_retries + 1):
            try:
                logger.info(
                    "[%s] Copilot API call attempt %d/%d, model=%s",
                    self.name,
                    attempt,
                    settings.llm_max_retries,
                    model_name,
                )

                content = await copilot.call_copilot_api(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    response_format=response_format,
                )

                logger.info("[%s] Copilot API call succeeded on attempt %d", self.name, attempt)
                return content

            except CopilotSubscriptionError as e:
                # 订阅/授权问题 (403) 不需要重试，直接抛出
                logger.error("[%s] Copilot subscription error (403): %s", self.name, str(e))
                raise LLMCallError(str(e), error_code="copilot_subscription_error") from e
            except (CopilotAuthError, CopilotAPIError) as e:
                last_error = e
                logger.warning(
                    "[%s] Copilot API call attempt %d failed: %s", self.name, attempt, str(e)
                )
                if attempt < settings.llm_max_retries:
                    import asyncio

                    wait_time = 2**attempt
                    logger.info("[%s] Retrying in %ds...", self.name, wait_time)
                    await asyncio.sleep(wait_time)
            except Exception as e:
                last_error = e
                logger.warning(
                    "[%s] Copilot API call attempt %d failed unexpectedly: %s",
                    self.name,
                    attempt,
                    str(e),
                )
                if attempt < settings.llm_max_retries:
                    import asyncio

                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)

        raise LLMCallError(
            f"Copilot API call failed after {settings.llm_max_retries} retries: {last_error}"
        )

    # ---- Prompt 构建 ----

    def build_system_prompt(self) -> str:
        """构建 system prompt

        使用 prompts 模块的模板，注入性格系统的完整描述文本。
        包含：角色身份 + 性格特征 + 炸金花规则 + 决策原则 + 牌桌交流指导 + 输出格式。

        Returns:
            完整的 system prompt 文本
        """
        personality_name = (
            self.personality_profile.name_zh if self.personality_profile else self.personality
        )
        return render_system_prompt(
            agent_name=self.name,
            personality_name=personality_name,
            personality_description=self.personality_description,
        )

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

    # ---- 决策流程 ----

    async def make_decision(
        self,
        game: GameState,
        player: Player,
        chat_context: list[dict[str, str]] | None = None,
    ) -> Decision:
        """完整的 AI 决策流程

        流程：
        1. 构建决策 prompt（手牌、局面、历史行动、聊天上下文、经验策略）
        2. 调用 LLM
        3. 解析响应为 Decision（action + thought + table_talk）
        4. 验证操作合法性，非法操作降级处理
        5. 比牌操作时验证/选择目标

        Args:
            game: 当前完整游戏状态
            player: 本 Agent 对应的玩家对象
            chat_context: 本局聊天记录列表，每条为 {"sender": ..., "message": ...}

        Returns:
            Decision 对象，包含 action、target、table_talk 和 thought
        """
        round_state = game.current_round
        assert round_state is not None

        # 1. 获取可用操作
        available_actions = get_available_actions(round_state, player, game.players, game.config)

        if not available_actions:
            logger.warning("[%s] No available actions, defaulting to FOLD", self.name)
            return Decision(action=GameAction.FOLD)

        # 2. 构建 prompt 上下文
        hand_description = format_hand_description(player.hand, player.has_seen_cards)
        seen_status = "看牌" if player.has_seen_cards else "未看牌"
        players_status_table = format_players_status(game.players, player.id, round_state)
        action_history = format_action_history(round_state.actions)
        chat_history = format_chat_history(chat_context)
        available_actions_text = format_available_actions(
            available_actions, round_state, player, game.players
        )
        experience_context = self.get_strategy_context()

        # 3. 渲染 prompt
        system_prompt = self.build_system_prompt()
        decision_prompt = render_decision_prompt(
            hand_description=hand_description,
            seen_status=seen_status,
            pot=round_state.pot,
            your_chips=player.chips,
            current_bet=round_state.current_bet,
            players_status_table=players_status_table,
            action_history=action_history,
            chat_history=chat_history,
            available_actions=available_actions_text,
            experience_context=experience_context,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": decision_prompt},
        ]

        # 4. 调用 LLM 并解析
        try:
            raw_response = await self.call_llm(messages)
            decision = self.parse_decision_response(raw_response, available_actions)
        except LLMCallError as e:
            # Copilot 订阅错误需要向上传播，让 WebSocket 层发送弹窗事件
            if e.error_code == "copilot_subscription_error":
                raise
            logger.error("[%s] LLM call failed, using fallback: %s", self.name, e)
            fallback_action = self._get_fallback_action(available_actions)
            decision = Decision(
                action=fallback_action,
                thought=ThoughtData(
                    reasoning=f"LLM 调用失败，降级为 {fallback_action.value}",
                    confidence=0.0,
                    emotion="无奈",
                ),
                raw_response=f"[LLM ERROR] {e}",
            )

        # 5. 验证比牌操作的目标
        if decision.action == GameAction.COMPARE:
            decision = self._validate_compare_target(decision, game, player, available_actions)

        # 6. 最终合法性校验（使用 rules 引擎做真正的校验）
        if not validate_action(
            round_state,
            player,
            decision.action,
            game.players,
            game.config,
            decision.target,
        ):
            logger.warning(
                "[%s] Action %s failed final validation, falling back",
                self.name,
                decision.action.value,
            )
            decision.action = self._get_fallback_action(available_actions)
            decision.target = None

        # 7. 记录思考数据
        if decision.thought:
            self.record_thought(round_state.round_number, decision.thought)

        return decision

    def _validate_compare_target(
        self,
        decision: Decision,
        game: GameState,
        player: Player,
        available_actions: list[GameAction],
    ) -> Decision:
        """验证比牌目标的合法性，必要时自动选择或降级

        Args:
            decision: 当前决策
            game: 游戏状态
            player: 当前玩家
            available_actions: 可用操作列表

        Returns:
            修正后的决策
        """
        # 获取可比牌的对手列表
        compare_targets = [p for p in game.players if p.id != player.id and p.is_active]

        if not compare_targets:
            # 没有可比的对手，降级
            logger.warning("[%s] No compare targets available, falling back", self.name)
            decision.action = self._get_fallback_action(
                [a for a in available_actions if a != GameAction.COMPARE]
            )
            decision.target = None
            return decision

        if decision.target:
            # 验证指定的目标是否合法
            target_player = game.get_player_by_id(decision.target)
            if target_player and target_player.is_active and target_player.id != player.id:
                return decision  # 目标合法
            else:
                logger.warning(
                    "[%s] Compare target '%s' is invalid, auto-selecting",
                    self.name,
                    decision.target,
                )

        # 自动选择比牌目标：选择筹码最少的活跃对手（策略性选择弱者）
        compare_targets.sort(key=lambda p: p.chips)
        decision.target = compare_targets[0].id
        logger.info(
            "[%s] Auto-selected compare target: %s",
            self.name,
            compare_targets[0].name,
        )
        return decision

    # ---- 策略上下文 ----

    def get_strategy_context(self) -> str:
        """获取经验回顾生成的策略上下文

        Returns:
            策略摘要文本，空字符串表示暂无策略调整
        """
        return self.memory.strategy_context

    def get_behavior_params(self) -> dict[str, float]:
        """获取性格行为倾向参数

        Returns:
            行为参数字典（aggression, bluff_tendency 等），
            如果没有性格配置则返回默认中性值。
        """
        if self.personality_profile:
            return self.personality_profile.get_behavior_params()
        return {
            "aggression": 0.5,
            "bluff_tendency": 0.3,
            "fold_threshold": 0.5,
            "talk_frequency": 0.5,
            "risk_tolerance": 0.5,
            "see_cards_tendency": 0.5,
        }

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
    """LLM 调用失败异常

    Attributes:
        error_code: 错误分类码，用于前端区分错误类型
            - "copilot_subscription_error": Copilot 订阅/授权问题 (403)
            - "llm_error": 其他 LLM 调用失败
    """

    def __init__(self, message: str, error_code: str = "llm_error") -> None:
        super().__init__(message)
        self.error_code = error_code


# ---- 辅助函数 ----


def _configure_api_keys(settings: Any) -> None:
    """配置 LiteLLM 使用的 API keys

    优先使用 ProviderManager 中的 key（包含用户通过 UI 运行时设置的），
    避免被 .env 中的占位符覆盖真实 key。
    """
    import os

    from app.services.provider_manager import get_provider_manager

    pm = get_provider_manager()

    for provider, env_key in [
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("google", "GEMINI_API_KEY"),
        ("openrouter", "OPENROUTER_API_KEY"),
    ]:
        key = pm.get_key(provider)
        if key:
            os.environ[env_key] = key


# ---- 决策上下文格式化函数 ----


def format_hand_description(hand: list[Card] | None, has_seen: bool) -> str:
    """格式化手牌描述

    Args:
        hand: 手牌列表（3 张牌），None 表示未发牌
        has_seen: 是否已看牌

    Returns:
        手牌描述文本，如 "红心K 黑桃K 方块3（一对K）"
        未看牌时返回 "未知（你还没有看牌）"
    """
    if hand is None:
        return "未知（未发牌）"

    if not has_seen:
        return "未知（你还没有看牌）"

    # 已看牌：显示具体的牌和牌型
    cards_str = ", ".join(c.chinese_description for c in hand)
    hand_result = evaluate_hand(hand)
    return f"{cards_str}（{hand_result.description}）"


def format_players_status(
    players: list[Player],
    viewer_id: str,
    round_state: RoundState,
) -> str:
    """格式化各玩家的状态表格

    Args:
        players: 所有玩家列表
        viewer_id: 当前 AI 的玩家 ID
        round_state: 当前局面状态

    Returns:
        格式化的玩家状态文本
    """
    lines = []
    for i, p in enumerate(players):
        is_self = "（你）" if p.id == viewer_id else ""
        is_current = " ← 当前行动" if i == round_state.current_player_index else ""

        if p.status == PlayerStatus.FOLDED:
            status_text = "已弃牌"
        elif p.status == PlayerStatus.OUT:
            status_text = "已出局"
        elif p.status == PlayerStatus.ACTIVE_BLIND:
            status_text = "暗注（未看牌）"
        elif p.status == PlayerStatus.ACTIVE_SEEN:
            status_text = "明注（已看牌）"
        else:
            status_text = p.status.value

        lines.append(
            f"- {p.name}{is_self}: 筹码 {p.chips}, "
            f"本局已下注 {p.total_bet_this_round}, "
            f"状态: {status_text}{is_current}"
        )

    return "\n".join(lines)


def format_action_history(actions: list[ActionRecord]) -> str:
    """格式化本局行动历史

    Args:
        actions: 行动记录列表

    Returns:
        格式化的行动历史文本，无行动时返回提示
    """
    if not actions:
        return "（本局尚无行动记录）"

    lines = []
    for i, a in enumerate(actions, 1):
        action_desc = _action_to_chinese(a.action)

        if a.amount and a.amount > 0:
            action_desc += f" {a.amount} 筹码"

        if a.target_id:
            action_desc += f"（对象: {a.target_id}）"

        name = a.player_name or a.player_id
        lines.append(f"{i}. {name} {action_desc}")

    return "\n".join(lines)


def format_chat_history(chat_context: list[dict[str, str]] | None) -> str:
    """格式化聊天记录

    Args:
        chat_context: 聊天记录列表，每条为 {"sender": ..., "message": ...}

    Returns:
        格式化的聊天记录文本
    """
    if not chat_context:
        return "（本局暂无聊天记录）"

    lines = []
    for msg in chat_context:
        sender = msg.get("sender", "未知")
        message = msg.get("message", "")
        lines.append(f"{sender}: {message}")

    return "\n".join(lines)


def format_available_actions(
    actions: list[GameAction],
    round_state: RoundState,
    player: Player,
    players: list[Player],
) -> str:
    """格式化可用操作列表（含费用说明）

    Args:
        actions: 可用操作列表
        round_state: 当前局面状态
        player: 当前玩家
        players: 所有玩家列表

    Returns:
        格式化的可用操作文本
    """
    lines = []
    for action in actions:
        desc = _action_to_chinese(action)

        if action == GameAction.CALL:
            cost = get_call_cost(round_state, player)
            desc += f"（费用: {cost} 筹码）"
        elif action == GameAction.RAISE:
            cost = get_raise_cost(round_state, player)
            desc += f"（费用: {cost} 筹码，注额将翻倍至 {round_state.current_bet * 2}）"
        elif action == GameAction.COMPARE:
            cost = get_compare_cost(round_state, player)
            targets = [p for p in players if p.id != player.id and p.is_active]
            target_names = ", ".join(f"{p.name}(ID:{p.id})" for p in targets)
            desc += f"（费用: {cost} 筹码，可比对象: {target_names}）"
        elif action == GameAction.FOLD:
            desc += "（无费用）"
        elif action == GameAction.CHECK_CARDS:
            desc += "（无费用，看牌后变为明注）"

        lines.append(f"- {action.value}: {desc}")

    return "\n".join(lines)


def _action_to_chinese(action: GameAction) -> str:
    """将 GameAction 转为中文描述"""
    mapping = {
        GameAction.FOLD: "弃牌",
        GameAction.CALL: "跟注",
        GameAction.RAISE: "加注",
        GameAction.CHECK_CARDS: "看牌",
        GameAction.COMPARE: "比牌",
    }
    return mapping.get(action, action.value)
