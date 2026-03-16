"""经验回顾系统

ExperienceReviewer 负责：
1. 检测经验回顾触发条件（5 种）
2. 收集近期心路历程和对手统计
3. 调用 LLM 生成经验分析和策略调整
4. 将策略摘要注入后续决策的 prompt

使用方式：
    reviewer = ExperienceReviewer(agent=agent, initial_chips=1000)
    trigger = reviewer.check_trigger(game, round_result)
    if trigger:
        review = await reviewer.perform_review(
            trigger, recent_narratives, recent_thoughts, opponent_stats
        )
        agent.set_strategy_context(review.strategy_context)
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from app.agents.prompts import (
    EXPERIENCE_REVIEW_OUTPUT_SCHEMA,
    render_experience_review_prompt,
)
from app.models.game import GameState, Player, RoundResult
from app.models.thought import (
    ExperienceReview,
    ReviewTrigger,
    RoundNarrative,
    ThoughtRecord,
)

if TYPE_CHECKING:
    from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# 回顾最近多少局
DEFAULT_REVIEW_WINDOW = 5

# 触发阈值常量
CHIP_CRISIS_RATIO = 0.3  # 筹码低于初始值的 30%
BIG_LOSS_RATIO = 0.2  # 单局损失超过初始筹码的 20%
CONSECUTIVE_LOSSES_THRESHOLD = 2  # 连续输 2 局触发
PERIODIC_INTERVAL = 5  # 每 5 局定期回顾
OPPONENT_SHIFT_THRESHOLD = 0.4  # 对手行为变化阈值


class ExperienceReviewer:
    """AI 经验回顾系统

    跟踪 AI 的胜负历史和筹码变化，在满足触发条件时
    调用 LLM 进行经验回顾，生成策略调整并注入后续决策。

    Attributes:
        agent: 关联的 BaseAgent 实例
        initial_chips: 游戏开始时的初始筹码
        consecutive_losses: 当前连败计数
        rounds_since_review: 距上次回顾的局数
        last_review_round: 上次回顾时的局号
        reviews: 所有经验回顾记录
        round_results_history: 历史局结果记录（用于对手行为分析）
    """

    def __init__(self, agent: BaseAgent, initial_chips: int = 1000) -> None:
        self.agent = agent
        self.initial_chips = initial_chips
        self.consecutive_losses: int = 0
        self.rounds_since_review: int = 0
        self.last_review_round: int = 0
        self.reviews: list[ExperienceReview] = []
        self.round_results_history: list[RoundResult] = []

        # 对手行为画像缓存: {player_id: {"fold_count": int, "raise_count": int, ...}}
        self._opponent_action_stats: dict[str, dict[str, int]] = {}

    # ============================================================
    # 触发条件检查
    # ============================================================

    def check_trigger(
        self,
        game: GameState,
        round_result: RoundResult,
    ) -> ReviewTrigger | None:
        """检查是否应该触发经验回顾

        按优先级从高到低检查 5 种触发条件。
        每次调用会更新内部的连败计数和回顾间隔计数。

        Args:
            game: 当前游戏状态
            round_result: 刚结束的那局的结算结果

        Returns:
            触发的条件类型，None 表示不触发
        """
        self.rounds_since_review += 1
        self.round_results_history.append(round_result)

        # 更新对手行为统计
        self._update_opponent_stats(round_result)

        # 更新连败计数
        is_loss = round_result.winner_id != self.agent.agent_id
        if is_loss:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # 获取当前筹码
        current_chips = self._get_player_chips(game)

        # 按优先级检查触发条件
        # 1. 筹码危机（最高优先级）
        if current_chips <= self.initial_chips * CHIP_CRISIS_RATIO:
            logger.info(
                "[ExperienceReviewer:%s] CHIP_CRISIS triggered (chips=%d, threshold=%d)",
                self.agent.name,
                current_chips,
                int(self.initial_chips * CHIP_CRISIS_RATIO),
            )
            return ReviewTrigger.CHIP_CRISIS

        # 2. 连续输牌
        if self.consecutive_losses >= CONSECUTIVE_LOSSES_THRESHOLD:
            logger.info(
                "[ExperienceReviewer:%s] CONSECUTIVE_LOSSES triggered (losses=%d)",
                self.agent.name,
                self.consecutive_losses,
            )
            return ReviewTrigger.CONSECUTIVE_LOSSES

        # 3. 单局大额损失
        if is_loss:
            loss_amount = self._calculate_loss(round_result)
            if loss_amount > self.initial_chips * BIG_LOSS_RATIO:
                logger.info(
                    "[ExperienceReviewer:%s] BIG_LOSS triggered (loss=%d, threshold=%d)",
                    self.agent.name,
                    loss_amount,
                    int(self.initial_chips * BIG_LOSS_RATIO),
                )
                return ReviewTrigger.BIG_LOSS

        # 4. 对手行为突变
        if self._detect_opponent_shift():
            logger.info(
                "[ExperienceReviewer:%s] OPPONENT_SHIFT triggered",
                self.agent.name,
            )
            return ReviewTrigger.OPPONENT_SHIFT

        # 5. 定期回顾（最低优先级）
        if self.rounds_since_review >= PERIODIC_INTERVAL:
            logger.info(
                "[ExperienceReviewer:%s] PERIODIC triggered (rounds_since_review=%d)",
                self.agent.name,
                self.rounds_since_review,
            )
            return ReviewTrigger.PERIODIC

        return None

    # ============================================================
    # 执行经验回顾
    # ============================================================

    async def perform_review(
        self,
        trigger: ReviewTrigger,
        recent_narratives: list[RoundNarrative],
        recent_thoughts: list[ThoughtRecord],
        opponent_stats: dict[str, str],
    ) -> ExperienceReview:
        """执行经验回顾，调用 LLM 生成策略调整

        Args:
            trigger: 触发条件
            recent_narratives: 最近几局的叙事回顾
            recent_thoughts: 最近几局的思考记录
            opponent_stats: 对手行为统计文本 {player_id: 描述}

        Returns:
            ExperienceReview 实例
        """
        # 重置计数器
        self.rounds_since_review = 0
        current_round = (
            self.round_results_history[-1].round_number if self.round_results_history else 0
        )
        self.last_review_round = current_round

        # 确定回顾范围
        rounds_reviewed = self._get_rounds_reviewed(recent_narratives)

        # 计算统计数据
        stats = self._calculate_review_stats(rounds_reviewed)

        # 构建 prompt
        trigger_reason = self._get_trigger_reason(trigger, stats)
        narratives_text = self._format_narratives(recent_narratives)
        opponent_behaviors_text = self._format_opponent_stats(opponent_stats)

        prompt = render_experience_review_prompt(
            trigger_reason=trigger_reason,
            past_rounds_narratives=narratives_text,
            review_round_count=len(rounds_reviewed),
            win_rate=stats["win_rate"],
            chips_change=stats["chips_change"],
            fold_rate=stats["fold_rate"],
            opponent_recent_behaviors=opponent_behaviors_text,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    f"你是{self.agent.name}，一个炸金花玩家。"
                    f"你正在回顾最近的牌局，反思自己的表现并调整策略。"
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            raw_response = await self.agent.call_llm(messages, temperature=0.7)
            review = self._parse_review_response(
                raw_response=raw_response,
                trigger=trigger,
                current_round=current_round,
                rounds_reviewed=rounds_reviewed,
            )
        except Exception as e:
            logger.error(
                "[ExperienceReviewer:%s] LLM call failed: %s",
                self.agent.name,
                str(e),
            )
            review = self._build_fallback_review(
                trigger=trigger,
                current_round=current_round,
                rounds_reviewed=rounds_reviewed,
                error=str(e),
            )

        # 生成策略注入文本
        review.strategy_context = self.generate_strategy_context(review)

        # 保存记录
        self.reviews.append(review)

        # 重置连败计数（回顾后重新计算）
        if trigger == ReviewTrigger.CONSECUTIVE_LOSSES:
            self.consecutive_losses = 0

        logger.info(
            "[ExperienceReviewer:%s] Review completed (trigger=%s, round=%d, "
            "strategy_adjustment=%s)",
            self.agent.name,
            trigger.value,
            current_round,
            review.strategy_adjustment[:80] if review.strategy_adjustment else "(empty)",
        )

        return review

    # ============================================================
    # 策略注入
    # ============================================================

    def generate_strategy_context(self, review: ExperienceReview) -> str:
        """生成注入后续决策的策略摘要文本

        将经验回顾的结论转化为简洁的策略提示，
        注入到后续决策 prompt 的 experience_context 部分。

        Args:
            review: 经验回顾记录

        Returns:
            策略摘要文本
        """
        parts: list[str] = []

        if review.self_analysis:
            parts.append(f"【自我反思】{review.self_analysis}")

        if review.opponent_patterns:
            opponent_lines = []
            for pid, pattern in review.opponent_patterns.items():
                opponent_lines.append(f"  - {pid}: {pattern}")
            if opponent_lines:
                parts.append("【对手分析】\n" + "\n".join(opponent_lines))

        if review.strategy_adjustment:
            parts.append(f"【策略调整】{review.strategy_adjustment}")

        if not parts:
            return ""

        header = f"（基于第 {review.triggered_at_round} 局后的经验回顾，"
        header += f"触发原因: {self._trigger_to_chinese(review.trigger)}）"

        return header + "\n" + "\n".join(parts)

    def get_all_reviews(self) -> list[ExperienceReview]:
        """获取所有经验回顾记录"""
        return self.reviews

    def get_reviews_text(self) -> str:
        """获取所有经验回顾记录的文本格式（用于叙事生成）"""
        if not self.reviews:
            return "（无经验回顾）"

        lines: list[str] = []
        for i, review in enumerate(self.reviews, 1):
            lines.append(
                f"第 {i} 次经验回顾（第 {review.triggered_at_round} 局后，"
                f"触发: {self._trigger_to_chinese(review.trigger)}）:"
            )
            if review.self_analysis:
                lines.append(f"  自我分析: {review.self_analysis}")
            if review.strategy_adjustment:
                lines.append(f"  策略调整: {review.strategy_adjustment}")
            lines.append("")

        return "\n".join(lines)

    def reset(self) -> None:
        """重置回顾器状态（新游戏时调用）"""
        self.consecutive_losses = 0
        self.rounds_since_review = 0
        self.last_review_round = 0
        self.reviews.clear()
        self.round_results_history.clear()
        self._opponent_action_stats.clear()

    # ============================================================
    # 内部辅助方法
    # ============================================================

    def _get_player_chips(self, game: GameState) -> int:
        """获取本 Agent 在游戏中的当前筹码"""
        player = game.get_player_by_id(self.agent.agent_id)
        if player:
            return player.chips
        return 0

    def _calculate_loss(self, round_result: RoundResult) -> int:
        """计算本 Agent 在某一局的损失金额"""
        chip_change = round_result.player_chip_changes.get(self.agent.agent_id, 0)
        # chip_change 为负数表示损失
        return abs(chip_change) if chip_change < 0 else 0

    def _update_opponent_stats(self, round_result: RoundResult) -> None:
        """根据局结果更新对手行为统计"""
        # 从 round_result 无法直接获取详细行动分布，
        # 这里主要记录胜负和筹码变化来辅助 opponent_shift 检测
        for pid, change in round_result.player_chip_changes.items():
            if pid == self.agent.agent_id:
                continue
            if pid not in self._opponent_action_stats:
                self._opponent_action_stats[pid] = {
                    "rounds": 0,
                    "wins": 0,
                    "total_change": 0,
                    "recent_wins": 0,
                    "recent_rounds": 0,
                }
            stats = self._opponent_action_stats[pid]
            stats["rounds"] += 1
            stats["total_change"] += change
            if round_result.winner_id == pid:
                stats["wins"] += 1

            # 滑动窗口：最近 5 局
            stats["recent_rounds"] += 1
            if round_result.winner_id == pid:
                stats["recent_wins"] += 1
            # 每 10 局重置 recent 计数以保持窗口
            if stats["recent_rounds"] > 10:
                stats["recent_wins"] = max(0, stats["recent_wins"] - stats["wins"] // 2)
                stats["recent_rounds"] = 5

    def _detect_opponent_shift(self) -> bool:
        """检测是否有对手行为突变

        比较对手的整体胜率与近期胜率，差异超过阈值则认为发生突变。
        """
        if len(self.round_results_history) < 5:
            return False

        for pid, stats in self._opponent_action_stats.items():
            total_rounds = stats["rounds"]
            if total_rounds < 5:
                continue

            overall_win_rate = stats["wins"] / total_rounds
            recent_rounds = stats["recent_rounds"]
            if recent_rounds < 3:
                continue

            recent_win_rate = stats["recent_wins"] / recent_rounds

            # 胜率变化超过阈值
            if abs(recent_win_rate - overall_win_rate) > OPPONENT_SHIFT_THRESHOLD:
                logger.debug(
                    "[ExperienceReviewer:%s] Opponent %s shift detected: overall=%.2f, recent=%.2f",
                    self.agent.name,
                    pid,
                    overall_win_rate,
                    recent_win_rate,
                )
                return True

        return False

    def _get_rounds_reviewed(self, narratives: list[RoundNarrative]) -> list[int]:
        """确定回顾了哪几局"""
        if narratives:
            return sorted({n.round_number for n in narratives})

        # 从历史结果推算
        recent = self.round_results_history[-DEFAULT_REVIEW_WINDOW:]
        return [r.round_number for r in recent]

    def _calculate_review_stats(self, rounds_reviewed: list[int]) -> dict[str, str]:
        """计算回顾范围内的统计数据"""
        if not rounds_reviewed or not self.round_results_history:
            return {
                "win_rate": "0%",
                "chips_change": "0",
                "fold_rate": "0%",
            }

        reviewed_set = set(rounds_reviewed)
        relevant_results = [r for r in self.round_results_history if r.round_number in reviewed_set]

        total = len(relevant_results)
        if total == 0:
            return {
                "win_rate": "0%",
                "chips_change": "0",
                "fold_rate": "0%",
            }

        wins = sum(1 for r in relevant_results if r.winner_id == self.agent.agent_id)
        chips_change = sum(
            r.player_chip_changes.get(self.agent.agent_id, 0) for r in relevant_results
        )

        # 弃牌率需要从行动记录推算，这里用近似值
        fold_count = sum(
            1
            for r in relevant_results
            if r.win_method and "弃牌" in r.win_method and r.winner_id != self.agent.agent_id
        )

        win_rate = f"{wins * 100 // total}%"
        chips_change_str = f"{chips_change:+d}" if chips_change != 0 else "0"
        fold_rate = f"{fold_count * 100 // total}%" if total > 0 else "0%"

        return {
            "win_rate": win_rate,
            "chips_change": chips_change_str,
            "fold_rate": fold_rate,
        }

    def _get_trigger_reason(self, trigger: ReviewTrigger, stats: dict[str, str]) -> str:
        """生成触发原因的描述文本"""
        reasons = {
            ReviewTrigger.CHIP_CRISIS: (
                f"你的筹码已经降至危险水平，"
                f"需要紧急调整策略。"
                f"最近的筹码变化: {stats['chips_change']}。"
            ),
            ReviewTrigger.CONSECUTIVE_LOSSES: (
                f"你已经连续输了 {self.consecutive_losses} 局，"
                f"需要反思一下自己的策略是否有问题。"
                f"近期胜率: {stats['win_rate']}。"
            ),
            ReviewTrigger.BIG_LOSS: (
                f"上一局你损失了大量筹码（{stats['chips_change']}），需要分析这次失误的原因。"
            ),
            ReviewTrigger.OPPONENT_SHIFT: (
                "你注意到某些对手的行为模式发生了明显变化，需要重新评估对手策略并调整自己的打法。"
            ),
            ReviewTrigger.PERIODIC: (
                f"打了好几局了（近期胜率: {stats['win_rate']}），是时候回顾一下整体表现了。"
            ),
        }
        return reasons.get(trigger, "需要回顾最近的表现。")

    @staticmethod
    def _format_narratives(narratives: list[RoundNarrative]) -> str:
        """格式化叙事回顾为文本"""
        if not narratives:
            return "（无叙事记录）"

        lines: list[str] = []
        for n in narratives:
            lines.append(f"第 {n.round_number} 局（结果: {n.outcome}）:")
            lines.append(f"  {n.narrative}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_opponent_stats(opponent_stats: dict[str, str]) -> str:
        """格式化对手统计为文本"""
        if not opponent_stats:
            return "（暂无对手行为数据）"

        lines: list[str] = []
        for pid, desc in opponent_stats.items():
            lines.append(f"- {pid}: {desc}")

        return "\n".join(lines)

    def _parse_review_response(
        self,
        raw_response: str,
        trigger: ReviewTrigger,
        current_round: int,
        rounds_reviewed: list[int],
    ) -> ExperienceReview:
        """解析 LLM 的经验回顾响应"""
        parsed = self._try_parse_json(raw_response)

        if parsed:
            # 解析 confidence_shift
            confidence_shift = parsed.get("confidence_shift", 0.0)
            try:
                confidence_shift = float(confidence_shift)
                confidence_shift = max(-1.0, min(1.0, confidence_shift))
            except (ValueError, TypeError):
                confidence_shift = 0.0

            # 解析 opponent_patterns
            opponent_patterns = parsed.get("opponent_patterns", {})
            if not isinstance(opponent_patterns, dict):
                opponent_patterns = {}
            # 确保 values 都是字符串
            opponent_patterns = {str(k): str(v) for k, v in opponent_patterns.items()}

            return ExperienceReview(
                agent_id=self.agent.agent_id,
                trigger=trigger,
                triggered_at_round=current_round,
                rounds_reviewed=rounds_reviewed,
                self_analysis=str(parsed.get("self_analysis", "")),
                opponent_patterns=opponent_patterns,
                strategy_adjustment=str(parsed.get("strategy_adjustment", "")),
                confidence_shift=confidence_shift,
            )
        else:
            # JSON 解析失败，将原始文本作为自我分析
            logger.warning(
                "[ExperienceReviewer:%s] Failed to parse review JSON, using raw text",
                self.agent.name,
            )
            return ExperienceReview(
                agent_id=self.agent.agent_id,
                trigger=trigger,
                triggered_at_round=current_round,
                rounds_reviewed=rounds_reviewed,
                self_analysis=raw_response.strip()[:500],
                strategy_adjustment="继续观察，谨慎调整。",
            )

    def _build_fallback_review(
        self,
        trigger: ReviewTrigger,
        current_round: int,
        rounds_reviewed: list[int],
        error: str,
    ) -> ExperienceReview:
        """LLM 调用失败时的降级回顾"""
        fallback_strategies = {
            ReviewTrigger.CHIP_CRISIS: "筹码不足，需要更谨慎地选择参与的牌局，只在有好牌时才投入。",
            ReviewTrigger.CONSECUTIVE_LOSSES: "连续输牌，需要调整打法，减少不必要的跟注。",
            ReviewTrigger.BIG_LOSS: "刚经历大额亏损，下几局需要保守一些，控制损失。",
            ReviewTrigger.OPPONENT_SHIFT: "对手打法有变化，需要更加注意观察。",
            ReviewTrigger.PERIODIC: "定期回顾，保持当前策略，注意对手动向。",
        }

        return ExperienceReview(
            agent_id=self.agent.agent_id,
            trigger=trigger,
            triggered_at_round=current_round,
            rounds_reviewed=rounds_reviewed,
            self_analysis=f"（经验回顾生成失败: {error}）",
            strategy_adjustment=fallback_strategies.get(trigger, "保持当前策略。"),
        )

    @staticmethod
    def _trigger_to_chinese(trigger: ReviewTrigger) -> str:
        """将触发条件转为中文描述"""
        mapping = {
            ReviewTrigger.CHIP_CRISIS: "筹码危机",
            ReviewTrigger.CONSECUTIVE_LOSSES: "连续输牌",
            ReviewTrigger.BIG_LOSS: "大额损失",
            ReviewTrigger.OPPONENT_SHIFT: "对手行为突变",
            ReviewTrigger.PERIODIC: "定期回顾",
        }
        return mapping.get(trigger, trigger.value)

    @staticmethod
    def _try_parse_json(text: str) -> dict | None:
        """尝试从文本中解析 JSON（与 BaseAgent 逻辑一致）"""
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
