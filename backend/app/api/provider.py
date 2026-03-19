"""Provider / API Key 管理 API 路由

提供端点管理各 LLM Provider 的配置:
- GET    /api/providers                       — 获取所有 Provider 状态
- POST   /api/providers/{provider}/verify     — 验证 API Key 有效性
- POST   /api/providers/{provider}/config     — 设置额外配置 (api_host, api_version)

注意: API Key 的存储/移除已迁移到前端 localStorage，
后端通过 X-Provider-Keys header 获取当前用户的 keys。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.provider_manager import (
    get_provider_manager,
    parse_provider_keys_header,
    PROVIDERS,
)

router = APIRouter(prefix="/api/providers", tags=["providers"])


class VerifyKeyRequest(BaseModel):
    """验证 API Key 请求体（可选传入 key）"""

    key: str | None = None


class SetExtraConfigRequest(BaseModel):
    """设置额外配置请求体"""

    api_host: str | None = None
    api_version: str | None = None


@router.get("")
async def get_providers(request: Request):
    """获取所有 Provider 的连接状态

    API Key 从 X-Provider-Keys header 中读取（来自前端 localStorage）。

    Returns:
        各 Provider 的状态列表，包含:
        - provider: Provider ID
        - name: 显示名称
        - configured: 是否已配置 API Key
        - key_preview: 遮盖后的 Key 预览
        - extra_config: 额外配置 (api_host, api_version 等)
    """
    manager = get_provider_manager()
    api_keys = parse_provider_keys_header(request.headers.get("X-Provider-Keys"))
    return manager.get_all_status(api_keys)


@router.post("/{provider}/verify")
async def verify_provider_key(provider: str, req: VerifyKeyRequest, request: Request):
    """验证某个 Provider 的 API Key 有效性

    可以传入 key 验证，也可以从 X-Provider-Keys header 中读取已配置的 key。

    Returns:
        valid: 是否有效
        message: 验证结果消息
    """
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    # 优先使用请求体中的 key，其次从 header 中读取
    api_keys = parse_provider_keys_header(request.headers.get("X-Provider-Keys"))
    key_to_verify = req.key or api_keys.get(provider)

    manager = get_provider_manager()
    result = await manager.verify_key(provider, key_to_verify)
    return result


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
