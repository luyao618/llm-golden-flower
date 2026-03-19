"""Azure OpenAI 模型管理 API 路由

提供端点管理 Azure OpenAI 的动态模型列表:
- GET    /api/azure-openai/models           — 从 Azure OpenAI 获取已部署的模型列表
- GET    /api/azure-openai/models/added     — 获取已添加到游戏的 Azure OpenAI 模型
- POST   /api/azure-openai/models           — 添加一个 Azure OpenAI 模型到游戏
- DELETE /api/azure-openai/models/{model_id} — 从游戏中移除一个 Azure OpenAI 模型
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.config import (
    add_azure_openai_model,
    get_azure_openai_models,
    remove_azure_openai_model,
)
from app.services.provider_manager import get_provider_manager, parse_provider_keys_header

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/azure-openai", tags=["azure-openai"])

# ---- 模型列表缓存 ----
_models_cache: list[dict[str, Any]] = []
_cache_timestamp: float = 0
_CACHE_TTL: float = 300.0  # 缓存 5 分钟


class AddModelRequest(BaseModel):
    """添加 Azure OpenAI 模型请求体"""

    model_id: str  # Azure 部署名称，如 "gpt-4o"
    display_name: str  # 模型显示名称


async def _fetch_azure_models(api_key: str) -> list[dict[str, Any]]:
    """从 Azure OpenAI 获取已部署的模型列表

    调用 GET {endpoint}/openai/models?api-version=...
    """
    global _models_cache, _cache_timestamp

    # 检查缓存
    now = time.time()
    if _models_cache and (now - _cache_timestamp) < _CACHE_TTL:
        return _models_cache

    manager = get_provider_manager()
    extra = manager.get_extra_config("azure_openai")
    api_host = extra.get("api_host", "")
    api_version = extra.get("api_version", "2024-10-21")

    if not api_host:
        raise HTTPException(
            status_code=400,
            detail="Azure OpenAI API Host (endpoint) not configured",
        )

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{api_host.rstrip('/')}/openai/models?api-version={api_version}",
            headers={"api-key": api_key},
            timeout=15.0,
        )

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch models from Azure OpenAI: HTTP {resp.status_code}",
            )

        data = resp.json()
        raw_models = data.get("data", [])

    models = []
    for m in raw_models:
        model_id = m.get("id", "")
        # Azure OpenAI 返回部署的模型名
        models.append(
            {
                "id": model_id,
                "name": model_id,
                "context_length": None,
                "pricing": {"prompt": "0", "completion": "0"},
            }
        )

    models.sort(key=lambda x: x["id"])

    _models_cache = models
    _cache_timestamp = now

    logger.info("Fetched %d models from Azure OpenAI", len(models))
    return models


@router.get("/models")
async def list_azure_models(request: Request):
    """从 Azure OpenAI 获取已部署的模型列表"""
    api_keys = parse_provider_keys_header(request.headers.get("X-Provider-Keys"))
    api_key = api_keys.get("azure_openai")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Azure OpenAI API Key not configured",
        )

    models = await _fetch_azure_models(api_key)
    return {"models": models, "total": len(models)}


@router.get("/models/added")
async def list_added_models():
    """获取已添加到游戏的 Azure OpenAI 模型列表"""
    return {"models": get_azure_openai_models()}


@router.post("/models")
async def add_model(req: AddModelRequest):
    """添加一个 Azure OpenAI 模型到游戏可用列表

    注意：不再检查 API Key 是否已配置，模型注册与 Key 无关。
    Key 在实际 LLM 调用时由前端通过 WebSocket 传入。
    """
    if not req.model_id or not req.model_id.strip():
        raise HTTPException(status_code=400, detail="model_id cannot be empty")
    if not req.display_name or not req.display_name.strip():
        raise HTTPException(status_code=400, detail="display_name cannot be empty")

    model_id = add_azure_openai_model(req.model_id.strip(), req.display_name.strip())

    return {
        "message": f"Model added: {req.display_name}",
        "model_id": model_id,
        "azure_id": req.model_id,
        "display_name": req.display_name,
    }


@router.delete("/models/{model_id:path}")
async def remove_model(model_id: str):
    """从游戏可用列表中移除一个 Azure OpenAI 模型"""
    removed = remove_azure_openai_model(model_id)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {model_id}",
        )

    return {
        "message": f"Model removed: {model_id}",
        "model_id": model_id,
    }
