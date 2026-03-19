"""智谱 (Zhipu / GLM) 模型管理 API 路由

提供端点管理智谱的动态模型列表:
- GET    /api/zhipu/models           — 从智谱 API 获取可用模型列表
- GET    /api/zhipu/models/added     — 获取已添加到游戏的智谱模型
- POST   /api/zhipu/models           — 添加一个智谱模型到游戏
- DELETE /api/zhipu/models/{model_id} — 从游戏中移除一个智谱模型
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.config import (
    add_zhipu_model,
    get_zhipu_models,
    remove_zhipu_model,
)
from app.services.provider_manager import get_provider_manager, parse_provider_keys_header

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/zhipu", tags=["zhipu"])

# ---- 模型列表缓存 ----
_models_cache: list[dict[str, Any]] = []
_cache_timestamp: float = 0
_CACHE_TTL: float = 300.0  # 缓存 5 分钟


class AddModelRequest(BaseModel):
    """添加智谱模型请求体"""

    model_id: str  # 智谱原始模型 ID，如 "glm-4-flash"
    display_name: str  # 模型显示名称


async def _fetch_zhipu_models(api_key: str) -> list[dict[str, Any]]:
    """从智谱 API 获取可用模型列表

    调用 GET /models（兼容 OpenAI 格式）
    """
    global _models_cache, _cache_timestamp

    # 检查缓存
    now = time.time()
    if _models_cache and (now - _cache_timestamp) < _CACHE_TTL:
        return _models_cache

    manager = get_provider_manager()
    extra = manager.get_extra_config("zhipu")
    api_host = extra.get("api_host", "https://open.bigmodel.cn/api/paas/v4")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{api_host.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
        )

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch models from Zhipu: HTTP {resp.status_code}",
            )

        data = resp.json()
        raw_models = data.get("data", [])

    # 过滤：只保留 chat 类型的模型（去掉 embedding/image/video 等）
    models = []
    for m in raw_models:
        model_id = m.get("id", "")
        id_lower = model_id.lower()
        skip_keywords = [
            "embed",
            "image",
            "video",
            "cogview",
            "cogvideo",
            "charglm",
            "emohaa",
        ]
        if any(kw in id_lower for kw in skip_keywords):
            continue

        models.append(
            {
                "id": model_id,
                "name": model_id,
                "context_length": None,
                "pricing": {"prompt": "0", "completion": "0"},
            }
        )

    # 按 id 排序
    models.sort(key=lambda x: x["id"])

    # 更新缓存
    _models_cache = models
    _cache_timestamp = now

    logger.info("Fetched %d chat models from Zhipu", len(models))
    return models


@router.get("/models")
async def list_zhipu_models(request: Request):
    """从智谱 API 获取可用模型列表"""
    api_keys = parse_provider_keys_header(request.headers.get("X-Provider-Keys"))
    api_key = api_keys.get("zhipu")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Zhipu API Key not configured",
        )

    models = await _fetch_zhipu_models(api_key)
    return {"models": models, "total": len(models)}


@router.get("/models/added")
async def list_added_models():
    """获取已添加到游戏的智谱模型列表"""
    return {"models": get_zhipu_models()}


@router.post("/models")
async def add_model(req: AddModelRequest):
    """添加一个智谱模型到游戏可用列表

    注意：不再检查 API Key 是否已配置，模型注册与 Key 无关。
    Key 在实际 LLM 调用时由前端通过 WebSocket 传入。
    """
    if not req.model_id or not req.model_id.strip():
        raise HTTPException(status_code=400, detail="model_id cannot be empty")
    if not req.display_name or not req.display_name.strip():
        raise HTTPException(status_code=400, detail="display_name cannot be empty")

    model_id = add_zhipu_model(req.model_id.strip(), req.display_name.strip())

    return {
        "message": f"Model added: {req.display_name}",
        "model_id": model_id,
        "zhipu_id": req.model_id,
        "display_name": req.display_name,
    }


@router.delete("/models/{model_id:path}")
async def remove_model(model_id: str):
    """从游戏可用列表中移除一个智谱模型"""
    removed = remove_zhipu_model(model_id)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {model_id}",
        )

    return {
        "message": f"Model removed: {model_id}",
        "model_id": model_id,
    }
