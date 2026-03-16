"""叙事报告生成器

ThoughtReporter 使用 LLM 生成两类叙事文本：
1. generate_round_narrative — 单局第一人称叙事回顾
2. generate_game_summary   — 整场游戏总结报告

依赖 BaseAgent.call_llm() 进行 LLM 调用，
使用 prompts 模块中已定义的模板。
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from app.agents.prompts import (
    render_game_summary_prompt,
    render_round_narrative_prompt,
)
from app.models.thought import GameSummary, RoundNarrative, ThoughtRecord

if TYPE_CHECKING:
    from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ThoughtReporter:
    """叙事报告生成器

    为指定的 Agent 调用 LLM 生成单局叙事和整场总结。

    Attributes:
        agent: 关联的 BaseAgent 实例（用于获取身份信息和调用 LLM）
    """

    def __init__(self, agent: BaseAgent) -> None:
        self.agent = agent

    async def generate_round_narrative(
        self,
        round_number: int,
        round_thoughts: list[ThoughtRecord],
        chat_messages: str,
        action_history: str,
        hand_description: str,
        round_outcome: str,
    ) -> RoundNarrative:
        """生成单局叙事回顾

        调用 LLM 以第一人称生成 200-400 字的单局叙事。

        Args:
            round_number: 局号
            round_thoughts: 该局的所有思考记录
            chat_messages: 该局的聊天记录文本
            action_history: 该局的行动记录文本
            hand_description: 手牌描述
            round_outcome: 本局结果描述

        Returns:
            RoundNarrative 实例
        """
        # 格式化思考过程
        thoughts_text = self._format_thoughts(round_thoughts)

        prompt = render_round_narrative_prompt(
            agent_name=self.agent.name,
            round_number=round_number,
            hand_description=hand_description,
            round_outcome=round_outcome,
            round_thoughts=thoughts_text,
            chat_messages=chat_messages,
            action_history=action_history,
        )

        messages = [
            {"role": "system", "content": f"你是{self.agent.name}，正在回顾一局炸金花的经历。"},
            {"role": "user", "content": prompt},
        ]

        try:
            raw_response = await self.agent.call_llm(messages, temperature=0.8)
            parsed = self._try_parse_json(raw_response)

            if parsed:
                return RoundNarrative(
                    agent_id=self.agent.agent_id,
                    round_number=round_number,
                    narrative=str(parsed.get("narrative", "")),
                    outcome=str(parsed.get("outcome", "")),
                )
            else:
                # JSON 解析失败，将原始文本作为叙事
                logger.warning(
                    "[ThoughtReporter:%s] Failed to parse round narrative JSON, using raw text",
                    self.agent.name,
                )
                return RoundNarrative(
                    agent_id=self.agent.agent_id,
                    round_number=round_number,
                    narrative=raw_response.strip(),
                    outcome=round_outcome,
                )

        except Exception as e:
            logger.error(
                "[ThoughtReporter:%s] Failed to generate round narrative: %s",
                self.agent.name,
                str(e),
            )
            # 降级：用思考记录拼接简单叙事
            fallback_narrative = self._build_fallback_narrative(
                round_number, round_thoughts, round_outcome
            )
            return RoundNarrative(
                agent_id=self.agent.agent_id,
                round_number=round_number,
                narrative=fallback_narrative,
                outcome=round_outcome,
            )

    async def generate_game_summary(
        self,
        rounds_played: int,
        rounds_won: int,
        total_chips_won: int,
        total_chips_lost: int,
        biggest_win: int,
        biggest_loss: int,
        fold_rate: str,
        all_narratives: str,
        all_reviews: str,
        opponents_info: str,
    ) -> GameSummary:
        """生成整场游戏总结

        调用 LLM 生成包含关键时刻、对手印象、自我反思等内容的完整总结。

        Args:
            rounds_played: 总局数
            rounds_won: 赢的局数
            total_chips_won: 总赢得筹码
            total_chips_lost: 总输掉筹码
            biggest_win: 最大单局赢利
            biggest_loss: 最大单局亏损
            fold_rate: 弃牌率文本（如 "40%"）
            all_narratives: 所有局的叙事回顾文本
            all_reviews: 所有经验回顾记录文本
            opponents_info: 对手信息列表文本

        Returns:
            GameSummary 实例
        """
        prompt = render_game_summary_prompt(
            agent_name=self.agent.name,
            rounds_played=rounds_played,
            rounds_won=rounds_won,
            total_chips_won=total_chips_won,
            total_chips_lost=total_chips_lost,
            biggest_win=biggest_win,
            biggest_loss=biggest_loss,
            fold_rate=fold_rate,
            all_narratives=all_narratives,
            all_reviews=all_reviews,
            opponents_info=opponents_info,
        )

        messages = [
            {
                "role": "system",
                "content": f"你是{self.agent.name}，正在对整场炸金花游戏进行总结回顾。",
            },
            {"role": "user", "content": prompt},
        ]

        # 解析 fold_rate 为 float（用于 GameSummary 模型）
        fold_rate_float = self._parse_fold_rate(fold_rate)

        try:
            raw_response = await self.agent.call_llm(messages, temperature=0.8)
            parsed = self._try_parse_json(raw_response)

            if parsed:
                return GameSummary(
                    agent_id=self.agent.agent_id,
                    rounds_played=rounds_played,
                    rounds_won=rounds_won,
                    total_chips_won=total_chips_won,
                    total_chips_lost=total_chips_lost,
                    biggest_win=biggest_win,
                    biggest_loss=biggest_loss,
                    fold_rate=fold_rate_float,
                    key_moments=parsed.get("key_moments", []),
                    opponent_impressions=parsed.get("opponent_impressions", {}),
                    self_reflection=str(parsed.get("self_reflection", "")),
                    chat_strategy_summary=str(parsed.get("chat_strategy_summary", "")),
                    learning_journey=str(parsed.get("learning_journey", "")),
                    narrative_summary=str(parsed.get("narrative_summary", "")),
                )
            else:
                logger.warning(
                    "[ThoughtReporter:%s] Failed to parse game summary JSON, "
                    "using raw text as narrative",
                    self.agent.name,
                )
                return GameSummary(
                    agent_id=self.agent.agent_id,
                    rounds_played=rounds_played,
                    rounds_won=rounds_won,
                    total_chips_won=total_chips_won,
                    total_chips_lost=total_chips_lost,
                    biggest_win=biggest_win,
                    biggest_loss=biggest_loss,
                    fold_rate=fold_rate_float,
                    narrative_summary=raw_response.strip(),
                )

        except Exception as e:
            logger.error(
                "[ThoughtReporter:%s] Failed to generate game summary: %s",
                self.agent.name,
                str(e),
            )
            return GameSummary(
                agent_id=self.agent.agent_id,
                rounds_played=rounds_played,
                rounds_won=rounds_won,
                total_chips_won=total_chips_won,
                total_chips_lost=total_chips_lost,
                biggest_win=biggest_win,
                biggest_loss=biggest_loss,
                fold_rate=fold_rate_float,
                narrative_summary=f"（总结生成失败: {e}）",
            )

    # ---- 辅助方法 ----

    @staticmethod
    def _format_thoughts(thoughts: list[ThoughtRecord]) -> str:
        """将思考记录列表格式化为 Prompt 文本"""
        if not thoughts:
            return "（本局无思考记录）"

        lines: list[str] = []
        for i, t in enumerate(thoughts, 1):
            lines.append(f"第 {i} 次决策（{t.decision.value}）:")
            if t.hand_evaluation:
                lines.append(f"  手牌评估: {t.hand_evaluation}")
            if t.opponent_analysis:
                lines.append(f"  对手分析: {t.opponent_analysis}")
            if t.chat_analysis:
                lines.append(f"  聊天分析: {t.chat_analysis}")
            if t.risk_assessment:
                lines.append(f"  风险评估: {t.risk_assessment}")
            if t.reasoning:
                lines.append(f"  决策理由: {t.reasoning}")
            lines.append(f"  信心: {t.confidence:.0%}, 情绪: {t.emotion}")
            if t.table_talk:
                lines.append(f'  发言: "{t.table_talk}"')
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _try_parse_json(text: str) -> dict | None:
        """尝试从文本中解析 JSON（与 BaseAgent 的逻辑一致）"""
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

    @staticmethod
    def _build_fallback_narrative(
        round_number: int,
        thoughts: list[ThoughtRecord],
        outcome: str,
    ) -> str:
        """LLM 调用失败时的降级叙事生成"""
        if not thoughts:
            return f"第 {round_number} 局，{outcome}。"

        parts = [f"第 {round_number} 局"]
        last_thought = thoughts[-1]

        if last_thought.hand_evaluation:
            parts.append(f"我的手牌{last_thought.hand_evaluation}")
        if last_thought.reasoning:
            parts.append(f"最终{last_thought.reasoning}")
        parts.append(f"结果是{outcome}")

        return "，".join(parts) + "。"

    @staticmethod
    def _parse_fold_rate(fold_rate: str) -> float:
        """将弃牌率文本解析为 float"""
        try:
            cleaned = fold_rate.strip().rstrip("%")
            return float(cleaned) / 100.0
        except (ValueError, AttributeError):
            return 0.0
