"""心路历程数据模型

定义 AI 心路历程系统的核心数据类型：
- ThoughtRecord: 单次决策的完整思考记录
- RoundNarrative: 单局叙事总结（第一人称）
- GameSummary: 整场游戏总结报告
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.game import GameAction


class ThoughtRecord(BaseModel):
    """单次决策的思考记录

    将 BaseAgent 中的 ThoughtData（轻量内存 dataclass）扩展为
    完整的持久化记录，增加了 agent_id、round/turn 编号、
    决策结果、发言、原始 LLM 响应等字段。

    Attributes:
        agent_id: Agent 唯一标识
        round_number: 局号
        turn_number: 该局中的第几次行动
        hand_evaluation: 手牌评估
        opponent_analysis: 对手分析
        risk_assessment: 风险评估
        chat_analysis: 对近期聊天内容的分析
        decision: 最终决策操作
        decision_target: 比牌对象 ID（如有）
        reasoning: 决策理由
        confidence: 信心值 0-1
        emotion: 情绪标签
        table_talk: 操作时附带的发言（None 表示沉默）
        raw_response: 原始 LLM 输出文本
    """

    agent_id: str
    round_number: int
    turn_number: int = 0

    # 结构化思考数据（对应 ThoughtData 的字段）
    hand_evaluation: str = ""
    opponent_analysis: str = ""
    risk_assessment: str = ""
    chat_analysis: str | None = None
    reasoning: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    emotion: str = "平静"

    # 决策结果
    decision: GameAction = GameAction.FOLD
    decision_target: str | None = None
    table_talk: str | None = None

    # 原始 LLM 输出
    raw_response: str = ""


class RoundNarrative(BaseModel):
    """单局叙事总结

    由 LLM 以第一人称生成的单局回顾叙事。

    Attributes:
        agent_id: Agent 唯一标识
        round_number: 局号
        narrative: 第一人称叙事文本（200-400 字）
        outcome: 本局结果的一句话总结
    """

    agent_id: str
    round_number: int
    narrative: str
    outcome: str


class GameSummary(BaseModel):
    """整场游戏总结

    由 LLM 生成的完整游戏回顾报告，包含统计数据和叙事内容。

    Attributes:
        agent_id: Agent 唯一标识
        rounds_played: 总局数
        rounds_won: 赢的局数
        total_chips_won: 总赢得筹码
        total_chips_lost: 总输掉筹码
        biggest_win: 最大单局赢利
        biggest_loss: 最大单局亏损
        fold_rate: 弃牌率
        key_moments: 关键时刻回顾列表
        opponent_impressions: 对各对手的印象评价
        self_reflection: 自我风格总结
        chat_strategy_summary: 聊天策略总结
        learning_journey: 学习历程总结
        narrative_summary: 完整叙事总结（300-600 字）
    """

    agent_id: str

    # 统计数据
    rounds_played: int = 0
    rounds_won: int = 0
    total_chips_won: int = 0
    total_chips_lost: int = 0
    biggest_win: int = 0
    biggest_loss: int = 0
    fold_rate: float = 0.0

    # 叙事报告
    key_moments: list[str] = Field(default_factory=list)
    opponent_impressions: dict[str, str] = Field(default_factory=dict)
    self_reflection: str = ""
    chat_strategy_summary: str = ""
    learning_journey: str = ""
    narrative_summary: str = ""
