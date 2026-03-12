"""T4.4 测试: 聊天记录 REST API

验证:
1. GET /{game_id}/chat                    所有聊天记录
2. GET /{game_id}/chat/round/{round_num}  某局聊天记录
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.game_store import reset_game_store
from app.db.database import Base, get_db
from app.db.schemas import ChatMessageDB, GameDB, PlayerDB
from app.main import create_app


# ---- Constants ----

GAME_ID = "chat-test-game"
AGENT_ID = "chat-test-agent"
AGENT_NAME = "测试AI"
HUMAN_ID = "chat-test-human"
HUMAN_NAME = "玩家"


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
async def async_client(async_engine):
    """创建测试用 HTTP 客户端（无预填充数据）"""
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

    # 预插入外键依赖
    async with test_session_factory() as session:
        game = GameDB(
            id=GAME_ID,
            config={"initial_chips": 1000},
            status="playing",
        )
        session.add(game)
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
    """创建预填充了聊天消息数据的测试客户端"""
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

    # 预插入外键依赖 + 测试消息
    async with test_session_factory() as session:
        game = GameDB(
            id=GAME_ID,
            config={"initial_chips": 1000},
            status="playing",
        )
        session.add(game)
        await session.flush()

        # Round 1: 3条消息
        session.add(
            ChatMessageDB(
                game_id=GAME_ID,
                round_number=1,
                sender_id=AGENT_ID,
                sender_name=AGENT_NAME,
                message_type="action_talk",
                content="我跟注！",
            )
        )
        session.add(
            ChatMessageDB(
                game_id=GAME_ID,
                round_number=1,
                sender_id=HUMAN_ID,
                sender_name=HUMAN_NAME,
                message_type="player_message",
                content="你敢跟？",
            )
        )
        session.add(
            ChatMessageDB(
                game_id=GAME_ID,
                round_number=1,
                sender_id=AGENT_ID,
                sender_name=AGENT_NAME,
                message_type="bystander_react",
                content="哈哈有意思",
                trigger_event="human raised 100",
                inner_thought="他在虚张声势",
            )
        )

        # Round 2: 2条消息
        session.add(
            ChatMessageDB(
                game_id=GAME_ID,
                round_number=2,
                sender_id=AGENT_ID,
                sender_name=AGENT_NAME,
                message_type="action_talk",
                content="加注200！",
            )
        )
        session.add(
            ChatMessageDB(
                game_id=GAME_ID,
                round_number=2,
                sender_id=HUMAN_ID,
                sender_name=HUMAN_NAME,
                message_type="player_message",
                content="弃了弃了",
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


# ---- GET /chat ----


class TestGetGameChat:
    @pytest.mark.asyncio
    async def test_get_all_chat(self, seeded_client: AsyncClient):
        """获取所有聊天记录"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/chat")
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_id"] == GAME_ID
        assert data["round_number"] is None
        assert data["count"] == 5
        assert len(data["messages"]) == 5

    @pytest.mark.asyncio
    async def test_chat_empty(self, async_client: AsyncClient):
        """没有聊天记录返回空列表"""
        resp = await async_client.get(f"/api/game/{GAME_ID}/chat")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["messages"] == []

    @pytest.mark.asyncio
    async def test_chat_nonexistent_game(self, async_client: AsyncClient):
        """不存在的游戏返回空列表"""
        resp = await async_client.get("/api/game/nonexistent/chat")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_chat_message_fields(self, seeded_client: AsyncClient):
        """验证聊天消息各字段正确返回"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/chat")
        data = resp.json()

        # 找到 bystander_react 类型的消息
        bystander_msgs = [m for m in data["messages"] if m["message_type"] == "bystander_react"]
        assert len(bystander_msgs) == 1

        msg = bystander_msgs[0]
        assert msg["game_id"] == GAME_ID
        assert msg["round_number"] == 1
        assert msg["sender_id"] == AGENT_ID
        assert msg["sender_name"] == AGENT_NAME
        assert msg["content"] == "哈哈有意思"
        assert msg["trigger_event"] == "human raised 100"
        assert msg["inner_thought"] == "他在虚张声势"
        assert "id" in msg

    @pytest.mark.asyncio
    async def test_chat_contains_all_types(self, seeded_client: AsyncClient):
        """验证包含各种消息类型"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/chat")
        data = resp.json()
        types = {m["message_type"] for m in data["messages"]}
        assert "action_talk" in types
        assert "player_message" in types
        assert "bystander_react" in types


# ---- GET /chat/round/{round_num} ----


class TestGetRoundChat:
    @pytest.mark.asyncio
    async def test_get_round_chat(self, seeded_client: AsyncClient):
        """获取某局聊天记录"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/chat/round/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_id"] == GAME_ID
        assert data["round_number"] == 1
        assert data["count"] == 3
        assert len(data["messages"]) == 3

    @pytest.mark.asyncio
    async def test_get_round_chat_round2(self, seeded_client: AsyncClient):
        """获取第2局聊天记录"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/chat/round/2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["round_number"] == 2
        assert data["count"] == 2

    @pytest.mark.asyncio
    async def test_round_chat_empty(self, seeded_client: AsyncClient):
        """不存在的局号返回空"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/chat/round/99")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["messages"] == []

    @pytest.mark.asyncio
    async def test_round_chat_only_contains_round_messages(self, seeded_client: AsyncClient):
        """确保只返回指定局的消息"""
        resp = await seeded_client.get(f"/api/game/{GAME_ID}/chat/round/1")
        data = resp.json()
        for msg in data["messages"]:
            assert msg["round_number"] == 1
