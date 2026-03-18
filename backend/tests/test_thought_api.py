"""T4.4 测试: 心路历程 REST API

验证:
1. GET /{game_id}/thoughts/{agent_id}                    所有思考记录
2. GET /{game_id}/thoughts/{agent_id}/round/{round_num}  某局思考记录
3. GET /{game_id}/narrative/{agent_id}/round/{round_num}  局叙事
4. GET /{game_id}/summary/{agent_id}                     游戏总结
5. GET /{game_id}/reviews/{agent_id}                     经验回顾列表
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.game_store import reset_game_store
from app.db.database import get_db
from app.db.schemas import (
    ExperienceReviewDB,
    GameDB,
    GameSummaryDB,
    PlayerDB,
    RoundNarrativeDB,
    ThoughtRecordDB,
)
from app.main import create_app

# async_engine fixture 由 conftest.py 提供


# ---- Constants ----

GAME_ID = "thought-test-game"
AGENT_ID = "thought-test-agent"
AGENT_NAME = "测试AI"


# ---- Fixtures ----


@pytest_asyncio.fixture
async def async_client(async_engine):
    """创建测试用 HTTP 客户端，预插入 Game + Player（覆盖 conftest 版本）"""
    test_session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _override_get_db():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    # 预插入外键依赖数据
    async with test_session_factory() as session:
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
            initial_chips=1000,
            current_chips=1000,
        )
        session.add(game)
        session.add(player)
        await session.commit()

    test_app = create_app()
    test_app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    reset_game_store()
    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_client(async_engine):
    """创建预填充了思考记录、叙事、总结、经验回顾数据的测试客户端"""
    test_session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _override_get_db():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    # 预插入外键依赖 + 测试数据
    async with test_session_factory() as session:
        game = GameDB(
            id=GAME_ID,
            config={"initial_chips": 1000},
            status="playing",
        )
        player = PlayerDB(
            id=AGENT_ID,
            game_id=GAME_ID,
            name=AGENT_NAME,
            player_type="ai",
            model_id="gpt-4",
            initial_chips=1000,
            current_chips=1000,
        )
        session.add(game)
        session.add(player)
        await session.flush()

        # 思考记录：3条（round 1 有2条，round 2 有1条）
        session.add(
            ThoughtRecordDB(
                agent_id=AGENT_ID,
                game_id=GAME_ID,
                round_number=1,
                turn_number=0,
                hand_evaluation="好牌",
                decision="call",
                reasoning="跟注",
                confidence=0.7,
                emotion="自信",
            )
        )
        session.add(
            ThoughtRecordDB(
                agent_id=AGENT_ID,
                game_id=GAME_ID,
                round_number=1,
                turn_number=1,
                hand_evaluation="好牌",
                decision="raise",
                reasoning="加注",
                confidence=0.8,
                emotion="兴奋",
            )
        )
        session.add(
            ThoughtRecordDB(
                agent_id=AGENT_ID,
                game_id=GAME_ID,
                round_number=2,
                turn_number=0,
                hand_evaluation="差牌",
                decision="fold",
                reasoning="弃牌保命",
                confidence=0.3,
                emotion="紧张",
            )
        )

        # 局叙事
        session.add(
            RoundNarrativeDB(
                agent_id=AGENT_ID,
                game_id=GAME_ID,
                round_number=1,
                narrative="第一局我拿到好牌，一路加注...",
                outcome="赢得200筹码",
            )
        )

        # 游戏总结
        session.add(
            GameSummaryDB(
                agent_id=AGENT_ID,
                game_id=GAME_ID,
                stats={"rounds_played": 5, "rounds_won": 3, "fold_rate": 0.2},
                key_moments=["第1局大胜", "第3局翻盘"],
                opponent_impressions={"opp1": "很激进"},
                self_reflection="整体发挥不错",
                narrative_summary="一场精彩对局...",
            )
        )

        # 经验回顾：2条
        session.add(
            ExperienceReviewDB(
                agent_id=AGENT_ID,
                game_id=GAME_ID,
                trigger="consecutive_losses",
                triggered_at_round=3,
                rounds_reviewed=[1, 2, 3],
                self_analysis="最近太保守了",
                strategy_adjustment="加大进攻",
                confidence_shift=-0.1,
            )
        )
        session.add(
            ExperienceReviewDB(
                agent_id=AGENT_ID,
                game_id=GAME_ID,
                trigger="periodic",
                triggered_at_round=5,
                rounds_reviewed=[1, 2, 3, 4, 5],
                self_analysis="整体稳定",
                confidence_shift=0.1,
            )
        )

        await session.commit()

    test_app = create_app()
    test_app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    reset_game_store()
    test_app.dependency_overrides.clear()


# ---- GET /thoughts/{agent_id} ----


class TestGetAgentThoughts:
    @pytest.mark.asyncio
    async def test_get_all_thoughts(self, seeded_client: AsyncClient):
        """获取 AI 的所有思考记录"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/thoughts/{AGENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_id"] == GAME_ID
        assert data["agent_id"] == AGENT_ID
        assert data["count"] == 3
        assert len(data["thoughts"]) == 3

        # 验证按 round_number, turn_number 排序
        thoughts = data["thoughts"]
        assert thoughts[0]["round_number"] == 1
        assert thoughts[0]["turn_number"] == 0
        assert thoughts[1]["round_number"] == 1
        assert thoughts[1]["turn_number"] == 1
        assert thoughts[2]["round_number"] == 2
        assert thoughts[2]["turn_number"] == 0

    @pytest.mark.asyncio
    async def test_get_thoughts_empty(self, async_client: AsyncClient):
        """没有思考记录时返回空列表"""
        resp = await async_client.get(f"/api/game/{GAME_ID}/thoughts/{AGENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["thoughts"] == []

    @pytest.mark.asyncio
    async def test_get_thoughts_nonexistent_game(self, async_client: AsyncClient):
        """不存在的游戏返回空列表（不是404）"""
        resp = await async_client.get("/api/game/nonexistent/thoughts/some-agent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0


# ---- GET /thoughts/{agent_id}/round/{round_num} ----


class TestGetAgentRoundThoughts:
    @pytest.mark.asyncio
    async def test_get_round_thoughts(self, seeded_client: AsyncClient):
        """获取某局的思考记录"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/thoughts/{AGENT_ID}/round/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["round_number"] == 1
        assert data["count"] == 2
        assert len(data["thoughts"]) == 2

        # 按 turn_number 排序
        assert data["thoughts"][0]["turn_number"] == 0
        assert data["thoughts"][1]["turn_number"] == 1

    @pytest.mark.asyncio
    async def test_get_round_thoughts_single(self, seeded_client: AsyncClient):
        """只有一条记录的局"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/thoughts/{AGENT_ID}/round/2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["thoughts"][0]["decision"] == "fold"

    @pytest.mark.asyncio
    async def test_get_round_thoughts_empty(self, seeded_client: AsyncClient):
        """不存在的局号返回空"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/thoughts/{AGENT_ID}/round/99")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_thought_record_fields(self, seeded_client: AsyncClient):
        """验证思考记录各字段正确返回"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/thoughts/{AGENT_ID}/round/1")
        data = resp.json()
        thought = data["thoughts"][0]

        assert "id" in thought
        assert thought["agent_id"] == AGENT_ID
        assert thought["game_id"] == GAME_ID
        assert thought["hand_evaluation"] == "好牌"
        assert thought["decision"] == "call"
        assert thought["reasoning"] == "跟注"
        assert thought["confidence"] == 0.7
        assert thought["emotion"] == "自信"


# ---- GET /narrative/{agent_id}/round/{round_num} ----


class TestGetRoundNarrative:
    @pytest.mark.asyncio
    async def test_get_narrative(self, seeded_client: AsyncClient):
        """获取局叙事"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/narrative/{AGENT_ID}/round/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == AGENT_ID
        assert data["game_id"] == GAME_ID
        assert data["round_number"] == 1
        assert "第一局" in data["narrative"]
        assert data["outcome"] == "赢得200筹码"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_narrative_not_found(self, seeded_client: AsyncClient):
        """不存在的叙事返回 404"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/narrative/{AGENT_ID}/round/99")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_narrative_wrong_agent(self, seeded_client: AsyncClient):
        """错误 agent_id 返回 404"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/narrative/wrong-agent/round/1")
        assert resp.status_code == 404


# ---- GET /summary/{agent_id} ----


class TestGetGameSummary:
    @pytest.mark.asyncio
    async def test_get_summary(self, seeded_client: AsyncClient):
        """获取游戏总结"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/summary/{AGENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == AGENT_ID
        assert data["game_id"] == GAME_ID
        assert data["stats"]["rounds_played"] == 5
        assert data["stats"]["rounds_won"] == 3
        assert data["stats"]["fold_rate"] == 0.2
        assert data["key_moments"] == ["第1局大胜", "第3局翻盘"]
        assert data["opponent_impressions"] == {"opp1": "很激进"}
        assert data["self_reflection"] == "整体发挥不错"
        assert data["narrative_summary"] == "一场精彩对局..."

    @pytest.mark.asyncio
    async def test_summary_not_found(self, seeded_client: AsyncClient):
        """不存在的总结返回 404"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/summary/wrong-agent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_summary_wrong_game(self, async_client: AsyncClient):
        """不存在的游戏返回 404"""
        resp = await async_client.get("/api/game/nonexistent/summary/some-agent")
        assert resp.status_code == 404


# ---- GET /reviews/{agent_id} ----


class TestGetExperienceReviews:
    @pytest.mark.asyncio
    async def test_get_reviews(self, seeded_client: AsyncClient):
        """获取经验回顾列表"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/reviews/{AGENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_id"] == GAME_ID
        assert data["agent_id"] == AGENT_ID
        assert data["count"] == 2
        assert len(data["reviews"]) == 2

        # 按 triggered_at_round 排序
        reviews = data["reviews"]
        assert reviews[0]["triggered_at_round"] == 3
        assert reviews[0]["trigger"] == "consecutive_losses"
        assert reviews[1]["triggered_at_round"] == 5
        assert reviews[1]["trigger"] == "periodic"

    @pytest.mark.asyncio
    async def test_review_fields(self, seeded_client: AsyncClient):
        """验证经验回顾字段"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/reviews/{AGENT_ID}")
        data = resp.json()
        review = data["reviews"][0]

        assert review["rounds_reviewed"] == [1, 2, 3]
        assert review["self_analysis"] == "最近太保守了"
        assert review["strategy_adjustment"] == "加大进攻"
        assert review["confidence_shift"] == -0.1

    @pytest.mark.asyncio
    async def test_reviews_empty(self, async_client: AsyncClient):
        """没有经验回顾返回空列表"""
        resp = await async_client.get(f"/api/game/{GAME_ID}/reviews/{AGENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["reviews"] == []
