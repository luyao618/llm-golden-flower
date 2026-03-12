"""Provider 管理器

管理各 LLM Provider（OpenAI / Anthropic / Google）的 API Key 配置。
API Key 运行时存储在内存中，不持久化到磁盘（安全考虑）。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Provider 元数据
PROVIDERS: dict[str, dict[str, str]] = {
    "openai": {
        "name": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "verify_url": "https://api.openai.com/v1/models",
    },
    "anthropic": {
        "name": "Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "verify_url": "https://api.anthropic.com/v1/messages",
    },
    "google": {
        "name": "Google Gemini",
        "env_key": "GEMINI_API_KEY",
        "verify_url": "https://generativelanguage.googleapis.com/v1beta/models",
    },
}


class ProviderManager:
    """Provider API Key 管理器（单例）

    在运行时管理各 Provider 的 API Key。
    Key 存储在内存中，应用重启后失效。
    """

    def __init__(self) -> None:
        # provider_id -> API Key
        self._keys: dict[str, str] = {}

    def set_key(self, provider: str, key: str) -> None:
        """设置某个 Provider 的 API Key

        同时更新环境变量，使 LiteLLM 能够使用。
        """
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")

        self._keys[provider] = key

        # 同步更新环境变量
        import os

        env_key = PROVIDERS[provider]["env_key"]
        os.environ[env_key] = key

        logger.info("API Key set for provider: %s", provider)

    def remove_key(self, provider: str) -> None:
        """移除某个 Provider 的 API Key"""
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")

        self._keys.pop(provider, None)

        # 清除环境变量
        import os

        env_key = PROVIDERS[provider]["env_key"]
        os.environ.pop(env_key, None)

        logger.info("API Key removed for provider: %s", provider)

    def get_key(self, provider: str) -> str | None:
        """获取某个 Provider 的 API Key"""
        # 优先使用运行时设置的 key
        if provider in self._keys:
            return self._keys[provider]

        # 回退到环境变量 / Settings
        import os
        from app.config import get_settings

        settings = get_settings()

        if provider == "openai":
            return settings.openai_api_key or os.environ.get("OPENAI_API_KEY") or None
        elif provider == "anthropic":
            return settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY") or None
        elif provider == "google":
            return settings.google_api_key or os.environ.get("GEMINI_API_KEY") or None

        return None

    def has_key(self, provider: str) -> bool:
        """检查某个 Provider 是否已配置 API Key"""
        key = self.get_key(provider)
        return bool(key and key.strip())

    def get_all_status(self) -> list[dict[str, Any]]:
        """获取所有 Provider 的状态"""
        result = []
        for provider_id, meta in PROVIDERS.items():
            has_key = self.has_key(provider_id)
            result.append(
                {
                    "provider": provider_id,
                    "name": meta["name"],
                    "configured": has_key,
                    "key_preview": self._mask_key(provider_id) if has_key else None,
                }
            )
        return result

    async def verify_key(self, provider: str, key: str | None = None) -> dict[str, Any]:
        """验证某个 Provider 的 API Key 是否有效

        Args:
            provider: Provider ID
            key: 要验证的 key，None 则使用已配置的 key

        Returns:
            {"valid": bool, "message": str}
        """
        if provider not in PROVIDERS:
            return {"valid": False, "message": f"Unknown provider: {provider}"}

        api_key = key or self.get_key(provider)
        if not api_key:
            return {"valid": False, "message": "No API key provided"}

        try:
            if provider == "openai":
                return await self._verify_openai(api_key)
            elif provider == "anthropic":
                return await self._verify_anthropic(api_key)
            elif provider == "google":
                return await self._verify_google(api_key)
            else:
                return {"valid": False, "message": f"Verification not supported for {provider}"}
        except Exception as e:
            logger.warning("Key verification failed for %s: %s", provider, e)
            return {"valid": False, "message": str(e)}

    # ---- 验证各 Provider ----

    async def _verify_openai(self, key: str) -> dict[str, Any]:
        """验证 OpenAI API Key"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                return {"valid": True, "message": "OpenAI API Key valid"}
            elif resp.status_code == 401:
                return {"valid": False, "message": "Invalid API Key"}
            else:
                return {"valid": False, "message": f"HTTP {resp.status_code}: {resp.text[:100]}"}

    async def _verify_anthropic(self, key: str) -> dict[str, Any]:
        """验证 Anthropic API Key"""
        async with httpx.AsyncClient() as client:
            # 用一个最小的请求来验证
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                return {"valid": True, "message": "Anthropic API Key valid"}
            elif resp.status_code == 401:
                return {"valid": False, "message": "Invalid API Key"}
            elif resp.status_code == 400:
                # 400 但不是 auth 错误说明 key 是有效的
                data = resp.json()
                error_type = data.get("error", {}).get("type", "")
                if error_type == "authentication_error":
                    return {"valid": False, "message": "Invalid API Key"}
                return {"valid": True, "message": "Anthropic API Key valid"}
            else:
                return {"valid": False, "message": f"HTTP {resp.status_code}"}

    async def _verify_google(self, key: str) -> dict[str, Any]:
        """验证 Google Gemini API Key"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
                timeout=10.0,
            )
            if resp.status_code == 200:
                return {"valid": True, "message": "Google API Key valid"}
            elif resp.status_code in (400, 401, 403):
                return {"valid": False, "message": "Invalid API Key"}
            else:
                return {"valid": False, "message": f"HTTP {resp.status_code}"}

    def _mask_key(self, provider: str) -> str:
        """遮盖 API Key，仅显示前后几位"""
        key = self.get_key(provider) or ""
        if len(key) <= 8:
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
