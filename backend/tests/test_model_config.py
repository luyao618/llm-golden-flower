"""模型配置中心 (T8.0) 单元测试

覆盖范围:
- ProviderManager: API Key 设置/移除/查询/遮盖/验证
- CopilotAuthManager: Device Flow 状态机、令牌管理、Chat API、断开连接
- config.py: get_available_models 动态过滤、get_model_config 查找
- base_agent.py: Copilot 路由 (_call_copilot)
- api/provider.py: Provider REST 端点
- api/copilot.py: Copilot REST 端点
"""

from __future__ import annotations

import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import (
    ALL_MODELS,
    AZURE_OPENAI_MODELS,
    COPILOT_MODELS,
    OPENROUTER_MODELS,
    SILICONFLOW_MODELS,
    get_available_models,
    get_model_config,
)
from app.services.copilot_auth import (
    CopilotAPIError,
    CopilotAuthError,
    CopilotAuthManager,
    CopilotToken,
    DeviceFlowState,
)
from app.services.provider_manager import PROVIDERS, ProviderManager


# ============================================================
# Helper: 创建轻量 API 测试客户端（不触发 db/schemas 导入）
# ============================================================


def _make_provider_test_app() -> FastAPI:
    """构建只包含 provider 路由的测试 FastAPI 应用"""
    from app.api.provider import router as provider_router

    test_app = FastAPI()
    test_app.include_router(provider_router)
    return test_app


def _make_copilot_test_app() -> FastAPI:
    """构建只包含 copilot 路由的测试 FastAPI 应用"""
    from app.api.copilot import router as copilot_router

    test_app = FastAPI()
    test_app.include_router(copilot_router)
    return test_app


# ============================================================
#  ProviderManager 单元测试
# ============================================================


class TestProviderManagerSetKey:
    """ProviderManager.set_key — 设置 API Key"""

    def test_set_valid_provider_key(self):
        """设置已知 Provider 的 Key 应成功"""
        mgr = ProviderManager()
        mgr.set_key("openai", "sk-test-123")
        assert mgr.get_key("openai") == "sk-test-123"
        # 清理环境变量
        os.environ.pop("OPENAI_API_KEY", None)

    def test_set_key_updates_env(self):
        """set_key 应同步写入环境变量"""
        mgr = ProviderManager()
        mgr.set_key("anthropic", "ant-key-456")
        assert os.environ.get("ANTHROPIC_API_KEY") == "ant-key-456"
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_set_key_unknown_provider_raises(self):
        """设置未知 Provider 应抛出 ValueError"""
        mgr = ProviderManager()
        with pytest.raises(ValueError, match="Unknown provider"):
            mgr.set_key("unknown_provider", "some-key")

    def test_set_key_overwrite(self):
        """重复设置同一 Provider 的 Key 应覆盖旧值"""
        mgr = ProviderManager()
        mgr.set_key("openai", "key-1")
        mgr.set_key("openai", "key-2")
        assert mgr.get_key("openai") == "key-2"
        os.environ.pop("OPENAI_API_KEY", None)

    def test_set_key_google(self):
        """设置 Google Provider 的 Key"""
        mgr = ProviderManager()
        mgr.set_key("google", "gemini-key-789")
        assert mgr.get_key("google") == "gemini-key-789"
        assert os.environ.get("GEMINI_API_KEY") == "gemini-key-789"
        os.environ.pop("GEMINI_API_KEY", None)


class TestProviderManagerRemoveKey:
    """ProviderManager.remove_key — 移除 API Key"""

    def test_remove_existing_key(self):
        """移除已设置的 Key"""
        mgr = ProviderManager()
        mgr.set_key("openai", "sk-to-remove")
        mgr.remove_key("openai")
        assert mgr._keys.get("openai") is None
        assert os.environ.get("OPENAI_API_KEY") is None

    def test_remove_nonexistent_key_no_error(self):
        """移除未设置的 Key 不应报错"""
        mgr = ProviderManager()
        mgr.remove_key("openai")  # 不应抛出异常

    def test_remove_unknown_provider_raises(self):
        """移除未知 Provider 应抛出 ValueError"""
        mgr = ProviderManager()
        with pytest.raises(ValueError, match="Unknown provider"):
            mgr.remove_key("bad_provider")


class TestProviderManagerGetKey:
    """ProviderManager.get_key — 获取 API Key"""

    def test_get_runtime_key(self):
        """运行时设置的 Key 优先于环境变量"""
        mgr = ProviderManager()
        mgr.set_key("openai", "runtime-key")
        assert mgr.get_key("openai") == "runtime-key"
        os.environ.pop("OPENAI_API_KEY", None)

    def test_get_key_returns_none_when_not_set(self):
        """未设置的 Provider 返回 None"""
        mgr = ProviderManager()
        # 确保环境变量也被清除
        os.environ.pop("OPENAI_API_KEY", None)
        with patch("app.config.get_settings") as mock_gs:
            settings = MagicMock()
            settings.openai_api_key = ""
            mock_gs.return_value = settings
            assert mgr.get_key("openai") is None


class TestProviderManagerHasKey:
    """ProviderManager.has_key — 检查是否已配置"""

    def test_has_key_true(self):
        """已设置非空 Key 返回 True"""
        mgr = ProviderManager()
        mgr.set_key("openai", "sk-valid")
        assert mgr.has_key("openai") is True
        os.environ.pop("OPENAI_API_KEY", None)

    def test_has_key_false_when_not_set(self):
        """未设置返回 False"""
        mgr = ProviderManager()
        os.environ.pop("OPENAI_API_KEY", None)
        with patch("app.config.get_settings") as mock_gs:
            settings = MagicMock()
            settings.openai_api_key = ""
            mock_gs.return_value = settings
            assert mgr.has_key("openai") is False

    def test_has_key_false_for_whitespace(self):
        """仅空白字符的 Key 视为未设置"""
        mgr = ProviderManager()
        mgr._keys["openai"] = "   "
        assert mgr.has_key("openai") is False


class TestProviderManagerGetAllStatus:
    """ProviderManager.get_all_status — 获取所有 Provider 状态"""

    def test_returns_all_providers(self):
        """应返回所有已注册 Provider 的状态"""
        mgr = ProviderManager()
        # 清理环境变量以获得干净状态
        for pid, meta in PROVIDERS.items():
            os.environ.pop(meta["env_key"], None)
        with patch("app.config.get_settings") as mock_gs:
            settings = MagicMock()
            settings.openai_api_key = ""
            settings.anthropic_api_key = ""
            settings.google_api_key = ""
            mock_gs.return_value = settings

            statuses = mgr.get_all_status()
            assert len(statuses) == len(PROVIDERS)
            provider_ids = [s["provider"] for s in statuses]
            assert "openai" in provider_ids
            assert "anthropic" in provider_ids
            assert "google" in provider_ids

    def test_configured_provider_shows_preview(self):
        """已配置的 Provider 显示 key_preview"""
        mgr = ProviderManager()
        mgr.set_key("openai", "sk-abcdefghijklmnop")
        statuses = mgr.get_all_status()
        openai_status = next(s for s in statuses if s["provider"] == "openai")
        assert openai_status["configured"] is True
        assert openai_status["key_preview"] is not None
        assert "..." in openai_status["key_preview"]
        os.environ.pop("OPENAI_API_KEY", None)


class TestProviderManagerMaskKey:
    """ProviderManager._mask_key — API Key 遮盖"""

    def test_mask_long_key(self):
        """长 Key 显示前4后4"""
        mgr = ProviderManager()
        mgr._keys["openai"] = "sk-1234567890abcdef"
        masked = mgr._mask_key("openai")
        assert masked == "sk-1...cdef"

    def test_mask_short_key(self):
        """短 Key 显示 ****"""
        mgr = ProviderManager()
        mgr._keys["openai"] = "abcd"
        masked = mgr._mask_key("openai")
        assert masked == "****"

    def test_mask_empty_key(self):
        """空 Key 显示 ****"""
        mgr = ProviderManager()
        mgr._keys["openai"] = ""
        masked = mgr._mask_key("openai")
        assert masked == "****"


class TestProviderManagerVerifyKey:
    """ProviderManager.verify_key — API Key 验证"""

    @pytest.mark.asyncio
    async def test_verify_unknown_provider(self):
        """验证未知 Provider 应返回 valid=False"""
        mgr = ProviderManager()
        result = await mgr.verify_key("bad_provider")
        assert result["valid"] is False
        assert "Unknown" in result["message"]

    @pytest.mark.asyncio
    async def test_verify_no_key(self):
        """未提供 Key 且无已配置 Key 时返回 valid=False"""
        mgr = ProviderManager()
        os.environ.pop("OPENAI_API_KEY", None)
        with patch("app.config.get_settings") as mock_gs:
            settings = MagicMock()
            settings.openai_api_key = ""
            mock_gs.return_value = settings
            result = await mgr.verify_key("openai")
            assert result["valid"] is False
            assert "No API key" in result["message"]

    @pytest.mark.asyncio
    async def test_verify_openai_success(self):
        """OpenAI Key 验证成功"""
        mgr = ProviderManager()
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            result = await mgr.verify_key("openai", "sk-valid-key")
            assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_verify_openai_invalid(self):
        """OpenAI Key 验证失败 (401)"""
        mgr = ProviderManager()
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            result = await mgr.verify_key("openai", "sk-bad-key")
            assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_verify_anthropic_success(self):
        """Anthropic Key 验证成功"""
        mgr = ProviderManager()
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await mgr.verify_key("anthropic", "ant-valid")
            assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_verify_anthropic_bad_request_but_valid(self):
        """Anthropic 400 但非 auth_error 说明 Key 有效"""
        mgr = ProviderManager()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"error": {"type": "invalid_request_error"}}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await mgr.verify_key("anthropic", "ant-valid")
            assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_verify_anthropic_auth_error(self):
        """Anthropic 400 + authentication_error 说明 Key 无效"""
        mgr = ProviderManager()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"error": {"type": "authentication_error"}}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await mgr.verify_key("anthropic", "ant-bad")
            assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_verify_google_success(self):
        """Google Key 验证成功"""
        mgr = ProviderManager()
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            result = await mgr.verify_key("google", "goog-valid")
            assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_verify_google_invalid(self):
        """Google Key 验证失败 (403)"""
        mgr = ProviderManager()
        mock_resp = MagicMock()
        mock_resp.status_code = 403

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            result = await mgr.verify_key("google", "goog-bad")
            assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_verify_exception_handled(self):
        """验证过程中的异常被捕获"""
        mgr = ProviderManager()
        with patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=Exception("timeout")
        ):
            result = await mgr.verify_key("openai", "sk-test")
            assert result["valid"] is False


# ============================================================
#  CopilotAuthManager 单元测试
# ============================================================


class TestCopilotTokenDataclass:
    """CopilotToken 数据类"""

    def test_empty_token_invalid(self):
        """空令牌视为无效"""
        token = CopilotToken()
        assert token.is_valid is False

    def test_expired_token_invalid(self):
        """过期令牌视为无效"""
        token = CopilotToken(token="abc", expires_at=time.time() - 10)
        assert token.is_valid is False

    def test_soon_expiring_token_invalid(self):
        """距过期不足 5 分钟的令牌视为无效"""
        token = CopilotToken(token="abc", expires_at=time.time() + 100)  # < 300s
        assert token.is_valid is False

    def test_valid_token(self):
        """有效期内的令牌"""
        token = CopilotToken(token="abc", expires_at=time.time() + 600)
        assert token.is_valid is True


class TestCopilotAuthManagerInit:
    """CopilotAuthManager 初始化状态"""

    def test_initial_state_disconnected(self):
        """初始状态应为未连接"""
        auth = CopilotAuthManager()
        assert auth.is_connected is False
        assert auth.has_valid_token is False

    def test_get_status_disconnected(self):
        """未连接时 get_status 返回空模型列表"""
        auth = CopilotAuthManager()
        status = auth.get_status()
        assert status["connected"] is False
        assert status["models"] == []


class TestCopilotDeviceFlow:
    """CopilotAuthManager Device Flow"""

    @pytest.mark.asyncio
    async def test_start_device_flow_success(self):
        """成功发起 Device Flow"""
        auth = CopilotAuthManager()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "device_code": "dc-123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await auth.start_device_flow()
            assert result["user_code"] == "ABCD-1234"
            assert result["verification_uri"] == "https://github.com/login/device"
            assert result["expires_in"] == 900
            assert auth._device_flow is not None
            assert auth._device_flow.device_code == "dc-123"

    @pytest.mark.asyncio
    async def test_start_device_flow_failure(self):
        """Device Flow 发起失败抛出 CopilotAuthError"""
        auth = CopilotAuthManager()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Server error"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(CopilotAuthError, match="Failed to start device flow"):
                await auth.start_device_flow()

    @pytest.mark.asyncio
    async def test_poll_without_device_flow_raises(self):
        """未启动 Device Flow 时 poll 应抛出异常"""
        auth = CopilotAuthManager()
        with pytest.raises(CopilotAuthError, match="not started"):
            await auth.poll_for_token()

    @pytest.mark.asyncio
    async def test_poll_expired_device_flow_raises(self):
        """Device Flow 过期应抛出异常"""
        auth = CopilotAuthManager()
        auth._device_flow = DeviceFlowState(
            device_code="dc-123",
            user_code="ABCD",
            started_at=time.time() - 1000,
            expires_in=900,
        )
        with pytest.raises(CopilotAuthError, match="expired"):
            await auth.poll_for_token()

    @pytest.mark.asyncio
    async def test_poll_pending(self):
        """轮询返回 authorization_pending"""
        auth = CopilotAuthManager()
        auth._device_flow = DeviceFlowState(
            device_code="dc-123",
            user_code="ABCD",
            started_at=time.time(),
            expires_in=900,
        )

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": "authorization_pending"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await auth.poll_for_token()
            assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_poll_slow_down(self):
        """轮询收到 slow_down 应增加 interval"""
        auth = CopilotAuthManager()
        auth._device_flow = DeviceFlowState(
            device_code="dc-123",
            user_code="ABCD",
            started_at=time.time(),
            expires_in=900,
            interval=5,
        )

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": "slow_down"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await auth.poll_for_token()
            assert result["status"] == "pending"
            assert auth._device_flow.interval == 10

    @pytest.mark.asyncio
    async def test_poll_access_denied(self):
        """用户拒绝授权应抛出异常"""
        auth = CopilotAuthManager()
        auth._device_flow = DeviceFlowState(
            device_code="dc-123",
            user_code="ABCD",
            started_at=time.time(),
            expires_in=900,
        )

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": "access_denied"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(CopilotAuthError, match="denied"):
                await auth.poll_for_token()

    @pytest.mark.asyncio
    async def test_poll_success(self):
        """轮询成功获取 access_token"""
        auth = CopilotAuthManager()
        auth._device_flow = DeviceFlowState(
            device_code="dc-123",
            user_code="ABCD",
            started_at=time.time(),
            expires_in=900,
        )

        # 模拟 GitHub OAuth 返回 access_token
        mock_oauth_resp = MagicMock()
        mock_oauth_resp.json.return_value = {"access_token": "gho_test_token"}

        # 模拟 Copilot token 获取
        mock_copilot_resp = MagicMock()
        mock_copilot_resp.status_code = 200
        mock_copilot_resp.json.return_value = {
            "token": "cpt_session_token",
            "expires_at": time.time() + 1800,
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_oauth_resp):
            with patch(
                "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_copilot_resp
            ):
                result = await auth.poll_for_token()
                assert result["status"] == "connected"
                assert auth.is_connected is True
                assert auth._github_token == "gho_test_token"
                assert len(result["models"]) > 0

    @pytest.mark.asyncio
    async def test_poll_success_but_copilot_token_fails(self):
        """OAuth 成功但 Copilot 令牌获取失败，仍返回 connected"""
        auth = CopilotAuthManager()
        auth._device_flow = DeviceFlowState(
            device_code="dc-123",
            user_code="ABCD",
            started_at=time.time(),
            expires_in=900,
        )

        mock_oauth_resp = MagicMock()
        mock_oauth_resp.json.return_value = {"access_token": "gho_test_token"}

        mock_copilot_resp = MagicMock()
        mock_copilot_resp.status_code = 500
        mock_copilot_resp.text = "Server error"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_oauth_resp):
            with patch(
                "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_copilot_resp
            ):
                result = await auth.poll_for_token()
                assert result["status"] == "connected"
                assert auth.is_connected is True

    @pytest.mark.asyncio
    async def test_poll_no_access_token_raises(self):
        """OAuth 返回无 access_token 应抛出异常"""
        auth = CopilotAuthManager()
        auth._device_flow = DeviceFlowState(
            device_code="dc-123",
            user_code="ABCD",
            started_at=time.time(),
            expires_in=900,
        )

        mock_resp = MagicMock()
        mock_resp.json.return_value = {}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(CopilotAuthError, match="No access_token"):
                await auth.poll_for_token()


class TestCopilotTokenManagement:
    """CopilotAuthManager 令牌管理"""

    @pytest.mark.asyncio
    async def test_fetch_copilot_token_success(self):
        """成功获取 Copilot 会话令牌"""
        auth = CopilotAuthManager()
        auth._github_token = "gho_test"
        auth._connected = True

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "token": "cpt_token",
            "expires_at": time.time() + 1800,
            "endpoints": {"api": "https://api.copilot.example.com"},
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            await auth._fetch_copilot_token()
            assert auth._copilot_token.token == "cpt_token"
            assert auth._copilot_token.endpoints["api"] == "https://api.copilot.example.com"

    @pytest.mark.asyncio
    async def test_fetch_copilot_token_401_disconnects(self):
        """Copilot 令牌获取返回 401 应断开连接"""
        auth = CopilotAuthManager()
        auth._github_token = "gho_expired"
        auth._connected = True

        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(CopilotAuthError, match="expired"):
                await auth._fetch_copilot_token()
            assert auth._connected is False
            assert auth._github_token == ""

    @pytest.mark.asyncio
    async def test_fetch_copilot_token_no_github_token(self):
        """没有 GitHub token 时应抛出异常"""
        auth = CopilotAuthManager()
        with pytest.raises(CopilotAuthError, match="No GitHub token"):
            await auth._fetch_copilot_token()

    @pytest.mark.asyncio
    async def test_ensure_valid_token_already_valid(self):
        """已有有效令牌时不刷新"""
        auth = CopilotAuthManager()
        auth._copilot_token = CopilotToken(token="cpt_valid", expires_at=time.time() + 600)

        token = await auth._ensure_valid_token()
        assert token == "cpt_valid"

    @pytest.mark.asyncio
    async def test_ensure_valid_token_refreshes(self):
        """令牌过期时自动刷新"""
        auth = CopilotAuthManager()
        auth._github_token = "gho_test"
        auth._connected = True
        auth._copilot_token = CopilotToken(token="cpt_old", expires_at=time.time() - 10)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "token": "cpt_new",
            "expires_at": time.time() + 1800,
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            token = await auth._ensure_valid_token()
            assert token == "cpt_new"


class TestCopilotChatAPI:
    """CopilotAuthManager.call_copilot_api"""

    @pytest.mark.asyncio
    async def test_call_not_connected_raises(self):
        """未连接时调用 API 应抛出 CopilotAuthError"""
        auth = CopilotAuthManager()
        with pytest.raises(CopilotAuthError, match="not connected"):
            await auth.call_copilot_api("gpt-4o", [{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_call_success(self):
        """成功调用 Copilot Chat API"""
        auth = CopilotAuthManager()
        auth._github_token = "gho_test"
        auth._connected = True
        auth._copilot_token = CopilotToken(token="cpt_valid", expires_at=time.time() + 600)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": '{"action": "call"}'}}]}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await auth.call_copilot_api("gpt-4o", [{"role": "user", "content": "test"}])
            assert result == '{"action": "call"}'

    @pytest.mark.asyncio
    async def test_call_no_choices_raises(self):
        """API 返回空 choices 应抛出 CopilotAPIError"""
        auth = CopilotAuthManager()
        auth._github_token = "gho_test"
        auth._connected = True
        auth._copilot_token = CopilotToken(token="cpt_valid", expires_at=time.time() + 600)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": []}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(CopilotAPIError, match="no choices"):
                await auth.call_copilot_api("gpt-4o", [{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_call_empty_content_raises(self):
        """API 返回空 content 应抛出 CopilotAPIError"""
        auth = CopilotAuthManager()
        auth._github_token = "gho_test"
        auth._connected = True
        auth._copilot_token = CopilotToken(token="cpt_valid", expires_at=time.time() + 600)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": ""}}]}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(CopilotAPIError, match="empty content"):
                await auth.call_copilot_api("gpt-4o", [{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_call_timeout_raises(self):
        """请求超时应抛出 CopilotAPIError"""
        import httpx as httpx_mod

        auth = CopilotAuthManager()
        auth._github_token = "gho_test"
        auth._connected = True
        auth._copilot_token = CopilotToken(token="cpt_valid", expires_at=time.time() + 600)

        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx_mod.TimeoutException("timed out"),
        ):
            with pytest.raises(CopilotAPIError, match="timed out"):
                await auth.call_copilot_api("gpt-4o", [{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_call_401_retries_with_refresh(self):
        """401 应触发令牌刷新并重试"""
        auth = CopilotAuthManager()
        auth._github_token = "gho_test"
        auth._connected = True
        auth._copilot_token = CopilotToken(token="cpt_valid", expires_at=time.time() + 600)

        # 第一次 post 返回 401，刷新令牌后第二次 post 成功
        mock_401 = MagicMock()
        mock_401.status_code = 401

        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.json.return_value = {"choices": [{"message": {"content": "retried ok"}}]}

        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {
            "token": "cpt_refreshed",
            "expires_at": time.time() + 1800,
        }

        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=[mock_401, mock_ok]
        ):
            with patch(
                "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_token_resp
            ):
                result = await auth.call_copilot_api(
                    "gpt-4o", [{"role": "user", "content": "test"}]
                )
                assert result == "retried ok"

    @pytest.mark.asyncio
    async def test_call_uses_endpoint_from_token(self):
        """使用 Copilot token 中的自定义端点"""
        auth = CopilotAuthManager()
        auth._github_token = "gho_test"
        auth._connected = True
        auth._copilot_token = CopilotToken(
            token="cpt_valid",
            expires_at=time.time() + 600,
            endpoints={"api": "https://custom.copilot.example.com"},
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}

        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp
        ) as mock_post:
            await auth.call_copilot_api("gpt-4o", [{"role": "user", "content": "test"}])
            # 验证使用了自定义端点
            call_args = mock_post.call_args
            url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
            assert "chat/completions" in str(url)


class TestCopilotDisconnect:
    """CopilotAuthManager.disconnect"""

    def test_disconnect_clears_all(self):
        """断开连接应清除所有凭据"""
        auth = CopilotAuthManager()
        auth._github_token = "gho_test"
        auth._connected = True
        auth._copilot_token = CopilotToken(token="cpt_token", expires_at=time.time() + 600)
        auth._device_flow = DeviceFlowState(device_code="dc-123")

        auth.disconnect()
        assert auth.is_connected is False
        assert auth._github_token == ""
        assert auth._copilot_token.token == ""
        assert auth._device_flow is None


class TestCopilotAvailableModels:
    """CopilotAuthManager.get_available_models"""

    def test_disconnected_returns_empty(self):
        """未连接时返回空列表"""
        auth = CopilotAuthManager()
        assert auth.get_available_models() == []

    def test_connected_returns_models(self):
        """连接后返回 Copilot 模型列表"""
        auth = CopilotAuthManager()
        auth._github_token = "gho_test"
        auth._connected = True
        models = auth.get_available_models()
        assert len(models) == 3
        model_ids = [m["id"] for m in models]
        assert "copilot-gpt4o" in model_ids
        assert "copilot-claude-sonnet" in model_ids


# ============================================================
#  config.py 单元测试
# ============================================================


class TestGetAvailableModels:
    """config.get_available_models — 动态过滤可用模型"""

    def test_no_providers_configured(self):
        """无 Provider 配置时返回空列表"""
        mock_pm = MagicMock()
        mock_pm.has_key.return_value = False
        mock_ca = MagicMock()
        mock_ca.is_connected = False

        with patch("app.services.provider_manager.get_provider_manager", return_value=mock_pm):
            with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_ca):
                models = get_available_models()
                assert models == []

    def test_openai_configured_only(self):
        """仅 OpenAI 配置时只返回 OpenAI 模型"""
        mock_pm = MagicMock()
        mock_pm.has_key.side_effect = lambda p: p == "openai"
        mock_ca = MagicMock()
        mock_ca.is_connected = False

        with patch("app.services.provider_manager.get_provider_manager", return_value=mock_pm):
            with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_ca):
                models = get_available_models()
                assert len(models) > 0
                for m in models:
                    assert m["provider"] == "openai"

    def test_copilot_connected_adds_models(self):
        """Copilot 连接后额外返回 Copilot 模型"""
        mock_pm = MagicMock()
        mock_pm.has_key.return_value = False
        mock_ca = MagicMock()
        mock_ca.is_connected = True

        with patch("app.services.provider_manager.get_provider_manager", return_value=mock_pm):
            with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_ca):
                models = get_available_models()
                assert len(models) == len(COPILOT_MODELS)
                for m in models:
                    assert m["provider"] == "github_copilot"

    def test_all_configured(self):
        """所有 Provider + Copilot 都配置时返回全部模型"""
        mock_pm = MagicMock()
        mock_pm.has_key.return_value = True
        mock_ca = MagicMock()
        mock_ca.is_connected = True

        with patch("app.services.provider_manager.get_provider_manager", return_value=mock_pm):
            with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_ca):
                models = get_available_models()
                non_copilot = {**OPENROUTER_MODELS, **SILICONFLOW_MODELS, **AZURE_OPENAI_MODELS}
                assert len(models) == len(non_copilot) + len(COPILOT_MODELS)


class TestGetModelConfig:
    """config.get_model_config — 查找模型配置"""

    def test_litellm_model(self):
        """查找 LiteLLM 模型"""
        config = get_model_config("openai-gpt4o")
        assert config is not None
        assert config["model"] == "gpt-4o"
        assert config["provider"] == "openai"

    def test_copilot_model(self):
        """查找 Copilot 模型"""
        config = get_model_config("copilot-gpt4o")
        assert config is not None
        assert config["model"] == "gpt-4o"
        assert config["provider"] == "github_copilot"

    def test_unknown_model(self):
        """查找不存在的模型返回 None"""
        config = get_model_config("nonexistent-model")
        assert config is None


class TestAllModelsRegistry:
    """ALL_MODELS 完整注册表"""

    def test_contains_litellm_models(self):
        """ALL_MODELS 包含所有 LiteLLM 模型"""
        non_copilot = {**OPENROUTER_MODELS, **SILICONFLOW_MODELS, **AZURE_OPENAI_MODELS}
        for model_id in non_copilot:
            assert model_id in ALL_MODELS

    def test_contains_copilot_models(self):
        """ALL_MODELS 包含所有 Copilot 模型"""
        for model_id in COPILOT_MODELS:
            assert model_id in ALL_MODELS

    def test_total_count(self):
        """ALL_MODELS 总数 = LiteLLM + Copilot"""
        non_copilot = {**OPENROUTER_MODELS, **SILICONFLOW_MODELS, **AZURE_OPENAI_MODELS}
        assert len(ALL_MODELS) == len(non_copilot) + len(COPILOT_MODELS)


# ============================================================
#  base_agent.py Copilot 路由测试
# ============================================================


class TestBaseAgentCopilotRouting:
    """BaseAgent.call_llm — Copilot 路由"""

    @pytest.mark.asyncio
    async def test_copilot_model_routes_to_call_copilot(self):
        """Copilot 模型应路由到 _call_copilot"""
        from app.agents.base_agent import BaseAgent

        agent = BaseAgent(
            agent_id="p1",
            name="TestBot",
            model_id="copilot-gpt4o",
        )

        with patch.object(
            agent, "_call_copilot", new_callable=AsyncMock, return_value='{"action":"call"}'
        ) as mock_copilot:
            result = await agent.call_llm([{"role": "user", "content": "test"}])
            mock_copilot.assert_called_once()
            assert result == '{"action":"call"}'

    @pytest.mark.asyncio
    async def test_litellm_model_does_not_route_to_copilot(self):
        """LiteLLM 模型不应路由到 _call_copilot"""
        from app.agents.base_agent import BaseAgent

        agent = BaseAgent(
            agent_id="p1",
            name="TestBot",
            model_id="openai-gpt4o",
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"action":"fold"}'

        with patch(
            "app.agents.base_agent.litellm.acompletion",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            with patch("app.agents.base_agent.get_settings") as mock_settings:
                settings = MagicMock()
                settings.llm_temperature = 0.7
                settings.llm_timeout = 5
                settings.llm_max_retries = 1
                settings.openai_api_key = "sk-test"
                settings.anthropic_api_key = ""
                settings.google_api_key = ""
                mock_settings.return_value = settings

                result = await agent.call_llm([{"role": "user", "content": "test"}])
                assert result == '{"action":"fold"}'

    @pytest.mark.asyncio
    async def test_call_copilot_retries_on_failure(self):
        """_call_copilot 在失败时应重试"""
        from app.agents.base_agent import BaseAgent

        agent = BaseAgent(
            agent_id="p1",
            name="TestBot",
            model_id="copilot-gpt4o",
        )

        mock_copilot = AsyncMock()
        mock_copilot.call_copilot_api = AsyncMock(
            side_effect=[CopilotAPIError("fail"), '{"action":"raise"}']
        )

        with patch("app.agents.base_agent.get_settings") as mock_settings:
            settings = MagicMock()
            settings.llm_max_retries = 2
            settings.llm_temperature = 0.7
            mock_settings.return_value = settings

            with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_copilot):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await agent._call_copilot(
                        "gpt-4o", [{"role": "user", "content": "test"}], 0.7
                    )
                    assert result == '{"action":"raise"}'
                    assert mock_copilot.call_copilot_api.call_count == 2

    @pytest.mark.asyncio
    async def test_call_copilot_exhausts_retries(self):
        """_call_copilot 重试耗尽后应抛出 LLMCallError"""
        from app.agents.base_agent import BaseAgent, LLMCallError

        agent = BaseAgent(
            agent_id="p1",
            name="TestBot",
            model_id="copilot-gpt4o",
        )

        mock_copilot = AsyncMock()
        mock_copilot.call_copilot_api = AsyncMock(side_effect=CopilotAPIError("always fails"))

        with patch("app.agents.base_agent.get_settings") as mock_settings:
            settings = MagicMock()
            settings.llm_max_retries = 2
            settings.llm_temperature = 0.7
            mock_settings.return_value = settings

            with patch("app.services.copilot_auth.get_copilot_auth", return_value=mock_copilot):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    with pytest.raises(LLMCallError, match="always fails"):
                        await agent._call_copilot(
                            "gpt-4o", [{"role": "user", "content": "test"}], 0.7
                        )


class TestBaseAgentModelValidation:
    """BaseAgent model_id 验证（含 Copilot 模型）"""

    def test_copilot_model_accepted(self):
        """Copilot 模型应被 BaseAgent 接受"""
        from app.agents.base_agent import BaseAgent

        agent = BaseAgent(
            agent_id="p1",
            name="TestBot",
            model_id="copilot-claude-sonnet",
        )
        assert agent.model_id == "copilot-claude-sonnet"

    def test_unknown_model_falls_back(self):
        """未知模型应回退到默认"""
        from app.agents.base_agent import BaseAgent

        agent = BaseAgent(
            agent_id="p1",
            name="TestBot",
            model_id="nonexistent-model",
        )
        assert agent.model_id == "openai-gpt4o-mini"


# ============================================================
#  Provider API 端点测试
# ============================================================


class TestProviderAPIGetProviders:
    """GET /api/providers — 获取所有 Provider 状态"""

    @pytest.mark.asyncio
    async def test_get_providers_returns_list(self):
        """应返回 Provider 状态列表"""
        mock_pm = MagicMock()
        mock_pm.get_all_status.return_value = [
            {"provider": "openai", "name": "OpenAI", "configured": False, "key_preview": None},
            {
                "provider": "anthropic",
                "name": "Anthropic",
                "configured": True,
                "key_preview": "ant-...xyz",
            },
            {
                "provider": "google",
                "name": "Google Gemini",
                "configured": False,
                "key_preview": None,
            },
        ]

        with patch("app.api.provider.get_provider_manager", return_value=mock_pm):
            app = _make_provider_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/providers")
                assert resp.status_code == 200
                data = resp.json()
                assert len(data) == 3


class TestProviderAPISetKey:
    """POST /api/providers/{provider}/key — 设置 API Key"""

    @pytest.mark.asyncio
    async def test_set_key_success(self):
        """成功设置 API Key"""
        mock_pm = MagicMock()

        with patch("app.api.provider.get_provider_manager", return_value=mock_pm):
            app = _make_provider_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/providers/openai/key",
                    json={"key": "sk-test-key"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["configured"] is True
                mock_pm.set_key.assert_called_once_with("openai", "sk-test-key")

    @pytest.mark.asyncio
    async def test_set_key_unknown_provider(self):
        """设置未知 Provider 应返回 404"""
        app = _make_provider_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/providers/unknown/key",
                json={"key": "some-key"},
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_set_key_empty(self):
        """设置空 Key 应返回 400"""
        app = _make_provider_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/providers/openai/key",
                json={"key": ""},
            )
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_set_key_whitespace_only(self):
        """设置纯空白 Key 应返回 400"""
        app = _make_provider_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/providers/openai/key",
                json={"key": "   "},
            )
            assert resp.status_code == 400


class TestProviderAPIVerifyKey:
    """POST /api/providers/{provider}/verify — 验证 API Key"""

    @pytest.mark.asyncio
    async def test_verify_key_success(self):
        """验证有效 Key"""
        mock_pm = MagicMock()
        mock_pm.verify_key = AsyncMock(return_value={"valid": True, "message": "OK"})

        with patch("app.api.provider.get_provider_manager", return_value=mock_pm):
            app = _make_provider_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/providers/openai/verify",
                    json={"key": "sk-test"},
                )
                assert resp.status_code == 200
                assert resp.json()["valid"] is True

    @pytest.mark.asyncio
    async def test_verify_key_unknown_provider(self):
        """验证未知 Provider 应返回 404"""
        app = _make_provider_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/providers/unknown/verify",
                json={},
            )
            assert resp.status_code == 404


class TestProviderAPIRemoveKey:
    """DELETE /api/providers/{provider}/key — 移除 API Key"""

    @pytest.mark.asyncio
    async def test_remove_key_success(self):
        """成功移除 API Key"""
        mock_pm = MagicMock()

        with patch("app.api.provider.get_provider_manager", return_value=mock_pm):
            app = _make_provider_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete("/api/providers/openai/key")
                assert resp.status_code == 200
                data = resp.json()
                assert data["configured"] is False
                mock_pm.remove_key.assert_called_once_with("openai")

    @pytest.mark.asyncio
    async def test_remove_key_unknown_provider(self):
        """移除未知 Provider 应返回 404"""
        app = _make_provider_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete("/api/providers/unknown/key")
            assert resp.status_code == 404


# ============================================================
#  Copilot API 端点测试
# ============================================================


class TestCopilotAPIConnect:
    """POST /api/copilot/connect — 发起 Device Flow"""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """成功发起 Device Flow"""
        mock_auth = MagicMock()
        mock_auth.start_device_flow = AsyncMock(
            return_value={
                "user_code": "ABCD-1234",
                "verification_uri": "https://github.com/login/device",
                "expires_in": 900,
            }
        )

        with patch("app.api.copilot.get_copilot_auth", return_value=mock_auth):
            app = _make_copilot_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/copilot/connect")
                assert resp.status_code == 200
                data = resp.json()
                assert data["user_code"] == "ABCD-1234"

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Device Flow 发起失败返回 500"""
        mock_auth = MagicMock()
        mock_auth.start_device_flow = AsyncMock(side_effect=CopilotAuthError("GitHub API error"))

        with patch("app.api.copilot.get_copilot_auth", return_value=mock_auth):
            app = _make_copilot_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/copilot/connect")
                assert resp.status_code == 500


class TestCopilotAPIPoll:
    """GET /api/copilot/poll — 轮询授权状态"""

    @pytest.mark.asyncio
    async def test_poll_pending(self):
        """轮询返回 pending"""
        mock_auth = MagicMock()
        mock_auth.poll_for_token = AsyncMock(return_value={"status": "pending"})

        with patch("app.api.copilot.get_copilot_auth", return_value=mock_auth):
            app = _make_copilot_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/copilot/poll")
                assert resp.status_code == 200
                assert resp.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_poll_connected(self):
        """轮询返回 connected"""
        mock_auth = MagicMock()
        mock_auth.poll_for_token = AsyncMock(
            return_value={
                "status": "connected",
                "models": [{"id": "copilot-gpt4o"}],
            }
        )

        with patch("app.api.copilot.get_copilot_auth", return_value=mock_auth):
            app = _make_copilot_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/copilot/poll")
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "connected"
                assert len(data["models"]) > 0

    @pytest.mark.asyncio
    async def test_poll_error(self):
        """轮询失败返回 400"""
        mock_auth = MagicMock()
        mock_auth.poll_for_token = AsyncMock(
            side_effect=CopilotAuthError("Device flow not started")
        )

        with patch("app.api.copilot.get_copilot_auth", return_value=mock_auth):
            app = _make_copilot_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/copilot/poll")
                assert resp.status_code == 400


class TestCopilotAPIStatus:
    """GET /api/copilot/status — 查询连接状态"""

    @pytest.mark.asyncio
    async def test_status_disconnected(self):
        """未连接时返回 connected=false"""
        mock_auth = MagicMock()
        mock_auth.get_status.return_value = {
            "connected": False,
            "has_valid_token": False,
            "models": [],
        }

        with patch("app.api.copilot.get_copilot_auth", return_value=mock_auth):
            app = _make_copilot_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/copilot/status")
                assert resp.status_code == 200
                assert resp.json()["connected"] is False

    @pytest.mark.asyncio
    async def test_status_connected(self):
        """已连接时返回 connected=true + 模型列表"""
        mock_auth = MagicMock()
        mock_auth.get_status.return_value = {
            "connected": True,
            "has_valid_token": True,
            "models": [{"id": "copilot-gpt4o"}],
        }

        with patch("app.api.copilot.get_copilot_auth", return_value=mock_auth):
            app = _make_copilot_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/copilot/status")
                assert resp.status_code == 200
                data = resp.json()
                assert data["connected"] is True
                assert len(data["models"]) > 0


class TestCopilotAPIDisconnect:
    """POST /api/copilot/disconnect — 断开连接"""

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """成功断开连接"""
        mock_auth = MagicMock()

        with patch("app.api.copilot.get_copilot_auth", return_value=mock_auth):
            app = _make_copilot_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/copilot/disconnect")
                assert resp.status_code == 200
                mock_auth.disconnect.assert_called_once()
                assert "disconnected" in resp.json()["message"].lower()
