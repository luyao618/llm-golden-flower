"""GitHub Copilot Device Flow API 路由

提供 3 个端点:
- POST /api/copilot/connect  — 发起设备授权
- GET  /api/copilot/poll     — 前端轮询授权状态
- GET  /api/copilot/status   — 查询 Copilot 连接状态
- POST /api/copilot/disconnect — 断开 Copilot 连接
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.copilot_auth import (
    CopilotAuthError,
    get_copilot_auth,
)

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


@router.post("/connect")
async def start_copilot_connect():
    """发起 GitHub Copilot Device Flow 授权

    Returns:
        user_code: 用户需要在 github.com/login/device 输入的验证码
        verification_uri: 授权页面 URL
        expires_in: 验证码有效期（秒）
    """
    auth = get_copilot_auth()
    try:
        result = await auth.start_device_flow()
        return result
    except CopilotAuthError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/poll")
async def poll_copilot_auth():
    """轮询 Device Flow 授权状态

    前端每 5 秒调用一次，直到返回 status="connected"。

    Returns:
        status: "pending" | "connected"
        models: Copilot 可用模型列表（仅 connected 时返回）
    """
    auth = get_copilot_auth()
    try:
        result = await auth.poll_for_token()
        return result
    except CopilotAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def get_copilot_status():
    """查询 Copilot 连接状态

    Returns:
        connected: 是否已连接
        has_valid_token: 是否有有效的会话令牌
        models: 可用模型列表
    """
    auth = get_copilot_auth()
    return auth.get_status()


@router.post("/disconnect")
async def disconnect_copilot():
    """断开 Copilot 连接"""
    auth = get_copilot_auth()
    auth.disconnect()
    return {"message": "Copilot disconnected"}
