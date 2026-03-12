"""GitHub Copilot 认证管理器

通过 GitHub OAuth Device Flow 获取访问令牌，
再换取 Copilot 会话令牌，最终调用 Copilot Chat Completions API。

认证流程:
1. start_device_flow() -> 返回 device_code + user_code
2. 用户在浏览器访问 github.com/login/device 输入 user_code
3. poll_for_token() -> 轮询获取 GitHub access_token
4. get_copilot_token() -> 用 access_token 换取 Copilot 会话令牌
5. call_copilot_api() -> 调用 Copilot Chat Completions API

注意: 使用未公开的 Copilot API + VS Code Client ID，仅限个人学习使用。
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# VS Code 公开的 OAuth App Client ID
GITHUB_CLIENT_ID = "Iv1.b507a08c87ecfe98"

# GitHub OAuth 端点
GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"

# Copilot 端点
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
COPILOT_CHAT_URL = "https://api.githubcopilot.com/chat/completions"

# Copilot Chat API 必需的 Headers
COPILOT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Copilot-Integration-Id": "vscode-chat",
    "Editor-Version": "vscode/1.95.0",
    "Editor-Plugin-Version": "copilot-chat/0.22.0",
    "Openai-Organization": "github-copilot",
    "User-Agent": "GitHubCopilotChat/0.22.0",
}


@dataclass
class DeviceFlowState:
    """Device Flow 认证状态"""

    device_code: str = ""
    user_code: str = ""
    verification_uri: str = ""
    expires_in: int = 900
    interval: int = 5
    started_at: float = 0.0


@dataclass
class CopilotToken:
    """Copilot 会话令牌"""

    token: str = ""
    expires_at: float = 0.0
    endpoints: dict[str, str] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """令牌是否仍然有效（提前 5 分钟判定为过期）"""
        return bool(self.token) and time.time() < (self.expires_at - 300)


class CopilotAuthManager:
    """Copilot 认证管理器（单例）

    管理 GitHub Device Flow 认证和 Copilot 会话令牌的生命周期。
    所有凭据存储在内存中，应用重启需重新授权。
    """

    def __init__(self) -> None:
        self._github_token: str = ""  # GitHub access_token (gho_XXX)
        self._copilot_token: CopilotToken = CopilotToken()
        self._device_flow: DeviceFlowState | None = None
        self._connected: bool = False
        self._refresh_lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        """是否已完成 GitHub 授权"""
        return self._connected and bool(self._github_token)

    @property
    def has_valid_token(self) -> bool:
        """是否有有效的 Copilot 会话令牌"""
        return self._copilot_token.is_valid

    # ---- Device Flow ----

    async def start_device_flow(self) -> dict[str, str]:
        """发起 GitHub Device Flow 认证

        Returns:
            包含 user_code 和 verification_uri 的字典

        Raises:
            CopilotAuthError: Device Flow 发起失败
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GITHUB_DEVICE_CODE_URL,
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "scope": "read:user",
                },
                headers={"Accept": "application/json"},
                timeout=15.0,
            )

            if resp.status_code != 200:
                raise CopilotAuthError(
                    f"Failed to start device flow: {resp.status_code} {resp.text}"
                )

            data = resp.json()
            self._device_flow = DeviceFlowState(
                device_code=data["device_code"],
                user_code=data["user_code"],
                verification_uri=data.get("verification_uri", "https://github.com/login/device"),
                expires_in=data.get("expires_in", 900),
                interval=data.get("interval", 5),
                started_at=time.time(),
            )

            logger.info("Device Flow started, user_code=%s", self._device_flow.user_code)

            return {
                "user_code": self._device_flow.user_code,
                "verification_uri": self._device_flow.verification_uri,
                "expires_in": self._device_flow.expires_in,
            }

    async def poll_for_token(self) -> dict[str, Any]:
        """轮询 GitHub 检查用户是否已完成授权

        Returns:
            {"status": "pending"} 或 {"status": "connected", "models": [...]}

        Raises:
            CopilotAuthError: Device Flow 未启动或已过期
        """
        if not self._device_flow:
            raise CopilotAuthError("Device flow not started")

        # 检查是否已过期
        elapsed = time.time() - self._device_flow.started_at
        if elapsed > self._device_flow.expires_in:
            self._device_flow = None
            raise CopilotAuthError("Device flow expired, please start again")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GITHUB_ACCESS_TOKEN_URL,
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "device_code": self._device_flow.device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
                timeout=15.0,
            )

            data = resp.json()

            if "error" in data:
                error = data["error"]
                if error == "authorization_pending":
                    return {"status": "pending"}
                elif error == "slow_down":
                    # GitHub 要求降低轮询频率
                    if self._device_flow:
                        self._device_flow.interval += 5
                    return {"status": "pending", "slow_down": True}
                elif error == "expired_token":
                    self._device_flow = None
                    raise CopilotAuthError("Device flow expired")
                elif error == "access_denied":
                    self._device_flow = None
                    raise CopilotAuthError("User denied authorization")
                else:
                    raise CopilotAuthError(
                        f"OAuth error: {error} - {data.get('error_description', '')}"
                    )

            # 成功获取 access_token
            access_token = data.get("access_token", "")
            if not access_token:
                raise CopilotAuthError("No access_token in response")

            self._github_token = access_token
            self._connected = True
            self._device_flow = None

            logger.info("GitHub authorization successful")

            # 立即获取 Copilot 令牌
            try:
                await self._fetch_copilot_token()
                logger.info("Copilot token obtained successfully")
            except Exception as e:
                logger.warning("Failed to get Copilot token: %s", e)
                # 授权成功但获取 Copilot 令牌失败，仍然返回已连接状态

            return {
                "status": "connected",
                "models": self.get_available_models(),
            }

    # ---- Copilot Token ----

    async def _fetch_copilot_token(self) -> None:
        """用 GitHub access_token 换取 Copilot 会话令牌"""
        if not self._github_token:
            raise CopilotAuthError("No GitHub token available")

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                COPILOT_TOKEN_URL,
                headers={
                    "Authorization": f"token {self._github_token}",
                    "Accept": "application/json",
                },
                timeout=15.0,
            )

            if resp.status_code == 401:
                # GitHub token 失效，需要重新授权
                self._connected = False
                self._github_token = ""
                raise CopilotAuthError("GitHub token expired, please reconnect")

            if resp.status_code != 200:
                raise CopilotAuthError(
                    f"Failed to get Copilot token: {resp.status_code} {resp.text}"
                )

            data = resp.json()
            self._copilot_token = CopilotToken(
                token=data.get("token", ""),
                expires_at=data.get("expires_at", time.time() + 1800),
                endpoints=data.get("endpoints", {}),
            )

    async def _ensure_valid_token(self) -> str:
        """确保有有效的 Copilot 令牌，必要时自动刷新

        Returns:
            有效的 Copilot 会话令牌
        """
        if self._copilot_token.is_valid:
            return self._copilot_token.token

        async with self._refresh_lock:
            # 双重检查（可能在等锁期间已被刷新）
            if self._copilot_token.is_valid:
                return self._copilot_token.token

            logger.info("Refreshing Copilot token...")
            await self._fetch_copilot_token()
            return self._copilot_token.token

    # ---- Chat API ----

    async def call_copilot_api(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """调用 Copilot Chat Completions API

        Args:
            model: 模型名称 (e.g., "gpt-4o", "claude-3.5-sonnet")
            messages: OpenAI 格式的消息列表
            temperature: 生成温度
            max_tokens: 最大生成 token 数

        Returns:
            LLM 响应文本

        Raises:
            CopilotAuthError: 未连接或令牌无效
            CopilotAPIError: API 调用失败
        """
        if not self.is_connected:
            raise CopilotAuthError("Copilot not connected, please authorize first")

        token = await self._ensure_valid_token()

        # 确定实际的 API endpoint
        chat_url = self._copilot_token.endpoints.get(
            "api", COPILOT_CHAT_URL.replace("/chat/completions", "")
        )
        if not chat_url.endswith("/chat/completions"):
            chat_url = chat_url.rstrip("/") + "/chat/completions"

        headers = {
            **COPILOT_HEADERS,
            "Authorization": f"Bearer {token}",
            "X-Request-Id": str(uuid.uuid4()),
        }

        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    chat_url,
                    json=body,
                    headers=headers,
                    timeout=60.0,
                )
            except httpx.TimeoutException:
                raise CopilotAPIError("Copilot API request timed out")
            except httpx.ConnectError:
                raise CopilotAPIError("Failed to connect to Copilot API")

            if resp.status_code == 401:
                # 令牌过期，尝试刷新后重试一次
                logger.warning("Copilot token expired, refreshing...")
                await self._fetch_copilot_token()
                token = self._copilot_token.token
                headers["Authorization"] = f"Bearer {token}"

                resp = await client.post(
                    chat_url,
                    json=body,
                    headers=headers,
                    timeout=60.0,
                )

            if resp.status_code != 200:
                raise CopilotAPIError(f"Copilot API error: {resp.status_code} {resp.text}")

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise CopilotAPIError("Copilot API returned no choices")

            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise CopilotAPIError("Copilot API returned empty content")

            return content

    # ---- 状态查询 ----

    def get_status(self) -> dict[str, Any]:
        """获取当前 Copilot 连接状态"""
        return {
            "connected": self.is_connected,
            "has_valid_token": self.has_valid_token,
            "models": self.get_available_models() if self.is_connected else [],
        }

    def get_available_models(self) -> list[dict[str, str]]:
        """获取 Copilot 可用的模型列表"""
        if not self.is_connected:
            return []

        return [
            {"id": "copilot-gpt4o", "model": "gpt-4o", "display_name": "Copilot GPT-4o"},
            {
                "id": "copilot-gpt4o-mini",
                "model": "gpt-4o-mini",
                "display_name": "Copilot GPT-4o Mini",
            },
            {
                "id": "copilot-claude-sonnet",
                "model": "claude-3.5-sonnet",
                "display_name": "Copilot Claude Sonnet",
            },
        ]

    def disconnect(self) -> None:
        """断开 Copilot 连接，清除所有凭据"""
        self._github_token = ""
        self._copilot_token = CopilotToken()
        self._device_flow = None
        self._connected = False
        logger.info("Copilot disconnected")


# ---- 异常 ----


class CopilotAuthError(Exception):
    """Copilot 认证错误"""

    pass


class CopilotAPIError(Exception):
    """Copilot API 调用错误"""

    pass


# ---- 单例 ----

_copilot_auth: CopilotAuthManager | None = None


def get_copilot_auth() -> CopilotAuthManager:
    """获取 CopilotAuthManager 单例"""
    global _copilot_auth
    if _copilot_auth is None:
        _copilot_auth = CopilotAuthManager()
    return _copilot_auth
