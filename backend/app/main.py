"""FastAPI 应用入口

配置 CORS、注册路由、管理应用生命周期（数据库初始化/关闭）。
启动命令: uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.database import close_db, init_db
from app.logging_config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理

    启动时初始化数据库（创建表），关闭时释放连接。
    """
    # 启动时
    await init_db()
    logger.info("数据库已初始化")
    yield
    # 关闭时
    await close_db()
    logger.info("数据库连接已关闭")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例"""
    settings = get_settings()

    # ---- 初始化日志系统（必须在所有其他操作之前） ----
    setup_logging(
        log_level=settings.log_level,
        debug=settings.debug,
    )
    logger.info("应用启动 — %s (debug=%s)", settings.app_name, settings.debug)

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

    # ---- HTTP 请求日志中间件 ----
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """记录每个 HTTP 请求的方法、路径、耗时和状态码"""
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        # 跳过健康检查的日志（避免噪音）
        if request.url.path != "/health":
            logger.info(
                "%s %s -> %d (%.1fms)",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

        return response

    # ---- 全局未捕获异常处理 ----
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """捕获所有未处理的异常，记录完整堆栈并返回 500"""
        logger.error(
            "未捕获异常: %s %s -> %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请查看日志获取详情"},
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

        return get_available_models()

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

    # T8.0: 模型配置中心 — Provider + Copilot + 各 Provider 模型管理路由
    from app.api.provider import router as provider_router
    from app.api.copilot import router as copilot_router
    from app.api.openrouter import router as openrouter_router
    from app.api.siliconflow import router as siliconflow_router
    from app.api.azure_openai import router as azure_openai_router
    from app.api.zhipu import router as zhipu_router

    app.include_router(provider_router)  # prefix already set in router
    app.include_router(copilot_router)  # prefix already set in router
    app.include_router(openrouter_router)  # prefix already set in router
    app.include_router(siliconflow_router)  # prefix already set in router
    app.include_router(azure_openai_router)  # prefix already set in router
    app.include_router(zhipu_router)  # prefix already set in router

    # 游戏设置路由
    from app.api.settings import router as settings_router

    app.include_router(settings_router)  # prefix already set in router

    logger.info("所有路由已注册")

    return app


# 创建全局应用实例
app = create_app()
