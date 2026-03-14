"""SiliconFlow 模型管理 API 路由

提供端点管理 SiliconFlow 的动态模型列表:
- GET    /api/siliconflow/models           — 从 SiliconFlow API 获取可用模型列表
- GET    /api/siliconflow/models/added     — 获取已添加到游戏的 SiliconFlow 模型
- POST   /api/siliconflow/models           — 添加一个 SiliconFlow 模型到游戏
- DELETE /api/siliconflow/models/{model_id} — 从游戏中移除一个 SiliconFlow 模型
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import (
    add_siliconflow_model,
    get_siliconflow_models,
    remove_siliconflow_model,
)
from app.services.provider_manager import get_provider_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/siliconflow", tags=["siliconflow"])

# ---- 模型列表缓存 ----
_models_cache: list[dict[str, Any]] = []
_cache_timestamp: float = 0
_CACHE_TTL: float = 300.0  # 缓存 5 分钟


class AddModelRequest(BaseModel):
    """添加 SiliconFlow 模型请求体"""

    model_id: str  # SiliconFlow 原始模型 ID，如 "deepseek-ai/DeepSeek-V3"
    display_name: str  # 模型显示名称


async def _fetch_siliconflow_models(api_key: str) -> list[dict[str, Any]]:
    """从 SiliconFlow API 获取可用模型列表

    调用 GET /v1/models（兼容 OpenAI 格式）
    """
    global _models_cache, _cache_timestamp

    # 检查缓存
    now = time.time()
    if _models_cache and (now - _cache_timestamp) < _CACHE_TTL:
        return _models_cache

    manager = get_provider_manager()
    extra = manager.get_extra_config("siliconflow")
    api_host = extra.get("api_host", "https://api.siliconflow.cn")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{api_host.rstrip('/')}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
        )

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch models from SiliconFlow: HTTP {resp.status_code}",
            )

        data = resp.json()
        raw_models = data.get("data", [])

    # 过滤：只保留 chat 类型的模型（去掉 embedding/audio/image 等）
    models = []
    for m in raw_models:
        model_id = m.get("id", "")
        # SiliconFlow 返回的模型格式：id 就是模型名
        # 过滤掉 embedding、reranker、image、audio、video 类的模型
        id_lower = model_id.lower()
        skip_keywords = [
            "embed",
            "rerank",
            "image",
            "audio",
            "video",
            "tts",
            "whisper",
            "stable-diffusion",
            "flux",
            "vae",
        ]
        if any(kw in id_lower for kw in skip_keywords):
            continue

        models.append(
            {
                "id": model_id,
                "name": model_id,  # SiliconFlow 的 id 就是显示名
                "context_length": None,
                "pricing": {"prompt": "0", "completion": "0"},
            }
        )

    # 按 id 排序
    models.sort(key=lambda x: x["id"])

    # 更新缓存
    _models_cache = models
    _cache_timestamp = now

    logger.info("Fetched %d chat models from SiliconFlow", len(models))
    return models


@router.get("/models")
async def list_siliconflow_models():
    """从 SiliconFlow API 获取可用模型列表"""
    manager = get_provider_manager()
    api_key = manager.get_key("siliconflow")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="SiliconFlow API Key not configured",
        )

    models = await _fetch_siliconflow_models(api_key)
    return {"models": models, "total": len(models)}


@router.get("/models/added")
async def list_added_models():
    """获取已添加到游戏的 SiliconFlow 模型列表"""
    return {"models": get_siliconflow_models()}


@router.post("/models")
async def add_model(req: AddModelRequest):
    """添加一个 SiliconFlow 模型到游戏可用列表"""
    manager = get_provider_manager()
    if not manager.has_key("siliconflow"):
        raise HTTPException(
            status_code=400,
            detail="SiliconFlow API Key not configured",
        )

    if not req.model_id or not req.model_id.strip():
        raise HTTPException(status_code=400, detail="model_id cannot be empty")
    if not req.display_name or not req.display_name.strip():
        raise HTTPException(status_code=400, detail="display_name cannot be empty")

    model_id = add_siliconflow_model(req.model_id.strip(), req.display_name.strip())

    return {
        "message": f"Model added: {req.display_name}",
        "model_id": model_id,
        "siliconflow_id": req.model_id,
        "display_name": req.display_name,
    }


@router.delete("/models/{model_id:path}")
async def remove_model(model_id: str):
    """从游戏可用列表中移除一个 SiliconFlow 模型"""
    removed = remove_siliconflow_model(model_id)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {model_id}",
        )

    return {
        "message": f"Model removed: {model_id}",
        "model_id": model_id,
    }
