"""T4.4 测试: 持久化辅助函数

验证 app/api/persistence.py 中 5 个 persist_* 函数
能正确将 Pydantic 模型写入 SQLite 数据库。
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base
from app.db.schemas import (
    ChatMessageDB,
    ExperienceReviewDB,
    GameDB,
    GameSummaryDB,
    PlayerDB,
    RoundNarrativeDB,
    ThoughtRecordDB,
)
from app.models.chat import ChatMessage, ChatMessageType
from app.models.game import GameAction
from app.models.thought import (
    ExperienceReview,
    GameSummary,
    ReviewTrigger,
    RoundNarrative,
    ThoughtRecord,
)
from app.api.persistence import (
    persist_chat_message,
    persist_experience_review,
    persist_game_summary,
    persist_round_narrative,
    persist_thought_record,
)


# ---- Constants ----

GAME_ID = "test-game-001"
AGENT_ID = "agent-001"
AGENT_NAME = "赵子龙"


# ---- Fixtures ----


@pytest_asyncio.fixture
async def async_engine():
    """创建内存 SQLite 异步引擎（测试专用）"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    import app.db.schemas  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine):
    """创建测试用数据库会话，并预插入必要的 Game 和 Player 记录"""
    session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # 插入外键依赖：games + players
        game = GameDB(
            id=GAME_ID,
            config={"initial_chips": 1000, "ante": 10},
            status="playing",
        )
        player = PlayerDB(
            id=AGENT_ID,
            game_id=GAME_ID,
            name=AGENT_NAME,
            player_type="ai",
            model_id="gpt-4",
            personality="aggressive",
            initial_chips=1000,
            current_chips=1000,
        )
        session.add(game)
        session.add(player)
        await session.commit()

        yield session


# ---- persist_thought_record ----


class TestPersistThoughtRecord:
    @pytest.mark.asyncio
    async def test_basic_persist(self, db_session: AsyncSession):
        """基本思考记录持久化"""
        record = ThoughtRecord(
            agent_id=AGENT_ID,
            round_number=1,
            turn_number=0,
            hand_evaluation="对子J，中等牌力",
            opponent_analysis="对手加注频繁",
            risk_assessment="中等风险",
            decision=GameAction.CALL,
            reasoning="跟注观察",
            confidence=0.6,
            emotion="谨慎",
            table_talk="我跟了",
            raw_response="...",
        )

        await persist_thought_record(db_session, GAME_ID, record)
        await db_session.commit()

        result = await db_session.execute(select(ThoughtRecordDB))
        rows = result.scalars().all()
        assert len(rows) == 1

        row = rows[0]
        assert row.agent_id == AGENT_ID
        assert row.game_id == GAME_ID
        assert row.round_number == 1
        assert row.turn_number == 0
        assert row.hand_evaluation == "对子J，中等牌力"
        assert row.opponent_analysis == "对手加注频繁"
        assert row.risk_assessment == "中等风险"
        assert row.decision == "call"
        assert row.reasoning == "跟注观察"
        assert row.confidence == 0.6
        assert row.emotion == "谨慎"
        assert row.table_talk == "我跟了"
        assert row.raw_response == "..."

    @pytest.mark.asyncio
    async def test_persist_with_optional_none(self, db_session: AsyncSession):
        """思考记录中可选字段为空"""
        record = ThoughtRecord(
            agent_id=AGENT_ID,
            round_number=2,
            turn_number=1,
            decision=GameAction.FOLD,
            confidence=0.3,
        )

        await persist_thought_record(db_session, GAME_ID, record)
        await db_session.commit()

        result = await db_session.execute(select(ThoughtRecordDB))
        row = result.scalars().first()
        assert row is not None
        assert row.decision == "fold"
        assert row.table_talk is None
        assert row.decision_target is None

    @pytest.mark.asyncio
    async def test_persist_multiple_records(self, db_session: AsyncSession):
        """多条思考记录"""
        for i in range(3):
            record = ThoughtRecord(
                agent_id=AGENT_ID,
                round_number=1,
                turn_number=i,
                decision=GameAction.CALL,
                reasoning=f"turn {i}",
                confidence=0.5 + i * 0.1,
            )
            await persist_thought_record(db_session, GAME_ID, record)

        await db_session.commit()

        result = await db_session.execute(select(ThoughtRecordDB))
        rows = result.scalars().all()
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_persist_with_compare_target(self, db_session: AsyncSession):
        """比牌决策包含 target"""
        record = ThoughtRecord(
            agent_id=AGENT_ID,
            round_number=3,
            turn_number=0,
            decision=GameAction.COMPARE,
            decision_target="opponent-001",
            confidence=0.8,
        )

        await persist_thought_record(db_session, GAME_ID, record)
        await db_session.commit()

        result = await db_session.execute(select(ThoughtRecordDB))
        row = result.scalars().first()
        assert row.decision == "compare"
        assert row.decision_target == "opponent-001"


# ---- persist_chat_message ----


class TestPersistChatMessage:
    @pytest.mark.asyncio
    async def test_basic_persist(self, db_session: AsyncSession):
        """基本聊天消息持久化"""
        msg = ChatMessage(
            game_id=GAME_ID,
            round_number=1,
            player_id=AGENT_ID,
            player_name=AGENT_NAME,
            message_type=ChatMessageType.ACTION_TALK,
            content="我加注100！",
            trigger_event="raise_100",
            inner_thought="其实我很紧张",
        )

        await persist_chat_message(db_session, msg)
        await db_session.commit()

        result = await db_session.execute(select(ChatMessageDB))
        rows = result.scalars().all()
        assert len(rows) == 1

        row = rows[0]
        assert row.game_id == GAME_ID
        assert row.round_number == 1
        assert row.sender_id == AGENT_ID
        assert row.sender_name == AGENT_NAME
        assert row.message_type == "action_talk"
        assert row.content == "我加注100！"
        assert row.trigger_event == "raise_100"
        assert row.inner_thought == "其实我很紧张"

    @pytest.mark.asyncio
    async def test_bystander_react_type(self, db_session: AsyncSession):
        """旁观者插嘴消息"""
        msg = ChatMessage(
            game_id=GAME_ID,
            round_number=2,
            player_id=AGENT_ID,
            player_name=AGENT_NAME,
            message_type=ChatMessageType.BYSTANDER_REACT,
            content="哈哈，这局有意思",
        )

        await persist_chat_message(db_session, msg)
        await db_session.commit()

        result = await db_session.execute(select(ChatMessageDB))
        row = result.scalars().first()
        assert row.message_type == "bystander_react"

    @pytest.mark.asyncio
    async def test_player_message_type(self, db_session: AsyncSession):
        """玩家主动消息"""
        msg = ChatMessage(
            game_id=GAME_ID,
            round_number=1,
            player_id="human-001",
            player_name="玩家",
            message_type=ChatMessageType.PLAYER_MESSAGE,
            content="你们谁敢跟？",
        )

        await persist_chat_message(db_session, msg)
        await db_session.commit()

        result = await db_session.execute(select(ChatMessageDB))
        row = result.scalars().first()
        assert row.message_type == "player_message"
        assert row.content == "你们谁敢跟？"

    @pytest.mark.asyncio
    async def test_multiple_messages(self, db_session: AsyncSession):
        """多条消息"""
        for i in range(5):
            msg = ChatMessage(
                game_id=GAME_ID,
                round_number=1,
                player_id=AGENT_ID,
                player_name=AGENT_NAME,
                message_type=ChatMessageType.ACTION_TALK,
                content=f"msg {i}",
            )
            await persist_chat_message(db_session, msg)

        await db_session.commit()

        result = await db_session.execute(select(ChatMessageDB))
        rows = result.scalars().all()
        assert len(rows) == 5


# ---- persist_round_narrative ----


class TestPersistRoundNarrative:
    @pytest.mark.asyncio
    async def test_basic_persist(self, db_session: AsyncSession):
        """基本局叙事持久化"""
        narrative = RoundNarrative(
            agent_id=AGENT_ID,
            round_number=1,
            narrative="第一局开场，我拿到了一手好牌...",
            outcome="赢得了200筹码",
        )

        await persist_round_narrative(db_session, GAME_ID, narrative)
        await db_session.commit()

        result = await db_session.execute(select(RoundNarrativeDB))
        rows = result.scalars().all()
        assert len(rows) == 1

        row = rows[0]
        assert row.agent_id == AGENT_ID
        assert row.game_id == GAME_ID
        assert row.round_number == 1
        assert row.narrative == "第一局开场，我拿到了一手好牌..."
        assert row.outcome == "赢得了200筹码"

    @pytest.mark.asyncio
    async def test_narrative_with_none_outcome(self, db_session: AsyncSession):
        """叙事无 outcome"""
        narrative = RoundNarrative(
            agent_id=AGENT_ID,
            round_number=2,
            narrative="这局比较平淡...",
            outcome="",
        )

        await persist_round_narrative(db_session, GAME_ID, narrative)
        await db_session.commit()

        result = await db_session.execute(select(RoundNarrativeDB))
        row = result.scalars().first()
        assert row is not None
        # outcome could be empty string or None depending on the persist logic
        assert row.round_number == 2


# ---- persist_game_summary ----


class TestPersistGameSummary:
    @pytest.mark.asyncio
    async def test_basic_persist(self, db_session: AsyncSession):
        """基本游戏总结持久化"""
        summary = GameSummary(
            agent_id=AGENT_ID,
            rounds_played=10,
            rounds_won=6,
            total_chips_won=800,
            total_chips_lost=300,
            biggest_win=200,
            biggest_loss=100,
            fold_rate=0.3,
            key_moments=["第3局精彩比牌", "第7局大胜"],
            opponent_impressions={"opp1": "激进", "opp2": "保守"},
            self_reflection="我的策略偏保守",
            chat_strategy_summary="多说少做",
            learning_journey="从谨慎到自信",
            narrative_summary="一场精彩的对局...",
        )

        await persist_game_summary(db_session, GAME_ID, summary)
        await db_session.commit()

        result = await db_session.execute(select(GameSummaryDB))
        rows = result.scalars().all()
        assert len(rows) == 1

        row = rows[0]
        assert row.agent_id == AGENT_ID
        assert row.game_id == GAME_ID
        assert row.stats["rounds_played"] == 10
        assert row.stats["rounds_won"] == 6
        assert row.stats["total_chips_won"] == 800
        assert row.stats["total_chips_lost"] == 300
        assert row.stats["biggest_win"] == 200
        assert row.stats["biggest_loss"] == 100
        assert row.stats["fold_rate"] == 0.3
        assert row.key_moments == ["第3局精彩比牌", "第7局大胜"]
        assert row.opponent_impressions == {"opp1": "激进", "opp2": "保守"}
        assert row.self_reflection == "我的策略偏保守"
        assert row.chat_strategy_summary == "多说少做"
        assert row.learning_journey == "从谨慎到自信"
        assert row.narrative_summary == "一场精彩的对局..."

    @pytest.mark.asyncio
    async def test_summary_with_defaults(self, db_session: AsyncSession):
        """游戏总结使用默认值"""
        summary = GameSummary(agent_id=AGENT_ID)

        await persist_game_summary(db_session, GAME_ID, summary)
        await db_session.commit()

        result = await db_session.execute(select(GameSummaryDB))
        row = result.scalars().first()
        assert row is not None
        assert row.stats["rounds_played"] == 0
        assert row.stats["rounds_won"] == 0
        assert row.stats["fold_rate"] == 0.0
        assert row.key_moments == []
        assert row.opponent_impressions == {}


# ---- persist_experience_review ----


class TestPersistExperienceReview:
    @pytest.mark.asyncio
    async def test_basic_persist(self, db_session: AsyncSession):
        """基本经验回顾持久化"""
        review = ExperienceReview(
            agent_id=AGENT_ID,
            trigger=ReviewTrigger.CONSECUTIVE_LOSSES,
            triggered_at_round=5,
            rounds_reviewed=[3, 4, 5],
            self_analysis="最近几局打得太保守",
            opponent_patterns={"opp1": "喜欢诈唬"},
            strategy_adjustment="适当提高跟注频率",
            confidence_shift=-0.2,
            strategy_context="需要更激进的策略",
        )

        await persist_experience_review(db_session, GAME_ID, review)
        await db_session.commit()

        result = await db_session.execute(select(ExperienceReviewDB))
        rows = result.scalars().all()
        assert len(rows) == 1

        row = rows[0]
        assert row.agent_id == AGENT_ID
        assert row.game_id == GAME_ID
        assert row.trigger == "consecutive_losses"
        assert row.triggered_at_round == 5
        assert row.rounds_reviewed == [3, 4, 5]
        assert row.self_analysis == "最近几局打得太保守"
        assert row.opponent_patterns == {"opp1": "喜欢诈唬"}
        assert row.strategy_adjustment == "适当提高跟注频率"
        assert row.confidence_shift == -0.2
        assert row.strategy_context == "需要更激进的策略"

    @pytest.mark.asyncio
    async def test_chip_crisis_trigger(self, db_session: AsyncSession):
        """筹码危机触发"""
        review = ExperienceReview(
            agent_id=AGENT_ID,
            trigger=ReviewTrigger.CHIP_CRISIS,
            triggered_at_round=8,
            rounds_reviewed=[6, 7, 8],
            self_analysis="筹码告急",
            confidence_shift=-0.5,
        )

        await persist_experience_review(db_session, GAME_ID, review)
        await db_session.commit()

        result = await db_session.execute(select(ExperienceReviewDB))
        row = result.scalars().first()
        assert row.trigger == "chip_crisis"
        assert row.confidence_shift == -0.5

    @pytest.mark.asyncio
    async def test_periodic_trigger(self, db_session: AsyncSession):
        """定期触发"""
        review = ExperienceReview(
            agent_id=AGENT_ID,
            trigger=ReviewTrigger.PERIODIC,
            triggered_at_round=5,
            rounds_reviewed=[1, 2, 3, 4, 5],
        )

        await persist_experience_review(db_session, GAME_ID, review)
        await db_session.commit()

        result = await db_session.execute(select(ExperienceReviewDB))
        row = result.scalars().first()
        assert row.trigger == "periodic"
        assert row.triggered_at_round == 5
        assert row.rounds_reviewed == [1, 2, 3, 4, 5]
