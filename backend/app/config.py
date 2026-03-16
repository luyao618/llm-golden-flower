"""基础配置管理

管理 AI 模型列表、游戏默认参数、环境变量等配置。
支持动态模型列表（根据已配置的 Provider 过滤）。
OpenRouter / SiliconFlow / Azure OpenAI 模型为动态注册（用户从 API 模型列表中选择添加）。
"""

from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


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
    openrouter_api_key: str = ""

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

# ---- 动态模型注册表（运行时由用户添加/移除） ----
OPENROUTER_MODELS: dict[str, dict] = {}
SILICONFLOW_MODELS: dict[str, dict] = {}
AZURE_OPENAI_MODELS: dict[str, dict] = {}

# 合并所有模型的完整注册表（用于 model_id 查找）
ALL_MODELS: dict[str, dict] = {**COPILOT_MODELS}

# AI 预设名字（扁平列表）
AI_NAMES: list[str] = [
    "火焰哥",
    "暴风姐",
    "铁拳王",
    "稳如山",
    "老谋子",
    "静水姐",
    "数据侠",
    "概率哥",
    "精算姐",
    "第六感",
    "灵感王",
    "直觉姐",
    "千面人",
    "烟雾弹",
    "影帝哥",
]

# 预设头像标识
AI_AVATARS = [
    "avatar_1",
    "avatar_2",
    "avatar_3",
    "avatar_4",
    "avatar_5",
]


@lru_cache()
def get_settings() -> Settings:
    """获取应用配置（单例模式）"""
    return Settings()


def _get_all_models() -> dict[str, dict]:
    """获取包含动态模型在内的完整模型注册表"""
    return {**COPILOT_MODELS, **OPENROUTER_MODELS, **SILICONFLOW_MODELS, **AZURE_OPENAI_MODELS}


def get_available_models() -> list[dict]:
    """获取可用的 AI 模型列表

    动态过滤：只返回已配置 API Key 的 Provider 的模型。
    - GitHub Copilot: 需要 Copilot 认证成功
    - OpenRouter: 需要 OpenRouter API Key 已配置，且模型由用户动态添加
    - SiliconFlow: 需要 SiliconFlow API Key 已配置，且模型由用户动态添加
    - Azure OpenAI: 需要 Azure OpenAI API Key 已配置，且模型由用户动态添加
    """
    from app.services.provider_manager import get_provider_manager
    from app.services.copilot_auth import get_copilot_auth

    provider_manager = get_provider_manager()
    copilot_auth = get_copilot_auth()

    models = []

    # Copilot 模型
    if copilot_auth.is_connected:
        for model_id, model_info in COPILOT_MODELS.items():
            models.append({"id": model_id, **model_info})

    # OpenRouter 动态模型
    if provider_manager.has_key("openrouter"):
        for model_id, model_info in OPENROUTER_MODELS.items():
            models.append({"id": model_id, **model_info})

    # SiliconFlow 动态模型
    if provider_manager.has_key("siliconflow"):
        for model_id, model_info in SILICONFLOW_MODELS.items():
            models.append({"id": model_id, **model_info})

    # Azure OpenAI 动态模型
    if provider_manager.has_key("azure_openai"):
        for model_id, model_info in AZURE_OPENAI_MODELS.items():
            models.append({"id": model_id, **model_info})

    return models


def get_model_config(model_id: str) -> dict | None:
    """根据 model_id 获取模型配置"""
    return _get_all_models().get(model_id)


# ---- OpenRouter 动态模型管理 ----


def add_openrouter_model(openrouter_model_id: str, display_name: str) -> str:
    """添加一个 OpenRouter 模型到可用列表"""
    model_id = "openrouter-" + openrouter_model_id.replace("/", "-")

    if model_id in OPENROUTER_MODELS:
        logger.info("OpenRouter model already added: %s", model_id)
        return model_id

    OPENROUTER_MODELS[model_id] = {
        "model": f"openrouter/{openrouter_model_id}",
        "display_name": display_name,
        "provider": "openrouter",
        "openrouter_id": openrouter_model_id,
    }
    ALL_MODELS[model_id] = OPENROUTER_MODELS[model_id]

    logger.info("OpenRouter model added: %s -> %s", model_id, openrouter_model_id)
    return model_id


def remove_openrouter_model(model_id: str) -> bool:
    """从可用列表中移除一个 OpenRouter 模型"""
    if model_id not in OPENROUTER_MODELS:
        return False
    del OPENROUTER_MODELS[model_id]
    ALL_MODELS.pop(model_id, None)
    logger.info("OpenRouter model removed: %s", model_id)
    return True


def get_openrouter_models() -> list[dict]:
    """获取当前已添加的 OpenRouter 模型列表"""
    return [{"id": mid, **info} for mid, info in OPENROUTER_MODELS.items()]


# ---- SiliconFlow 动态模型管理 ----


def add_siliconflow_model(siliconflow_model_id: str, display_name: str) -> str:
    """添加一个 SiliconFlow 模型到可用列表"""
    model_id = "siliconflow-" + siliconflow_model_id.replace("/", "-")

    if model_id in SILICONFLOW_MODELS:
        logger.info("SiliconFlow model already added: %s", model_id)
        return model_id

    SILICONFLOW_MODELS[model_id] = {
        "model": f"openai/{siliconflow_model_id}",  # SiliconFlow 兼容 OpenAI 格式，通过 LiteLLM openai/ 前缀调用
        "display_name": display_name,
        "provider": "siliconflow",
        "siliconflow_id": siliconflow_model_id,
    }
    ALL_MODELS[model_id] = SILICONFLOW_MODELS[model_id]

    logger.info("SiliconFlow model added: %s -> %s", model_id, siliconflow_model_id)
    return model_id


def remove_siliconflow_model(model_id: str) -> bool:
    """从可用列表中移除一个 SiliconFlow 模型"""
    if model_id not in SILICONFLOW_MODELS:
        return False
    del SILICONFLOW_MODELS[model_id]
    ALL_MODELS.pop(model_id, None)
    logger.info("SiliconFlow model removed: %s", model_id)
    return True


def get_siliconflow_models() -> list[dict]:
    """获取当前已添加的 SiliconFlow 模型列表"""
    return [{"id": mid, **info} for mid, info in SILICONFLOW_MODELS.items()]


# ---- Azure OpenAI 动态模型管理 ----


def add_azure_openai_model(azure_model_id: str, display_name: str) -> str:
    """添加一个 Azure OpenAI 模型到可用列表"""
    model_id = "azure-" + azure_model_id.replace("/", "-")

    if model_id in AZURE_OPENAI_MODELS:
        logger.info("Azure OpenAI model already added: %s", model_id)
        return model_id

    AZURE_OPENAI_MODELS[model_id] = {
        "model": f"azure/{azure_model_id}",  # LiteLLM azure/ 前缀
        "display_name": display_name,
        "provider": "azure_openai",
        "azure_id": azure_model_id,
    }
    ALL_MODELS[model_id] = AZURE_OPENAI_MODELS[model_id]

    logger.info("Azure OpenAI model added: %s -> %s", model_id, azure_model_id)
    return model_id


def remove_azure_openai_model(model_id: str) -> bool:
    """从可用列表中移除一个 Azure OpenAI 模型"""
    if model_id not in AZURE_OPENAI_MODELS:
        return False
    del AZURE_OPENAI_MODELS[model_id]
    ALL_MODELS.pop(model_id, None)
    logger.info("Azure OpenAI model removed: %s", model_id)
    return True


def get_azure_openai_models() -> list[dict]:
    """获取当前已添加的 Azure OpenAI 模型列表"""
    return [{"id": mid, **info} for mid, info in AZURE_OPENAI_MODELS.items()]
