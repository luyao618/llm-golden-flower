"""基础配置管理

管理 AI 模型列表、游戏默认参数、环境变量等配置。
支持动态模型列表（根据已配置的 Provider 过滤）。
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置，支持从环境变量和 .env 文件加载"""

    # ---- 服务配置 ----
    app_name: str = "Golden Flower Poker AI"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # ---- 数据库 ----
    database_url: str = "sqlite+aiosqlite:///./golden_flower.db"

    # ---- AI API Keys ----
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # ---- 游戏默认配置 ----
    default_initial_chips: int = 1000
    default_ante: int = 10
    default_max_bet: int = 200
    default_max_turns: int = 10

    # ---- AI 调用配置 ----
    llm_timeout: int = 30  # LLM API 调用超时（秒）
    llm_max_retries: int = 3  # LLM API 最大重试次数
    llm_temperature: float = 0.7  # LLM 生成温度

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# ---- LiteLLM Provider 的模型配置（静态注册表） ----
AI_MODELS: dict[str, dict] = {
    "openai-gpt4o": {
        "model": "gpt-4o",
        "display_name": "GPT-4o",
        "provider": "openai",
    },
    "openai-gpt4o-mini": {
        "model": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "provider": "openai",
    },
    "anthropic-claude-sonnet": {
        "model": "claude-sonnet-4-20250514",
        "display_name": "Claude Sonnet",
        "provider": "anthropic",
    },
    "google-gemini-flash": {
        "model": "gemini/gemini-2.0-flash",
        "display_name": "Gemini 2.0 Flash",
        "provider": "google",
    },
}

# ---- GitHub Copilot 模型配置（仅在 Copilot 认证成功后可用） ----
COPILOT_MODELS: dict[str, dict] = {
    "copilot-gpt4o": {
        "model": "gpt-4o",
        "display_name": "Copilot GPT-4o",
        "provider": "github_copilot",
    },
    "copilot-gpt4o-mini": {
        "model": "gpt-4o-mini",
        "display_name": "Copilot GPT-4o Mini",
        "provider": "github_copilot",
    },
    "copilot-claude-sonnet": {
        "model": "claude-3.5-sonnet",
        "display_name": "Copilot Claude Sonnet",
        "provider": "github_copilot",
    },
}

# 合并所有模型的完整注册表（用于 model_id 查找）
ALL_MODELS: dict[str, dict] = {**AI_MODELS, **COPILOT_MODELS}

# AI 性格预设名称列表
AI_PERSONALITIES = [
    "aggressive",  # 激进型
    "conservative",  # 保守型
    "analytical",  # 分析型
    "intuitive",  # 直觉型
    "bluffer",  # 诈唬型
]

# 预设 AI 名字（按性格分组）
AI_NAMES: dict[str, list[str]] = {
    "aggressive": ["火焰哥", "暴风姐", "铁拳王"],
    "conservative": ["稳如山", "老谋子", "静水姐"],
    "analytical": ["数据侠", "概率哥", "精算姐"],
    "intuitive": ["第六感", "灵感王", "直觉姐"],
    "bluffer": ["千面人", "烟雾弹", "影帝哥"],
}

# 预设头像标识
AI_AVATARS = [
    "avatar_1",
    "avatar_2",
    "avatar_3",
    "avatar_4",
    "avatar_5",
]


def get_settings() -> Settings:
    """获取应用配置（单例模式）"""
    return Settings()


def get_available_models() -> list[dict]:
    """获取可用的 AI 模型列表

    动态过滤：只返回已配置 API Key 的 Provider 的模型。
    - LiteLLM Provider (openai/anthropic/google): 需要对应 API Key 已配置
    - GitHub Copilot: 需要 Copilot 认证成功
    """
    from app.services.provider_manager import get_provider_manager
    from app.services.copilot_auth import get_copilot_auth

    provider_manager = get_provider_manager()
    copilot_auth = get_copilot_auth()

    models = []

    # LiteLLM Provider 的模型
    for model_id, model_info in AI_MODELS.items():
        provider = model_info["provider"]
        if provider_manager.has_key(provider):
            models.append({"id": model_id, **model_info})

    # Copilot 模型
    if copilot_auth.is_connected:
        for model_id, model_info in COPILOT_MODELS.items():
            models.append({"id": model_id, **model_info})

    return models


def get_model_config(model_id: str) -> dict | None:
    """根据 model_id 获取模型配置

    从完整注册表（ALL_MODELS）中查找，不受 Provider 配置状态影响。
    """
    return ALL_MODELS.get(model_id)
