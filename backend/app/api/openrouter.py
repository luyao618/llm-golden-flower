"""OpenRouter 模型管理 API 路由

提供端点管理 OpenRouter 的动态模型列表:
- GET    /api/openrouter/models           — 从 OpenRouter API 获取可用模型列表
- GET    /api/openrouter/models/added     — 获取已添加到游戏的 OpenRouter 模型
- POST   /api/openrouter/models           — 添加一个 OpenRouter 模型到游戏
- DELETE /api/openrouter/models/{model_id} — 从游戏中移除一个 OpenRouter 模型
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import (
    add_openrouter_model,
    get_openrouter_models,
    remove_openrouter_model,
)
from app.services.provider_manager import get_provider_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/openrouter", tags=["openrouter"])

# ---- 模型列表缓存 ----
# OpenRouter 有数百个模型，缓存避免频繁调用外部 API
_models_cache: list[dict[str, Any]] = []
_cache_timestamp: float = 0
_CACHE_TTL: float = 300.0  # 缓存 5 分钟


class AddModelRequest(BaseModel):
    """添加 OpenRouter 模型请求体"""

    model_id: str  # OpenRouter 原始模型 ID，如 "openai/gpt-4o"
    display_name: str  # 模型显示名称，如 "GPT-4o"


async def _fetch_openrouter_models(api_key: str) -> list[dict[str, Any]]:
    """从 OpenRouter API 获取可用模型列表

    调用 GET https://openrouter.ai/api/v1/models
    返回精简后的模型信息列表。
    """
    global _models_cache, _cache_timestamp

    # 检查缓存
    now = time.time()
    if _models_cache and (now - _cache_timestamp) < _CACHE_TTL:
        return _models_cache

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
        )

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch models from OpenRouter: HTTP {resp.status_code}",
            )

        data = resp.json()
        raw_models = data.get("data", [])

    # 只保留 text 类的模型（过滤掉 image/audio/embedding 模型）
    models = []
    for m in raw_models:
        model_id = m.get("id", "")
        name = m.get("name", model_id)

        # 过滤：只保留支持 text 输出的模型
        arch = m.get("architecture", {})
        output_modalities = arch.get("output_modalities", [])
        if output_modalities and "text" not in output_modalities:
            continue

        # 获取定价信息
        pricing = m.get("pricing", {})
        prompt_price = pricing.get("prompt", "0")
        completion_price = pricing.get("completion", "0")

        # 获取上下文长度
        context_length = m.get("context_length")

        models.append(
            {
                "id": model_id,
                "name": name,
                "context_length": context_length,
                "pricing": {
                    "prompt": prompt_price,
                    "completion": completion_price,
                },
            }
        )

    # 按 id 排序
    models.sort(key=lambda x: x["id"])

    # 更新缓存
    _models_cache = models
    _cache_timestamp = now

    logger.info("Fetched %d text models from OpenRouter", len(models))
    return models


@router.get("/models")
async def list_openrouter_models():
    """从 OpenRouter API 获取可用模型列表

    需要先配置 OpenRouter API Key。
    返回的列表经过过滤（仅 text 模型），并带有定价信息。
    """
    manager = get_provider_manager()
    api_key = manager.get_key("openrouter")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="OpenRouter API Key not configured",
        )

    models = await _fetch_openrouter_models(api_key)
    return {"models": models, "total": len(models)}


@router.get("/models/added")
async def list_added_models():
    """获取已添加到游戏的 OpenRouter 模型列表"""
    return {"models": get_openrouter_models()}


@router.post("/models")
async def add_model(req: AddModelRequest):
    """添加一个 OpenRouter 模型到游戏可用列表

    添加后该模型将出现在游戏的 AI 对手模型下拉列表中。
    """
    manager = get_provider_manager()
    if not manager.has_key("openrouter"):
        raise HTTPException(
            status_code=400,
            detail="OpenRouter API Key not configured",
        )

    if not req.model_id or not req.model_id.strip():
        raise HTTPException(status_code=400, detail="model_id cannot be empty")
    if not req.display_name or not req.display_name.strip():
        raise HTTPException(status_code=400, detail="display_name cannot be empty")

    model_id = add_openrouter_model(req.model_id.strip(), req.display_name.strip())

    return {
        "message": f"Model added: {req.display_name}",
        "model_id": model_id,
        "openrouter_id": req.model_id,
        "display_name": req.display_name,
    }


@router.delete("/models/{model_id:path}")
async def remove_model(model_id: str):
    """从游戏可用列表中移除一个 OpenRouter 模型

    Args:
        model_id: 应用内 model_id，如 "openrouter-openai-gpt-4o"
    """
    removed = remove_openrouter_model(model_id)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {model_id}",
        )

    return {
        "message": f"Model removed: {model_id}",
        "model_id": model_id,
    }
