"""FastAPI 应用入口

配置 CORS、注册路由、管理应用生命周期（数据库初始化/关闭）。
启动命令: uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理

    启动时初始化数据库（创建表），关闭时释放连接。
    """
    # 启动时
    await init_db()
    yield
    # 关闭时
    await close_db()


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="炸金花 AI 对战平台 — 多 LLM 模型驱动的智能扑克游戏",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ---- CORS 配置 ----
    # 开发阶段允许所有来源，生产环境应限制为前端域名
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- 注册路由 ----
    # 健康检查端点
    @app.get("/health", tags=["system"])
    async def health_check():
        """健康检查"""
        return {"status": "ok", "app": settings.app_name}

    @app.get("/api/models", tags=["config"])
    async def get_models():
        """获取可用的 AI 模型列表"""
        from app.config import get_available_models

        return {"models": get_available_models()}

    # T4.2: 游戏管理路由
    from app.api.game import router as game_router

    app.include_router(game_router, prefix="/api/game", tags=["game"])

    # T4.3: WebSocket 路由
    from app.api.websocket import router as ws_router

    app.include_router(ws_router, tags=["websocket"])

    # T4.4: 心路历程和聊天路由
    from app.api.thought import router as thought_router
    from app.api.chat import router as chat_router

    app.include_router(thought_router, prefix="/api/game", tags=["thought"])
    app.include_router(chat_router, prefix="/api/game", tags=["chat"])

    return app


# 创建全局应用实例
app = create_app()
