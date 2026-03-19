"""Provider 管理器

管理各 LLM Provider 的额外配置（api_host, api_version）和 Key 验证逻辑。
API Key 不再存储在后端，由前端通过 localStorage 管理，
每次请求通过 X-Provider-Keys header 或 WebSocket query params 传入。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Provider 元数据
# 注意：azure_openai 和 siliconflow 需要额外配置（api_host 等），在 _extra_config 中管理
PROVIDERS: dict[str, dict[str, str]] = {
    "openrouter": {
        "name": "OpenRouter",
        "env_key": "OPENROUTER_API_KEY",
        "verify_url": "https://openrouter.ai/api/v1/models",
    },
    "siliconflow": {
        "name": "SiliconFlow",
        "env_key": "SILICONFLOW_API_KEY",
        "verify_url": "https://api.siliconflow.cn/v1/models",
        "default_api_host": "https://api.siliconflow.cn",
    },
    "azure_openai": {
        "name": "Azure OpenAI",
        "env_key": "AZURE_OPENAI_API_KEY",
        "verify_url": "",  # dynamic: {endpoint}/openai/models?api-version=...
        "default_api_version": "2024-10-21",
    },
    "zhipu": {
        "name": "Zhipu (智谱)",
        "env_key": "ZHIPU_API_KEY",
        "verify_url": "https://open.bigmodel.cn/api/paas/v4/models",
        "default_api_host": "https://open.bigmodel.cn/api/paas/v4",
    },
}


class ProviderManager:
    """Provider 配置管理器（单例）

    管理各 Provider 的额外配置（api_host, api_version）和 Key 验证。
    API Key 不再存储在后端内存中。
    """

    def __init__(self) -> None:
        # provider_id -> extra config (api_host, api_version, etc.)
        self._extra_config: dict[str, dict[str, str]] = {}

    # ---- 额外配置管理 (api_host, api_version) ----

    def set_extra_config(self, provider: str, config: dict[str, str]) -> None:
        """设置 Provider 的额外配置"""
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        if provider not in self._extra_config:
            self._extra_config[provider] = {}
        self._extra_config[provider].update(config)

        # Azure OpenAI: 同步环境变量
        import os

        if provider == "azure_openai":
            if "api_host" in config:
                os.environ["AZURE_API_BASE"] = config["api_host"]
            if "api_version" in config:
                os.environ["AZURE_API_VERSION"] = config["api_version"]

        logger.info("Extra config set for provider: %s -> %s", provider, list(config.keys()))

    def get_extra_config(self, provider: str) -> dict[str, str]:
        """获取 Provider 的额外配置"""
        base = {}
        meta = PROVIDERS.get(provider, {})
        if "default_api_host" in meta:
            base["api_host"] = meta["default_api_host"]
        if "default_api_version" in meta:
            base["api_version"] = meta["default_api_version"]
        # 运行时配置覆盖默认值
        base.update(self._extra_config.get(provider, {}))
        return base

    def get_all_status(self, api_keys: dict[str, str] | None = None) -> list[dict[str, Any]]:
        """获取所有 Provider 的状态

        Args:
            api_keys: 从请求中传入的 provider keys（来自前端 localStorage）
        """
        keys = api_keys or {}
        result = []
        for provider_id, meta in PROVIDERS.items():
            has_key = bool(keys.get(provider_id, "").strip())
            extra = self.get_extra_config(provider_id)
            status: dict[str, Any] = {
                "provider": provider_id,
                "name": meta["name"],
                "configured": has_key,
                "key_preview": self._mask_key(keys.get(provider_id, "")) if has_key else None,
            }
            # 包含额外配置信息
            if extra:
                status["extra_config"] = extra
            result.append(status)
        return result

    async def verify_key(self, provider: str, key: str | None = None) -> dict[str, Any]:
        """验证某个 Provider 的 API Key 是否有效

        Args:
            provider: Provider ID
            key: 要验证的 key

        Returns:
            {"valid": bool, "message": str}
        """
        if provider not in PROVIDERS:
            return {"valid": False, "message": f"Unknown provider: {provider}"}

        api_key = key
        if not api_key:
            return {"valid": False, "message": "No API key provided"}

        try:
            if provider == "openrouter":
                return await self._verify_openrouter(api_key)
            elif provider == "siliconflow":
                return await self._verify_siliconflow(api_key)
            elif provider == "azure_openai":
                return await self._verify_azure_openai(api_key)
            elif provider == "zhipu":
                return await self._verify_zhipu(api_key)
            else:
                return {"valid": False, "message": f"Verification not supported for {provider}"}
        except Exception as e:
            logger.warning("Key verification failed for %s: %s", provider, e)
            return {"valid": False, "message": str(e)}

    # ---- 验证各 Provider ----

    async def _verify_openrouter(self, key: str) -> dict[str, Any]:
        """验证 OpenRouter API Key"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                return {"valid": True, "message": "OpenRouter API Key valid"}
            elif resp.status_code in (401, 403):
                return {"valid": False, "message": "Invalid API Key"}
            else:
                return {"valid": False, "message": f"HTTP {resp.status_code}: {resp.text[:100]}"}

    async def _verify_siliconflow(self, key: str) -> dict[str, Any]:
        """验证 SiliconFlow API Key

        SiliconFlow 兼容 OpenAI API 格式，通过 GET /v1/models 验证。
        """
        extra = self.get_extra_config("siliconflow")
        api_host = extra.get("api_host", "https://api.siliconflow.cn")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{api_host.rstrip('/')}/v1/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                return {"valid": True, "message": "SiliconFlow API Key valid"}
            elif resp.status_code in (401, 403):
                return {"valid": False, "message": "Invalid API Key"}
            else:
                return {"valid": False, "message": f"HTTP {resp.status_code}: {resp.text[:100]}"}

    async def _verify_azure_openai(self, key: str) -> dict[str, Any]:
        """验证 Azure OpenAI API Key

        通过 GET {endpoint}/openai/models?api-version=... 验证。
        需要先配置 api_host (Azure endpoint)。
        """
        extra = self.get_extra_config("azure_openai")
        api_host = extra.get("api_host", "")
        api_version = extra.get("api_version", "2024-10-21")

        if not api_host:
            return {"valid": False, "message": "请先配置 API Host (Azure Endpoint)"}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{api_host.rstrip('/')}/openai/models?api-version={api_version}",
                headers={"api-key": key},
                timeout=10.0,
            )
            if resp.status_code == 200:
                return {"valid": True, "message": "Azure OpenAI API Key valid"}
            elif resp.status_code in (401, 403):
                return {"valid": False, "message": "Invalid API Key"}
            else:
                return {"valid": False, "message": f"HTTP {resp.status_code}: {resp.text[:100]}"}

    async def _verify_zhipu(self, key: str) -> dict[str, Any]:
        """验证智谱 API Key

        智谱兼容 OpenAI API 格式，通过 GET /models 验证。
        """
        extra = self.get_extra_config("zhipu")
        api_host = extra.get("api_host", "https://open.bigmodel.cn/api/paas/v4")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{api_host.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                return {"valid": True, "message": "Zhipu API Key valid"}
            elif resp.status_code in (401, 403):
                return {"valid": False, "message": "Invalid API Key"}
            else:
                return {"valid": False, "message": f"HTTP {resp.status_code}: {resp.text[:100]}"}

    @staticmethod
    def _mask_key(key: str) -> str:
        """遮盖 API Key，仅显示前后几位"""
        if not key or len(key) <= 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"


# ---- 单例 ----

_provider_manager: ProviderManager | None = None


def get_provider_manager() -> ProviderManager:
    """获取 ProviderManager 单例"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


def parse_provider_keys_header(header_value: str | None) -> dict[str, str]:
    """解析 X-Provider-Keys header 值

    Args:
        header_value: JSON 格式的 provider keys，如 '{"openrouter":"sk-xxx","zhipu":"zk-xxx"}'

    Returns:
        provider -> key 的字典
    """
    if not header_value:
        return {}
    import json

    try:
        keys = json.loads(header_value)
        if isinstance(keys, dict):
            return {k: v for k, v in keys.items() if isinstance(v, str) and v.strip()}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse X-Provider-Keys header")
    return {}
