"""全局测试配置与共享 Fixtures

提供:
1. pytest 标记配置（integration 标记自动跳过逻辑）
2. 数据库 fixtures（async_engine, db_session, async_client）
3. 工厂函数（make_card, make_player, make_agent, make_game_state）
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents.base_agent import BaseAgent
from app.api.game_store import reset_game_store
from app.db.database import Base, get_db
from app.main import create_app
from app.models.card import Card, Rank, Suit
from app.models.game import (
    ActionRecord,
    GameAction,
    GameConfig,
    GamePhase,
    GameState,
    Player,
    PlayerStatus,
    PlayerType,
    RoundState,
)
from app.models.thought import ThoughtRecord

# ============================================================
# pytest 钩子：integration 标记默认跳过
# ============================================================


def pytest_collection_modifyitems(config, items):
    """未指定 -m integration 时，自动跳过 integration 标记的测试"""
    # 如果命令行显式指定了 -m 表达式且包含 integration，则不跳过
    markexpr = config.getoption("-m", default="")
    if "integration" in markexpr:
        return

    skip_integration = pytest.mark.skip(
        reason="需要 -m integration 才会运行（需设置 API Key 环境变量）"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


# ============================================================
# 数据库 Fixtures
# ============================================================


@pytest_asyncio.fixture
async def async_engine():
    """创建内存 SQLite 异步引擎（测试专用）

    - 自动创建全部数据库表
    - 测试结束后删除所有表并释放引擎
    """
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
    """创建测试用异步数据库会话（无预填充数据）"""
    session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def db_session_factory(async_engine):
    """返回 session 工厂，用于需要多次创建会话的场景"""
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def async_client(async_engine):
    """创建测试用 HTTP 客户端

    - 覆盖数据库依赖为内存 SQLite
    - 模拟 Copilot 认证已连接
    - 测试结束后清理 game_store 和依赖覆盖
    """
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

    test_app = create_app()
    test_app.dependency_overrides[get_db] = _override_get_db

    # 模拟 Copilot 认证已连接
    mock_copilot = MagicMock()
    mock_copilot.is_connected = True

    transport = ASGITransport(app=test_app)
    with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_copilot):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    reset_game_store()
    test_app.dependency_overrides.clear()


# ============================================================
# 工厂函数
# ============================================================


def make_card(rank: Rank, suit: Suit = Suit.SPADES) -> Card:
    """快速创建一张牌

    Args:
        rank: 牌面大小
        suit: 花色，默认黑桃
    """
    return Card(suit=suit, rank=rank)


def make_player(
    name: str = "玩家1",
    player_id: str = "",
    chips: int = 1000,
    status: PlayerStatus = PlayerStatus.ACTIVE_BLIND,
    player_type: PlayerType = PlayerType.AI,
    hand: list[Card] | None = None,
    total_bet: int = 0,
) -> Player:
    """快速创建一个玩家

    Args:
        name: 玩家名称
        player_id: 玩家 ID，为空时自动生成 "player-{name}"
        chips: 筹码数
        status: 玩家状态
        player_type: 玩家类型（人类/AI）
        hand: 手牌
        total_bet: 本轮总下注额
    """
    return Player(
        id=player_id or f"player-{name}",
        name=name,
        player_type=player_type,
        chips=chips,
        status=status,
        hand=hand,
        total_bet_this_round=total_bet,
    )


def make_agent(
    agent_id: str = "agent-1",
    name: str = "测试选手",
    model_id: str = "copilot-gpt4o-mini",
) -> BaseAgent:
    """快速创建测试用 BaseAgent

    Args:
        agent_id: Agent 唯一标识
        name: Agent 名称
        model_id: 使用的 LLM 模型 ID
    """
    return BaseAgent(
        agent_id=agent_id,
        name=name,
        model_id=model_id,
    )


def make_game_state(
    players: list[Player] | None = None,
    round_number: int = 1,
    pot: int = 30,
    current_bet: int = 10,
    current_player_index: int = 0,
    phase: GamePhase = GamePhase.BETTING,
    actions: list[ActionRecord] | None = None,
    game_id: str = "test-game",
) -> GameState:
    """快速创建一个游戏状态

    Args:
        players: 玩家列表，为空时自动创建 3 人（含手牌）
        round_number: 局数
        pot: 底池
        current_bet: 当前下注额
        current_player_index: 当前玩家索引
        phase: 游戏阶段
        actions: 操作记录列表
        game_id: 游戏 ID
    """
    if players is None:
        hand_p1 = [
            make_card(Rank.KING, Suit.HEARTS),
            make_card(Rank.KING, Suit.SPADES),
            make_card(Rank.THREE, Suit.DIAMONDS),
        ]
        hand_p2 = [
            make_card(Rank.ACE, Suit.CLUBS),
            make_card(Rank.ACE, Suit.HEARTS),
            make_card(Rank.SEVEN, Suit.SPADES),
        ]
        hand_p3 = [
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SIX, Suit.CLUBS),
            make_card(Rank.SEVEN, Suit.HEARTS),
        ]
        players = [
            make_player("玩家A", "p1", hand=hand_p1, status=PlayerStatus.ACTIVE_SEEN, total_bet=10),
            make_player("玩家B", "p2", hand=hand_p2, total_bet=10),
            make_player("玩家C", "p3", hand=hand_p3, total_bet=10),
        ]

    round_state = RoundState(
        round_number=round_number,
        pot=pot,
        current_bet=current_bet,
        dealer_index=0,
        current_player_index=current_player_index,
        phase=phase,
        actions=actions or [],
    )

    return GameState(
        game_id=game_id,
        players=players,
        current_round=round_state,
        config=GameConfig(),
        status="playing",
    )


def make_thought_record(
    agent_id: str = "agent-1",
    round_number: int = 1,
    turn_number: int = 1,
    decision: GameAction = GameAction.CALL,
    confidence: float = 0.6,
    hand_evaluation: str = "中等牌力",
    reasoning: str = "跟注观察",
) -> ThoughtRecord:
    """快速创建测试用思考记录

    Args:
        agent_id: Agent ID
        round_number: 局数
        turn_number: 回合数
        decision: 决策动作
        confidence: 信心值
        hand_evaluation: 手牌评估
        reasoning: 决策理由
    """
    return ThoughtRecord(
        agent_id=agent_id,
        round_number=round_number,
        turn_number=turn_number,
        hand_evaluation=hand_evaluation,
        opponent_analysis="对手表现正常",
        risk_assessment="中等风险",
        decision=decision,
        reasoning=reasoning,
        confidence=confidence,
        emotion="平静",
        table_talk="嗯...",
        raw_response="{}",
    )
