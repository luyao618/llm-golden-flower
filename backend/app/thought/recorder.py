"""思考记录器

ThoughtRecorder 负责将 BaseAgent 的轻量 ThoughtData + Decision 数据
转换为完整的 ThoughtRecord，并按局号组织存储。

使用方式：
    recorder = ThoughtRecorder(agent_id="agent-1")
    recorder.append_thought(round_number=1, thought_data=td, decision=dec, turn_number=3)
    thoughts = recorder.get_round_thoughts(1)
"""

from __future__ import annotations

import logging

from app.agents.base_agent import Decision, ThoughtData
from app.models.game import GameAction
from app.models.thought import ThoughtRecord

logger = logging.getLogger(__name__)


class ThoughtRecorder:
    """AI 决策思考记录器

    将每次 AI 决策产生的 ThoughtData 和 Decision 合并为
    完整的 ThoughtRecord，按 round_number 索引存储。

    Attributes:
        agent_id: 所属 Agent 的唯一标识
        records: 按局号索引的思考记录字典
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self.records: dict[int, list[ThoughtRecord]] = {}

    def append_thought(
        self,
        round_number: int,
        thought_data: ThoughtData | None = None,
        decision: Decision | None = None,
        turn_number: int = 0,
    ) -> ThoughtRecord:
        """记录一次决策的思考数据

        将 ThoughtData（思考过程）和 Decision（决策结果）合并为
        完整的 ThoughtRecord 并存储。

        Args:
            round_number: 局号
            thought_data: 思考数据（来自 LLM 响应解析）
            decision: 决策结果（含 action, target, table_talk 等）
            turn_number: 该局中的第几次行动

        Returns:
            创建的 ThoughtRecord 实例
        """
        td = thought_data or ThoughtData()

        record = ThoughtRecord(
            agent_id=self.agent_id,
            round_number=round_number,
            turn_number=turn_number,
            hand_evaluation=td.hand_evaluation,
            opponent_analysis=td.opponent_analysis,
            risk_assessment=td.risk_assessment,
            chat_analysis=td.chat_analysis if td.chat_analysis else None,
            reasoning=td.reasoning,
            confidence=td.confidence,
            emotion=td.emotion,
            decision=decision.action if decision else GameAction.FOLD,
            decision_target=decision.target if decision else None,
            table_talk=decision.table_talk if decision else None,
            raw_response=decision.raw_response if decision else "",
        )

        if round_number not in self.records:
            self.records[round_number] = []
        self.records[round_number].append(record)

        logger.debug(
            "[ThoughtRecorder:%s] Recorded thought for round %d, turn %d "
            "(decision=%s, confidence=%.2f, emotion=%s)",
            self.agent_id,
            round_number,
            turn_number,
            record.decision.value,
            record.confidence,
            record.emotion,
        )

        return record

    def get_round_thoughts(self, round_number: int) -> list[ThoughtRecord]:
        """获取某一局的所有思考记录

        Args:
            round_number: 局号

        Returns:
            该局的思考记录列表，如果没有则返回空列表
        """
        return self.records.get(round_number, [])

    def get_all_thoughts(self) -> dict[int, list[ThoughtRecord]]:
        """获取所有局的思考记录

        Returns:
            按局号索引的完整思考记录字典
        """
        return self.records

    def get_all_thoughts_flat(self) -> list[ThoughtRecord]:
        """获取所有思考记录的扁平列表（按局号和 turn 排序）

        Returns:
            所有思考记录的有序列表
        """
        result: list[ThoughtRecord] = []
        for round_num in sorted(self.records.keys()):
            result.extend(self.records[round_num])
        return result

    def clear(self) -> None:
        """清空所有记录"""
        self.records.clear()

    def format_round_thoughts_for_prompt(self, round_number: int) -> str:
        """将某局的思考记录格式化为文本，供 Prompt 使用

        Args:
            round_number: 局号

        Returns:
            格式化后的思考过程文本
        """
        thoughts = self.get_round_thoughts(round_number)
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
