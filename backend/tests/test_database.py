"""T4.1 测试: FastAPI 应用启动 + 数据库表创建

验证:
1. 数据库初始化能创建全部 8 张表
2. 各表能正常插入和查询数据
3. 外键关系正确
4. FastAPI 应用能正常启动
5. 健康检查和模型列表 API 正常工作
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base
from app.db.schemas import (
    ChatMessageDB,
    ExperienceReviewDB,
    GameDB,
    GameSummaryDB,
    PlayerDB,
    RoundDB,
    RoundNarrativeDB,
    ThoughtRecordDB,
)
from app.main import app


# ---- Fixtures ----


@pytest_asyncio.fixture
async def async_engine():
    """创建内存 SQLite 异步引擎（测试专用）"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    # 导入 schemas 确保所有模型注册到 Base
    import app.db.schemas  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine):
    """创建测试用异步 session"""
    session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def async_client():
    """创建测试用 HTTP 客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ---- 数据库表创建测试 ----


class TestDatabaseTableCreation:
    """测试数据库表创建"""

    EXPECTED_TABLES = [
        "games",
        "players",
        "rounds",
        "thought_records",
        "chat_messages",
        "experience_reviews",
        "round_narratives",
        "game_summaries",
    ]

    @pytest.mark.asyncio
    async def test_all_tables_created(self, async_engine):
        """验证全部 8 张表被创建"""
        async with async_engine.connect() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        for table in self.EXPECTED_TABLES:
            assert table in table_names, f"表 '{table}' 未创建"

    @pytest.mark.asyncio
    async def test_table_count(self, async_engine):
        """验证表数量为 8"""
        async with async_engine.connect() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        assert len(table_names) == 8, f"期望 8 张表，实际 {len(table_names)}"


# ---- games 表测试 ----


class TestGameDB:
    """测试 games 表"""

    @pytest.mark.asyncio
    async def test_create_game(self, db_session: AsyncSession):
        """能创建游戏记录"""
        game = GameDB(
            id="game-001",
            config={"initial_chips": 1000, "ante": 10, "max_bet": 200, "max_turns": 10},
            status="waiting",
        )
        db_session.add(game)
        await db_session.commit()

        result = await db_session.get(GameDB, "game-001")
        assert result is not None
        assert result.id == "game-001"
        assert result.status == "waiting"
        assert result.config["initial_chips"] == 1000
        assert result.created_at is not None
        assert result.finished_at is None

    @pytest.mark.asyncio
    async def test_game_status_update(self, db_session: AsyncSession):
        """能更新游戏状态"""
        game = GameDB(
            id="game-002",
            config={"initial_chips": 1000},
            status="waiting",
        )
        db_session.add(game)
        await db_session.commit()

        game.status = "playing"
        await db_session.commit()

        result = await db_session.get(GameDB, "game-002")
        assert result is not None
        assert result.status == "playing"


# ---- players 表测试 ----


class TestPlayerDB:
    """测试 players 表"""

    @pytest.mark.asyncio
    async def test_create_human_player(self, db_session: AsyncSession):
        """能创建人类玩家"""
        game = GameDB(id="game-p1", config={}, status="waiting")
        db_session.add(game)
        await db_session.commit()

        player = PlayerDB(
            id="player-001",
            game_id="game-p1",
            name="测试玩家",
            avatar="avatar_1",
            player_type="human",
            initial_chips=1000,
            current_chips=1000,
        )
        db_session.add(player)
        await db_session.commit()

        result = await db_session.get(PlayerDB, "player-001")
        assert result is not None
        assert result.name == "测试玩家"
        assert result.player_type == "human"
        assert result.model_id is None

    @pytest.mark.asyncio
    async def test_create_ai_player(self, db_session: AsyncSession):
        """能创建 AI 玩家"""
        game = GameDB(id="game-p2", config={}, status="waiting")
        db_session.add(game)
        await db_session.commit()

        player = PlayerDB(
            id="ai-001",
            game_id="game-p2",
            name="火焰哥",
            avatar="avatar_2",
            player_type="ai",
            model_id="openai-gpt4o",
            personality="aggressive",
            initial_chips=1000,
            current_chips=950,
        )
        db_session.add(player)
        await db_session.commit()

        result = await db_session.get(PlayerDB, "ai-001")
        assert result is not None
        assert result.player_type == "ai"
        assert result.model_id == "openai-gpt4o"
        assert result.personality == "aggressive"
        assert result.current_chips == 950

    @pytest.mark.asyncio
    async def test_game_players_relationship(self, db_session: AsyncSession):
        """验证 game -> players 关系"""
        game = GameDB(id="game-rel", config={}, status="waiting")
        db_session.add(game)
        await db_session.commit()

        p1 = PlayerDB(
            id="rel-p1",
            game_id="game-rel",
            name="玩家1",
            player_type="human",
            initial_chips=1000,
            current_chips=1000,
        )
        p2 = PlayerDB(
            id="rel-p2",
            game_id="game-rel",
            name="AI-1",
            player_type="ai",
            model_id="openai-gpt4o",
            initial_chips=1000,
            current_chips=1000,
        )
        db_session.add_all([p1, p2])
        await db_session.commit()

        await db_session.refresh(game, ["players"])
        assert len(game.players) == 2


# ---- rounds 表测试 ----


class TestRoundDB:
    """测试 rounds 表"""

    @pytest.mark.asyncio
    async def test_create_round(self, db_session: AsyncSession):
        """能创建局记录"""
        game = GameDB(id="game-r1", config={}, status="playing")
        db_session.add(game)
        await db_session.commit()

        round_record = RoundDB(
            game_id="game-r1",
            round_number=1,
            pot=100,
            winner_id="player-001",
            win_method="弃牌胜出",
            actions=[
                {"player_id": "player-001", "action": "call", "amount": 20},
                {"player_id": "ai-001", "action": "fold"},
            ],
            hands={"player-001": [{"suit": "hearts", "rank": 14}]},
            player_chip_changes={"player-001": 80, "ai-001": -20},
        )
        db_session.add(round_record)
        await db_session.commit()

        result = await db_session.get(RoundDB, round_record.id)
        assert result is not None
        assert result.round_number == 1
        assert result.pot == 100
        assert result.winner_id == "player-001"
        assert len(result.actions) == 2


# ---- thought_records 表测试 ----


class TestThoughtRecordDB:
    """测试 thought_records 表"""

    @pytest.mark.asyncio
    async def test_create_thought_record(self, db_session: AsyncSession):
        """能创建心路历程记录"""
        game = GameDB(id="game-t1", config={}, status="playing")
        db_session.add(game)
        await db_session.commit()

        player = PlayerDB(
            id="ai-t1",
            game_id="game-t1",
            name="AI",
            player_type="ai",
            initial_chips=1000,
            current_chips=1000,
        )
        db_session.add(player)
        await db_session.commit()

        thought = ThoughtRecordDB(
            agent_id="ai-t1",
            game_id="game-t1",
            round_number=1,
            turn_number=1,
            hand_evaluation="一对K，中等牌力",
            opponent_analysis="对手连续加注，可能有大牌",
            chat_analysis="对手说'你们小心点'，语气自信",
            risk_assessment="底池赔率值得跟注",
            decision="call",
            reasoning="虽然牌力一般，但底池赔率值得一跟",
            confidence=0.65,
            emotion="忐忑",
            table_talk="那我跟着看看",
            raw_response='{"action": "call"}',
        )
        db_session.add(thought)
        await db_session.commit()

        result = await db_session.get(ThoughtRecordDB, thought.id)
        assert result is not None
        assert result.decision == "call"
        assert result.confidence == 0.65
        assert result.emotion == "忐忑"
        assert result.table_talk == "那我跟着看看"
        assert result.chat_analysis is not None


# ---- chat_messages 表测试 ----


class TestChatMessageDB:
    """测试 chat_messages 表"""

    @pytest.mark.asyncio
    async def test_create_chat_message(self, db_session: AsyncSession):
        """能创建聊天消息"""
        game = GameDB(id="game-c1", config={}, status="playing")
        db_session.add(game)
        await db_session.commit()

        msg = ChatMessageDB(
            game_id="game-c1",
            round_number=1,
            sender_id="player-001",
            sender_name="测试玩家",
            message_type="player_message",
            content="你们谁敢跟我比？",
        )
        db_session.add(msg)
        await db_session.commit()

        result = await db_session.get(ChatMessageDB, msg.id)
        assert result is not None
        assert result.content == "你们谁敢跟我比？"
        assert result.message_type == "player_message"

    @pytest.mark.asyncio
    async def test_create_action_talk(self, db_session: AsyncSession):
        """能创建行动发言消息"""
        game = GameDB(id="game-c2", config={}, status="playing")
        db_session.add(game)
        await db_session.commit()

        msg = ChatMessageDB(
            game_id="game-c2",
            round_number=1,
            sender_id="ai-001",
            sender_name="火焰哥",
            message_type="action_talk",
            content="加注！我就不信你们跟得起",
            related_action="raise",
        )
        db_session.add(msg)
        await db_session.commit()

        result = await db_session.get(ChatMessageDB, msg.id)
        assert result is not None
        assert result.related_action == "raise"

    @pytest.mark.asyncio
    async def test_create_bystander_react(self, db_session: AsyncSession):
        """能创建旁观插嘴消息"""
        game = GameDB(id="game-c3", config={}, status="playing")
        db_session.add(game)
        await db_session.commit()

        msg = ChatMessageDB(
            game_id="game-c3",
            round_number=1,
            sender_id="ai-002",
            sender_name="稳如山",
            message_type="bystander_react",
            content="别被他吓到了",
            trigger_event="火焰哥加注到80",
            inner_thought="他可能在诈唬",
        )
        db_session.add(msg)
        await db_session.commit()

        result = await db_session.get(ChatMessageDB, msg.id)
        assert result is not None
        assert result.trigger_event == "火焰哥加注到80"
        assert result.inner_thought == "他可能在诈唬"


# ---- experience_reviews 表测试 ----


class TestExperienceReviewDB:
    """测试 experience_reviews 表"""

    @pytest.mark.asyncio
    async def test_create_experience_review(self, db_session: AsyncSession):
        """能创建经验回顾记录"""
        game = GameDB(id="game-e1", config={}, status="playing")
        db_session.add(game)
        await db_session.commit()

        player = PlayerDB(
            id="ai-e1",
            game_id="game-e1",
            name="AI",
            player_type="ai",
            initial_chips=1000,
            current_chips=600,
        )
        db_session.add(player)
        await db_session.commit()

        review = ExperienceReviewDB(
            agent_id="ai-e1",
            game_id="game-e1",
            trigger="consecutive_losses",
            triggered_at_round=5,
            rounds_reviewed=[3, 4, 5],
            self_analysis="最近几局过于保守，错过了好机会",
            opponent_patterns={
                "player-001": "倾向诈唬，弃牌率低",
                "ai-002": "非常保守，只有好牌才跟注",
            },
            strategy_adjustment="适当增加攻击性，对保守对手加压",
            confidence_shift=-0.2,
            strategy_context="最近连续输了2局，需要调整策略...",
        )
        db_session.add(review)
        await db_session.commit()

        result = await db_session.get(ExperienceReviewDB, review.id)
        assert result is not None
        assert result.trigger == "consecutive_losses"
        assert result.rounds_reviewed == [3, 4, 5]
        assert result.confidence_shift == -0.2


# ---- round_narratives 表测试 ----


class TestRoundNarrativeDB:
    """测试 round_narratives 表"""

    @pytest.mark.asyncio
    async def test_create_round_narrative(self, db_session: AsyncSession):
        """能创建局叙事"""
        game = GameDB(id="game-n1", config={}, status="playing")
        db_session.add(game)
        await db_session.commit()

        player = PlayerDB(
            id="ai-n1",
            game_id="game-n1",
            name="AI",
            player_type="ai",
            initial_chips=1000,
            current_chips=1000,
        )
        db_session.add(player)
        await db_session.commit()

        narrative = RoundNarrativeDB(
            agent_id="ai-n1",
            game_id="game-n1",
            round_number=1,
            narrative="这一局我拿到了一对K，心里有底。看到对面连续加注，我选择了稳稳跟住...",
            outcome="以一对K赢得底池120筹码",
        )
        db_session.add(narrative)
        await db_session.commit()

        result = await db_session.get(RoundNarrativeDB, narrative.id)
        assert result is not None
        assert "一对K" in result.narrative
        assert result.outcome is not None


# ---- game_summaries 表测试 ----


class TestGameSummaryDB:
    """测试 game_summaries 表"""

    @pytest.mark.asyncio
    async def test_create_game_summary(self, db_session: AsyncSession):
        """能创建游戏总结"""
        game = GameDB(id="game-s1", config={}, status="finished")
        db_session.add(game)
        await db_session.commit()

        player = PlayerDB(
            id="ai-s1",
            game_id="game-s1",
            name="AI",
            player_type="ai",
            initial_chips=1000,
            current_chips=1200,
        )
        db_session.add(player)
        await db_session.commit()

        summary = GameSummaryDB(
            agent_id="ai-s1",
            game_id="game-s1",
            stats={
                "rounds_played": 10,
                "rounds_won": 4,
                "total_chips_won": 500,
                "total_chips_lost": 300,
                "biggest_win": 200,
                "biggest_loss": 100,
                "fold_rate": 0.3,
            },
            key_moments=["第3局诈唬成功", "第7局判断错误导致大亏"],
            opponent_impressions={
                "player-001": "非常激进，但有时会过于冲动",
            },
            self_reflection="我的风格偏保守，需要在关键时刻更果断",
            chat_strategy_summary="通过示弱引诱对手加注，效果不错",
            learning_journey="从第5局开始意识到需要调整策略",
            narrative_summary="这场游戏让我学到了很多...",
        )
        db_session.add(summary)
        await db_session.commit()

        result = await db_session.get(GameSummaryDB, summary.id)
        assert result is not None
        assert result.stats["rounds_played"] == 10
        assert len(result.key_moments) == 2


# ---- FastAPI 应用测试 ----


class TestFastAPIApp:
    """测试 FastAPI 应用"""

    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient):
        """健康检查端点正常工作"""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "app" in data

    @pytest.mark.asyncio
    async def test_get_models(self, async_client: AsyncClient):
        """获取 AI 模型列表"""
        response = await async_client.get("/api/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0
        # 验证模型包含必要字段
        model = data["models"][0]
        assert "id" in model
        assert "model" in model
        assert "display_name" in model
        assert "provider" in model

    @pytest.mark.asyncio
    async def test_cors_headers(self, async_client: AsyncClient):
        """CORS 配置正确"""
        response = await async_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    @pytest.mark.asyncio
    async def test_openapi_docs(self, async_client: AsyncClient):
        """OpenAPI 文档可访问"""
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Golden Flower Poker AI"


# ---- 跨表关系测试 ----


class TestCrossTableRelationships:
    """测试跨表关系和级联"""

    @pytest.mark.asyncio
    async def test_full_game_data_creation(self, db_session: AsyncSession):
        """完整游戏数据创建（游戏 + 玩家 + 局 + 聊天）"""
        # 创建游戏
        game = GameDB(
            id="game-full",
            config={"initial_chips": 1000, "ante": 10},
            status="playing",
        )
        db_session.add(game)
        await db_session.commit()

        # 创建玩家
        human = PlayerDB(
            id="human-full",
            game_id="game-full",
            name="人类玩家",
            player_type="human",
            initial_chips=1000,
            current_chips=1000,
        )
        ai1 = PlayerDB(
            id="ai-full-1",
            game_id="game-full",
            name="火焰哥",
            player_type="ai",
            model_id="openai-gpt4o",
            personality="aggressive",
            initial_chips=1000,
            current_chips=1000,
        )
        db_session.add_all([human, ai1])
        await db_session.commit()

        # 创建局记录
        round1 = RoundDB(
            game_id="game-full",
            round_number=1,
            pot=60,
            winner_id="human-full",
            win_method="比牌获胜",
        )
        db_session.add(round1)
        await db_session.commit()

        # 创建聊天消息
        msg1 = ChatMessageDB(
            game_id="game-full",
            round_number=1,
            sender_id="human-full",
            sender_name="人类玩家",
            message_type="player_message",
            content="加油！",
        )
        msg2 = ChatMessageDB(
            game_id="game-full",
            round_number=1,
            sender_id="ai-full-1",
            sender_name="火焰哥",
            message_type="bystander_react",
            content="别得意太早！",
        )
        db_session.add_all([msg1, msg2])
        await db_session.commit()

        # 创建心路历程
        thought = ThoughtRecordDB(
            agent_id="ai-full-1",
            game_id="game-full",
            round_number=1,
            turn_number=1,
            decision="call",
            confidence=0.7,
            emotion="紧张",
        )
        db_session.add(thought)
        await db_session.commit()

        # 验证关系
        await db_session.refresh(game, ["players", "rounds", "chat_messages"])
        assert len(game.players) == 2
        assert len(game.rounds) == 1
        assert len(game.chat_messages) == 2

        await db_session.refresh(ai1, ["thought_records"])
        assert len(ai1.thought_records) == 1

    @pytest.mark.asyncio
    async def test_cascade_delete(self, db_session: AsyncSession):
        """级联删除：删除游戏时关联数据一起删除"""
        game = GameDB(id="game-cascade", config={}, status="waiting")
        db_session.add(game)
        await db_session.commit()

        player = PlayerDB(
            id="player-cascade",
            game_id="game-cascade",
            name="测试",
            player_type="human",
            initial_chips=1000,
            current_chips=1000,
        )
        db_session.add(player)
        await db_session.commit()

        msg = ChatMessageDB(
            game_id="game-cascade",
            round_number=1,
            sender_id="player-cascade",
            sender_name="测试",
            message_type="system_message",
            content="游戏开始",
        )
        db_session.add(msg)
        await db_session.commit()

        # 删除游戏
        await db_session.delete(game)
        await db_session.commit()

        # 验证关联数据也被删除
        result = await db_session.get(PlayerDB, "player-cascade")
        assert result is None

        result = await db_session.get(ChatMessageDB, msg.id)
        assert result is None
