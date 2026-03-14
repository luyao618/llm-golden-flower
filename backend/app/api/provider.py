"""Provider / API Key 管理 API 路由

提供端点管理各 LLM Provider 的 API Key 和配置:
- GET    /api/providers                       — 获取所有 Provider 状态
- POST   /api/providers/{provider}/key        — 设置 API Key
- POST   /api/providers/{provider}/verify     — 验证 API Key 有效性
- DELETE /api/providers/{provider}/key        — 移除 API Key
- POST   /api/providers/{provider}/config     — 设置额外配置 (api_host, api_version)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.provider_manager import get_provider_manager, PROVIDERS

router = APIRouter(prefix="/api/providers", tags=["providers"])


class SetKeyRequest(BaseModel):
    """设置 API Key 请求体"""

    key: str


class VerifyKeyRequest(BaseModel):
    """验证 API Key 请求体（可选传入 key）"""

    key: str | None = None


class SetExtraConfigRequest(BaseModel):
    """设置额外配置请求体"""

    api_host: str | None = None
    api_version: str | None = None


@router.get("")
async def get_providers():
    """获取所有 Provider 的连接状态

    Returns:
        各 Provider 的状态列表，包含:
        - provider: Provider ID
        - name: 显示名称
        - configured: 是否已配置 API Key
        - key_preview: 遮盖后的 Key 预览
        - extra_config: 额外配置 (api_host, api_version 等)
    """
    manager = get_provider_manager()
    return manager.get_all_status()


@router.post("/{provider}/key")
async def set_provider_key(provider: str, req: SetKeyRequest):
    """设置某个 Provider 的 API Key

    设置后该 Provider 的模型将出现在可用模型列表中。
    """
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    if not req.key or not req.key.strip():
        raise HTTPException(status_code=400, detail="API Key cannot be empty")

    manager = get_provider_manager()
    manager.set_key(provider, req.key.strip())

    return {
        "message": f"API Key set for {PROVIDERS[provider]['name']}",
        "provider": provider,
        "configured": True,
    }


@router.post("/{provider}/verify")
async def verify_provider_key(provider: str, req: VerifyKeyRequest):
    """验证某个 Provider 的 API Key 有效性

    可以传入 key 验证，也可以不传验证已配置的 key。

    Returns:
        valid: 是否有效
        message: 验证结果消息
    """
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    manager = get_provider_manager()
    result = await manager.verify_key(provider, req.key)
    return result


@router.delete("/{provider}/key")
async def remove_provider_key(provider: str):
    """移除某个 Provider 的 API Key

    移除后该 Provider 的模型将从可用模型列表中消失。
    """
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    manager = get_provider_manager()
    manager.remove_key(provider)

    return {
        "message": f"API Key removed for {PROVIDERS[provider]['name']}",
        "provider": provider,
        "configured": False,
    }


@router.post("/{provider}/config")
async def set_provider_config(provider: str, req: SetExtraConfigRequest):
    """设置 Provider 的额外配置（api_host, api_version 等）

    用于 Azure OpenAI（需要 endpoint + api_version）和 SiliconFlow（可自定义 api_host）。
    """
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    manager = get_provider_manager()
    config = {}
    if req.api_host is not None:
        config["api_host"] = req.api_host.strip()
    if req.api_version is not None:
        config["api_version"] = req.api_version.strip()

    if not config:
        raise HTTPException(status_code=400, detail="No config provided")

    manager.set_extra_config(provider, config)

    return {
        "message": f"Config updated for {PROVIDERS[provider]['name']}",
        "provider": provider,
        "extra_config": manager.get_extra_config(provider),
    }
