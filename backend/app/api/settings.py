"""游戏设置 API 路由

提供端点管理全局游戏设置:
- GET  /api/settings — 获取当前设置
- POST /api/settings — 更新设置
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])

# ---- 运行时可修改的设置（内存中，重启后恢复默认） ----

_runtime_settings: dict = {
    "llm_max_tokens": None,  # None 表示无上限，使用各路径的默认值
}


class SettingsResponse(BaseModel):
    """设置响应"""

    llm_max_tokens: int | None = None


class UpdateSettingsRequest(BaseModel):
    """更新设置请求体"""

    llm_max_tokens: int | None = None


def get_runtime_max_tokens() -> int | None:
    """获取运行时 max_tokens 设置，供 base_agent 调用"""
    return _runtime_settings["llm_max_tokens"]


@router.get("")
async def get_settings() -> SettingsResponse:
    """获取当前设置"""
    return SettingsResponse(**_runtime_settings)


@router.post("")
async def update_settings(req: UpdateSettingsRequest) -> SettingsResponse:
    """更新设置"""
    if req.llm_max_tokens is not None:
        _runtime_settings["llm_max_tokens"] = req.llm_max_tokens
    else:
        _runtime_settings["llm_max_tokens"] = None
    return SettingsResponse(**_runtime_settings)
