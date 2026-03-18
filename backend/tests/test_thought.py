"""T2.5 单元测试: ThoughtRecorder + ThoughtReporter + 数据模型

测试覆盖:
- ThoughtRecord / RoundNarrative / GameSummary 数据模型
- ThoughtRecorder: append_thought, get_round_thoughts, format
- ThoughtReporter: generate_round_narrative, generate_game_summary (mock LLM)
- 容错: JSON 解析失败降级, LLM 调用失败降级
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from app.agents.base_agent import BaseAgent, Decision, ThoughtData
from app.models.game import GameAction
from app.models.thought import GameSummary, RoundNarrative, ThoughtRecord
from app.thought.recorder import ThoughtRecorder
from app.thought.reporter import ThoughtReporter


# ============================================================
# 数据模型测试
# ============================================================


class TestThoughtRecord:
    """ThoughtRecord 模型测试"""

    def test_default_values(self):
        record = ThoughtRecord(agent_id="agent-1", round_number=1)
        assert record.agent_id == "agent-1"
        assert record.round_number == 1
        assert record.turn_number == 0
        assert record.decision == GameAction.FOLD
        assert record.confidence == 0.5
        assert record.emotion == "平静"
        assert record.hand_evaluation == ""
        assert record.decision_target is None
        assert record.table_talk is None
        assert record.raw_response == ""

    def test_full_construction(self):
        record = ThoughtRecord(
            agent_id="agent-2",
            round_number=3,
            turn_number=2,
            hand_evaluation="一对K，牌力不错",
            opponent_analysis="对手比较保守",
            risk_assessment="风险中等",
            chat_analysis="对手说自己很自信，可能是虚张声势",
            decision=GameAction.RAISE,
            decision_target=None,
            reasoning="手牌不错，加注试探",
            confidence=0.75,
            emotion="自信",
            table_talk="来吧，加注！",
            raw_response='{"action": "raise"}',
        )
        assert record.decision == GameAction.RAISE
        assert record.confidence == 0.75
        assert record.table_talk == "来吧，加注！"
        assert record.chat_analysis == "对手说自己很自信，可能是虚张声势"

    def test_confidence_clamped(self):
        """confidence 字段应在 0-1 范围内"""
        record = ThoughtRecord(agent_id="a", round_number=1, confidence=0.0)
        assert record.confidence == 0.0

        record = ThoughtRecord(agent_id="a", round_number=1, confidence=1.0)
        assert record.confidence == 1.0

        with pytest.raises(Exception):
            ThoughtRecord(agent_id="a", round_number=1, confidence=1.5)

        with pytest.raises(Exception):
            ThoughtRecord(agent_id="a", round_number=1, confidence=-0.1)

    def test_serialization(self):
        """测试序列化和反序列化"""
        record = ThoughtRecord(
            agent_id="agent-1",
            round_number=1,
            decision=GameAction.CALL,
            confidence=0.8,
            emotion="紧张",
        )
        data = record.model_dump()
        assert data["agent_id"] == "agent-1"
        assert data["decision"] == "call"
        assert data["confidence"] == 0.8

        # 反序列化
        restored = ThoughtRecord.model_validate(data)
        assert restored.decision == GameAction.CALL
        assert restored.emotion == "紧张"


class TestRoundNarrative:
    """RoundNarrative 模型测试"""

    def test_construction(self):
        narrative = RoundNarrative(
            agent_id="agent-1",
            round_number=2,
            narrative="这一局我拿到了一对A...",
            outcome="赢得底池 200 筹码",
        )
        assert narrative.agent_id == "agent-1"
        assert narrative.round_number == 2
        assert "一对A" in narrative.narrative
        assert "200" in narrative.outcome


class TestGameSummary:
    """GameSummary 模型测试"""

    def test_default_values(self):
        summary = GameSummary(agent_id="agent-1")
        assert summary.rounds_played == 0
        assert summary.key_moments == []
        assert summary.opponent_impressions == {}
        assert summary.narrative_summary == ""

    def test_full_construction(self):
        summary = GameSummary(
            agent_id="agent-1",
            rounds_played=10,
            rounds_won=4,
            total_chips_won=500,
            total_chips_lost=300,
            biggest_win=200,
            biggest_loss=100,
            fold_rate=0.3,
            key_moments=["第3局豹子翻盘", "第7局大胆加注"],
            opponent_impressions={"player-2": "非常激进", "player-3": "比较保守"},
            self_reflection="我偏向保守打法",
            chat_strategy_summary="主要用施压策略",
            learning_journey="第5局后开始更大胆",
            narrative_summary="这是一场精彩的游戏...",
        )
        assert summary.rounds_won == 4
        assert len(summary.key_moments) == 2
        assert summary.opponent_impressions["player-2"] == "非常激进"


# ============================================================
# ThoughtRecorder 测试
# ============================================================


class TestThoughtRecorder:
    """ThoughtRecorder 测试"""

    def test_init(self):
        recorder = ThoughtRecorder(agent_id="agent-1")
        assert recorder.agent_id == "agent-1"
        assert recorder.records == {}

    def test_append_thought_basic(self):
        recorder = ThoughtRecorder(agent_id="agent-1")
        td = ThoughtData(
            hand_evaluation="一对K",
            opponent_analysis="对手保守",
            reasoning="跟注观察",
            confidence=0.6,
            emotion="平静",
        )
        dec = Decision(
            action=GameAction.CALL,
            table_talk="我跟",
            raw_response='{"action":"call"}',
        )

        record = recorder.append_thought(
            round_number=1,
            thought_data=td,
            decision=dec,
            turn_number=1,
        )

        assert isinstance(record, ThoughtRecord)
        assert record.agent_id == "agent-1"
        assert record.round_number == 1
        assert record.turn_number == 1
        assert record.hand_evaluation == "一对K"
        assert record.decision == GameAction.CALL
        assert record.table_talk == "我跟"
        assert record.confidence == 0.6

    def test_append_thought_no_decision(self):
        """没有 Decision 时应使用默认值"""
        recorder = ThoughtRecorder(agent_id="agent-1")
        td = ThoughtData(reasoning="思考中")

        record = recorder.append_thought(round_number=1, thought_data=td)

        assert record.decision == GameAction.FOLD
        assert record.decision_target is None
        assert record.table_talk is None
        assert record.raw_response == ""

    def test_append_thought_no_thought_data(self):
        """没有 ThoughtData 时应使用默认值"""
        recorder = ThoughtRecorder(agent_id="agent-1")
        dec = Decision(action=GameAction.RAISE, raw_response="raw")

        record = recorder.append_thought(round_number=1, decision=dec)

        assert record.hand_evaluation == ""
        assert record.decision == GameAction.RAISE
        assert record.confidence == 0.5

    def test_get_round_thoughts(self):
        recorder = ThoughtRecorder(agent_id="agent-1")

        # Round 1: 2 thoughts
        recorder.append_thought(
            round_number=1,
            thought_data=ThoughtData(reasoning="first"),
            decision=Decision(action=GameAction.CALL),
            turn_number=1,
        )
        recorder.append_thought(
            round_number=1,
            thought_data=ThoughtData(reasoning="second"),
            decision=Decision(action=GameAction.RAISE),
            turn_number=2,
        )

        # Round 2: 1 thought
        recorder.append_thought(
            round_number=2,
            thought_data=ThoughtData(reasoning="third"),
            decision=Decision(action=GameAction.FOLD),
            turn_number=1,
        )

        r1_thoughts = recorder.get_round_thoughts(1)
        assert len(r1_thoughts) == 2
        assert r1_thoughts[0].reasoning == "first"
        assert r1_thoughts[1].reasoning == "second"

        r2_thoughts = recorder.get_round_thoughts(2)
        assert len(r2_thoughts) == 1
        assert r2_thoughts[0].decision == GameAction.FOLD

        # Non-existent round
        assert recorder.get_round_thoughts(99) == []

    def test_get_all_thoughts(self):
        recorder = ThoughtRecorder(agent_id="agent-1")
        recorder.append_thought(round_number=1, decision=Decision(action=GameAction.CALL))
        recorder.append_thought(round_number=2, decision=Decision(action=GameAction.FOLD))

        all_thoughts = recorder.get_all_thoughts()
        assert 1 in all_thoughts
        assert 2 in all_thoughts

    def test_get_all_thoughts_flat(self):
        recorder = ThoughtRecorder(agent_id="agent-1")
        recorder.append_thought(
            round_number=2, decision=Decision(action=GameAction.FOLD), turn_number=1
        )
        recorder.append_thought(
            round_number=1, decision=Decision(action=GameAction.CALL), turn_number=1
        )
        recorder.append_thought(
            round_number=1, decision=Decision(action=GameAction.RAISE), turn_number=2
        )

        flat = recorder.get_all_thoughts_flat()
        assert len(flat) == 3
        # Should be sorted by round number
        assert flat[0].round_number == 1
        assert flat[1].round_number == 1
        assert flat[2].round_number == 2

    def test_clear(self):
        recorder = ThoughtRecorder(agent_id="agent-1")
        recorder.append_thought(round_number=1, decision=Decision(action=GameAction.CALL))
        assert len(recorder.records) == 1
        recorder.clear()
        assert len(recorder.records) == 0

    def test_format_round_thoughts_for_prompt(self):
        recorder = ThoughtRecorder(agent_id="agent-1")
        recorder.append_thought(
            round_number=1,
            thought_data=ThoughtData(
                hand_evaluation="一对K",
                opponent_analysis="对手保守",
                reasoning="跟注试探",
                confidence=0.7,
                emotion="自信",
                chat_analysis="对手说了大话",
            ),
            decision=Decision(
                action=GameAction.CALL,
                table_talk="我跟你",
            ),
            turn_number=1,
        )

        text = recorder.format_round_thoughts_for_prompt(1)
        assert "第 1 次决策（call）" in text
        assert "一对K" in text
        assert "对手保守" in text
        assert "对手说了大话" in text
        assert "跟注试探" in text
        assert "70%" in text
        assert "自信" in text
        assert "我跟你" in text

    def test_format_empty_round(self):
        recorder = ThoughtRecorder(agent_id="agent-1")
        text = recorder.format_round_thoughts_for_prompt(99)
        assert "无思考记录" in text


# ============================================================
# ThoughtReporter 测试
# ============================================================


def _make_agent(agent_id: str = "agent-1", name: str = "测试选手") -> BaseAgent:
    """创建测试用 Agent"""
    return BaseAgent(
        agent_id=agent_id,
        name=name,
        model_id="copilot-gpt4o-mini",
    )


def _make_thoughts(count: int = 2) -> list[ThoughtRecord]:
    """创建测试用思考记录"""
    records = []
    for i in range(count):
        records.append(
            ThoughtRecord(
                agent_id="agent-1",
                round_number=1,
                turn_number=i + 1,
                hand_evaluation=f"评估{i + 1}",
                reasoning=f"理由{i + 1}",
                decision=GameAction.CALL if i == 0 else GameAction.RAISE,
                confidence=0.5 + i * 0.1,
                emotion="平静" if i == 0 else "自信",
            )
        )
    return records


class TestThoughtReporter:
    """ThoughtReporter 测试（LLM 调用使用 mock）"""

    @pytest.mark.asyncio
    async def test_generate_round_narrative_success(self):
        """正常 LLM 调用返回有效 JSON"""
        agent = _make_agent()
        reporter = ThoughtReporter(agent)

        llm_response = json.dumps(
            {
                "narrative": "这一局我拿到一对K，心中暗喜...",
                "outcome": "赢得底池 150 筹码",
            }
        )

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=llm_response):
            narrative = await reporter.generate_round_narrative(
                round_number=1,
                round_thoughts=_make_thoughts(),
                chat_messages="张三: 我牌很好\n李四: 我不信",
                action_history="1. 张三 跟注\n2. 李四 加注",
                hand_description="红心K, 黑桃K, 方块3（一对K）",
                round_outcome="赢得底池 150 筹码",
            )

        assert isinstance(narrative, RoundNarrative)
        assert narrative.agent_id == "agent-1"
        assert narrative.round_number == 1
        assert "一对K" in narrative.narrative
        assert "150" in narrative.outcome

    @pytest.mark.asyncio
    async def test_generate_round_narrative_json_parse_failure(self):
        """LLM 返回非 JSON 文本时的降级"""
        agent = _make_agent()
        reporter = ThoughtReporter(agent)

        with patch.object(
            agent,
            "call_llm",
            new_callable=AsyncMock,
            return_value="这是一段非 JSON 的叙事文本...",
        ):
            narrative = await reporter.generate_round_narrative(
                round_number=1,
                round_thoughts=_make_thoughts(),
                chat_messages="",
                action_history="",
                hand_description="散牌",
                round_outcome="输了",
            )

        assert isinstance(narrative, RoundNarrative)
        assert "非 JSON" in narrative.narrative
        assert narrative.outcome == "输了"

    @pytest.mark.asyncio
    async def test_generate_round_narrative_llm_failure(self):
        """LLM 调用失败时的降级叙事"""
        agent = _make_agent()
        reporter = ThoughtReporter(agent)

        thoughts = _make_thoughts(1)
        thoughts[0].hand_evaluation = "散牌"
        thoughts[0].reasoning = "弃牌保筹码"

        with patch.object(
            agent,
            "call_llm",
            new_callable=AsyncMock,
            side_effect=Exception("API error"),
        ):
            narrative = await reporter.generate_round_narrative(
                round_number=3,
                round_thoughts=thoughts,
                chat_messages="",
                action_history="",
                hand_description="散牌",
                round_outcome="弃牌退出",
            )

        assert isinstance(narrative, RoundNarrative)
        assert narrative.round_number == 3
        # 降级叙事应包含基本信息
        assert "3" in narrative.narrative
        assert narrative.outcome == "弃牌退出"

    @pytest.mark.asyncio
    async def test_generate_game_summary_success(self):
        """正常 LLM 调用返回有效 JSON"""
        agent = _make_agent()
        reporter = ThoughtReporter(agent)

        llm_response = json.dumps(
            {
                "key_moments": ["第3局豹子翻盘", "第7局大胆加注"],
                "opponent_impressions": {"player-2": "激进型选手"},
                "self_reflection": "我偏保守",
                "chat_strategy_summary": "施压为主",
                "learning_journey": "后半场调整了策略",
                "narrative_summary": "这是一场精彩的对决...",
            }
        )

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=llm_response):
            summary = await reporter.generate_game_summary(
                rounds_played=10,
                rounds_won=4,
                total_chips_won=500,
                total_chips_lost=300,
                biggest_win=200,
                biggest_loss=100,
                fold_rate="30%",
                all_narratives="第1局: ...\n第2局: ...",
                all_reviews="（无经验回顾）",
                opponents_info="player-2: 激进\nplayer-3: 保守",
            )

        assert isinstance(summary, GameSummary)
        assert summary.agent_id == "agent-1"
        assert summary.rounds_played == 10
        assert summary.rounds_won == 4
        assert summary.fold_rate == pytest.approx(0.3)
        assert len(summary.key_moments) == 2
        assert "player-2" in summary.opponent_impressions
        assert "精彩" in summary.narrative_summary

    @pytest.mark.asyncio
    async def test_generate_game_summary_llm_failure(self):
        """LLM 调用失败时返回降级 summary"""
        agent = _make_agent()
        reporter = ThoughtReporter(agent)

        with patch.object(
            agent,
            "call_llm",
            new_callable=AsyncMock,
            side_effect=Exception("LLM timeout"),
        ):
            summary = await reporter.generate_game_summary(
                rounds_played=5,
                rounds_won=2,
                total_chips_won=200,
                total_chips_lost=100,
                biggest_win=100,
                biggest_loss=50,
                fold_rate="40%",
                all_narratives="",
                all_reviews="",
                opponents_info="",
            )

        assert isinstance(summary, GameSummary)
        assert summary.rounds_played == 5
        assert "失败" in summary.narrative_summary

    @pytest.mark.asyncio
    async def test_generate_round_narrative_markdown_json(self):
        """LLM 返回 markdown 代码块包裹的 JSON"""
        agent = _make_agent()
        reporter = ThoughtReporter(agent)

        llm_response = '```json\n{"narrative": "精彩的一局！", "outcome": "赢了"}\n```'

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=llm_response):
            narrative = await reporter.generate_round_narrative(
                round_number=1,
                round_thoughts=[],
                chat_messages="",
                action_history="",
                hand_description="同花顺",
                round_outcome="赢了",
            )

        assert narrative.narrative == "精彩的一局！"
        assert narrative.outcome == "赢了"


class TestThoughtReporterHelpers:
    """ThoughtReporter 静态辅助方法测试"""

    def test_format_thoughts_empty(self):
        text = ThoughtReporter._format_thoughts([])
        assert "无思考记录" in text

    def test_format_thoughts_with_records(self):
        thoughts = _make_thoughts(2)
        thoughts[0].table_talk = "说点什么"
        text = ThoughtReporter._format_thoughts(thoughts)
        assert "第 1 次决策" in text
        assert "第 2 次决策" in text
        assert "说点什么" in text

    def test_build_fallback_narrative_empty(self):
        text = ThoughtReporter._build_fallback_narrative(5, [], "弃牌退出")
        assert "第 5 局" in text
        assert "弃牌退出" in text

    def test_build_fallback_narrative_with_thoughts(self):
        thoughts = _make_thoughts(1)
        thoughts[0].hand_evaluation = "散牌"
        thoughts[0].reasoning = "没希望了"
        text = ThoughtReporter._build_fallback_narrative(3, thoughts, "输了")
        assert "散牌" in text
        assert "没希望了" in text
        assert "输了" in text

    def test_parse_fold_rate(self):
        assert ThoughtReporter._parse_fold_rate("40%") == pytest.approx(0.4)
        assert ThoughtReporter._parse_fold_rate("0%") == pytest.approx(0.0)
        assert ThoughtReporter._parse_fold_rate("100%") == pytest.approx(1.0)
        assert ThoughtReporter._parse_fold_rate("33.3%") == pytest.approx(0.333)
        assert ThoughtReporter._parse_fold_rate("invalid") == 0.0
        assert ThoughtReporter._parse_fold_rate("") == 0.0

    def test_try_parse_json_valid(self):
        result = ThoughtReporter._try_parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_try_parse_json_markdown(self):
        result = ThoughtReporter._try_parse_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_try_parse_json_invalid(self):
        result = ThoughtReporter._try_parse_json("this is not json at all")
        assert result is None
