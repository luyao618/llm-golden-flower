"""数据库连接管理

使用 SQLAlchemy 异步引擎 + aiosqlite 驱动管理 SQLite 数据库连接。
提供 async session 工厂和数据库生命周期管理函数。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类

    所有 ORM 模型都继承此基类，用于统一元数据管理和表创建。
    """

    pass


# 全局引擎和 session 工厂（延迟初始化）
_engine = None
_async_session_factory = None


def _get_engine():
    """获取或创建异步数据库引擎（单例）"""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            # SQLite 特定配置
            connect_args={"check_same_thread": False},
        )
    return _engine


def _get_session_factory():
    """获取或创建 async session 工厂（单例）"""
    global _async_session_factory
    if _async_session_factory is None:
        engine = _get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库 session

    用法::

        @app.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...

    Yields:
        AsyncSession: 数据库会话，请求结束后自动关闭
    """
    session_factory = _get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库：创建所有表

    在应用启动时调用，确保所有 ORM 模型对应的表已创建。
    需要在调用前确保 schemas 模块已导入（以注册所有模型到 Base.metadata）。
    """
    # 确保 schemas 模块已导入，使所有 ORM 模型注册到 Base.metadata
    import app.db.schemas  # noqa: F401

    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接

    在应用关闭时调用，释放数据库引擎资源。
    """
    global _engine, _async_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None


def reset_engine() -> None:
    """重置引擎（仅用于测试）

    在测试中切换数据库 URL 后调用，强制重新创建引擎。
    """
    global _engine, _async_session_factory
    _engine = None
    _async_session_factory = None
