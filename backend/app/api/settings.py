"""游戏设置 API 路由

提供端点管理全局游戏设置:
- GET  /api/settings — 获取当前设置
- POST /api/settings — 更新设置（部分更新，只修改请求中包含的字段）
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import get_settings


class ThinkingMode(str, Enum):
    """AI 思考模式

    控制 AI 决策时的输出详细程度，影响响应速度和心路历程丰富度。

    - detailed: 完整思考 — 7 个思考字段全部输出，心路历程最丰富，速度最慢
    - fast: 快速思考 — 仅输出 reasoning + confidence + emotion，速度与质量的平衡
    - turbo: 极速决策 — 不输出思考过程，仅返回 action + target + table_talk，速度最快
    """

    DETAILED = "detailed"
    FAST = "fast"
    TURBO = "turbo"


router = APIRouter(prefix="/api/settings", tags=["settings"])

# ---- 运行时可修改的设置（内存中，重启后恢复默认） ----
# None 表示使用 config.py Settings 中的默认值


def _build_defaults() -> dict:
    """从 Settings 构建初始默认值"""
    s = get_settings()
    return {
        "llm_max_tokens": None,  # None = 无上限
        "ai_thinking_mode": ThinkingMode.FAST.value,  # 默认快速思考
        # AI 调用配置
        "llm_timeout": s.llm_timeout,
        "llm_max_retries": s.llm_max_retries,
        "llm_temperature": s.llm_temperature,
    }


_runtime_settings: dict = _build_defaults()


class SettingsResponse(BaseModel):
    """设置响应"""

    llm_max_tokens: int | None = None
    ai_thinking_mode: str = ThinkingMode.FAST.value
    # AI 调用配置
    llm_timeout: int = 30
    llm_max_retries: int = 3
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class UpdateSettingsRequest(BaseModel):
    """更新设置请求体（部分更新，仅提交需要修改的字段）"""

    llm_max_tokens: int | None = None
    ai_thinking_mode: Literal["detailed", "fast", "turbo"] | None = None
    # AI 调用配置
    llm_timeout: int | None = Field(None, ge=5, le=120)
    llm_max_retries: int | None = Field(None, ge=0, le=10)
    llm_temperature: float | None = Field(None, ge=0.0, le=2.0)


# ---- Getter 函数，供其他模块读取运行时设置 ----


def get_runtime_max_tokens() -> int | None:
    """获取运行时 max_tokens 设置，供 base_agent 调用"""
    return _runtime_settings["llm_max_tokens"]


def get_thinking_mode() -> ThinkingMode:
    """获取当前 AI 思考模式

    Returns:
        ThinkingMode 枚举值
    """
    raw = _runtime_settings.get("ai_thinking_mode", ThinkingMode.FAST.value)
    try:
        return ThinkingMode(raw)
    except ValueError:
        return ThinkingMode.FAST


def get_runtime_llm_config() -> dict:
    """获取运行时 LLM 调用配置"""
    return {
        "llm_timeout": _runtime_settings["llm_timeout"],
        "llm_max_retries": _runtime_settings["llm_max_retries"],
        "llm_temperature": _runtime_settings["llm_temperature"],
    }


@router.get("")
async def get_settings_api() -> SettingsResponse:
    """获取当前设置"""
    return SettingsResponse(**_runtime_settings)


@router.post("")
async def update_settings(req: UpdateSettingsRequest) -> SettingsResponse:
    """更新设置（部分更新）

    只修改请求中显式提供的字段，其余保持不变。
    llm_max_tokens 为特殊字段：显式传 null 表示设为无上限。
    """
    update_data = req.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        _runtime_settings[key] = value

    return SettingsResponse(**_runtime_settings)
