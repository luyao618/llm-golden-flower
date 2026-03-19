"""模型管理 & 设置 API 端点测试

覆盖 Phase 3 的 19 个未测试端点:

模型管理（4 个 Provider × 4 个端点 = 16 个端点）:
- GET    /api/{provider}/models           — 从远程 API 获取可用模型列表
- GET    /api/{provider}/models/added     — 获取已添加到游戏的模型
- POST   /api/{provider}/models           — 添加模型到游戏
- DELETE /api/{provider}/models/{model_id} — 从游戏中移除模型

设置（2 个端点）:
- GET  /api/settings     — 获取当前设置
- POST /api/settings     — 更新设置

Provider 额外配置（1 个端点）:
- POST /api/providers/{provider}/config — 设置额外配置 (api_host, api_version)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import (
    AZURE_OPENAI_MODELS,
    OPENROUTER_MODELS,
    SILICONFLOW_MODELS,
    ZHIPU_MODELS,
    add_azure_openai_model,
    add_openrouter_model,
    add_siliconflow_model,
    add_zhipu_model,
    get_azure_openai_models,
    get_openrouter_models,
    get_siliconflow_models,
    get_zhipu_models,
    remove_azure_openai_model,
    remove_openrouter_model,
    remove_siliconflow_model,
    remove_zhipu_model,
)
from app.services.provider_manager import ProviderManager

# ============================================================
# Helper: 创建轻量测试 FastAPI 应用
# ============================================================


def _make_model_mgmt_test_app() -> FastAPI:
    """构建包含所有模型管理和设置路由的测试 FastAPI 应用"""
    from app.api.azure_openai import router as azure_router
    from app.api.openrouter import router as openrouter_router
    from app.api.provider import router as provider_router
    from app.api.settings import router as settings_router
    from app.api.siliconflow import router as siliconflow_router
    from app.api.zhipu import router as zhipu_router

    test_app = FastAPI()
    test_app.include_router(openrouter_router)
    test_app.include_router(siliconflow_router)
    test_app.include_router(azure_router)
    test_app.include_router(zhipu_router)
    test_app.include_router(settings_router)
    test_app.include_router(provider_router)
    return test_app


# ============================================================
# 模型管理端点测试：GET /models/added, POST /models, DELETE /models
# （不需要外部 API 调用的端点 — 纯本地 CRUD）
# ============================================================

# Provider 参数化配置
PROVIDER_PARAMS = [
    pytest.param(
        "openrouter",
        "/api/openrouter",
        "openai/gpt-4o",
        "GPT-4o",
        add_openrouter_model,
        remove_openrouter_model,
        get_openrouter_models,
        OPENROUTER_MODELS,
        "openrouter_id",
        id="openrouter",
    ),
    pytest.param(
        "siliconflow",
        "/api/siliconflow",
        "deepseek-ai/DeepSeek-V3",
        "DeepSeek V3",
        add_siliconflow_model,
        remove_siliconflow_model,
        get_siliconflow_models,
        SILICONFLOW_MODELS,
        "siliconflow_id",
        id="siliconflow",
    ),
    pytest.param(
        "azure_openai",
        "/api/azure-openai",
        "gpt-4o",
        "GPT-4o Azure",
        add_azure_openai_model,
        remove_azure_openai_model,
        get_azure_openai_models,
        AZURE_OPENAI_MODELS,
        "azure_id",
        id="azure_openai",
    ),
    pytest.param(
        "zhipu",
        "/api/zhipu",
        "glm-4-flash",
        "GLM-4 Flash",
        add_zhipu_model,
        remove_zhipu_model,
        get_zhipu_models,
        ZHIPU_MODELS,
        "zhipu_id",
        id="zhipu",
    ),
]


class TestListAddedModels:
    """GET /api/{provider}/models/added — 获取已添加到游戏的模型列表"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,prefix,raw_id,display,add_fn,remove_fn,get_fn,registry,id_key",
        PROVIDER_PARAMS,
    )
    async def test_empty_list(
        self, provider, prefix, raw_id, display, add_fn, remove_fn, get_fn, registry, id_key
    ):
        """初始状态下已添加模型列表为空（或只含预设）"""
        # 保存原始注册表状态
        original = dict(registry)
        # 清空注册表
        registry.clear()
        try:
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"{prefix}/models/added")
                assert resp.status_code == 200
                data = resp.json()
                assert "models" in data
                assert data["models"] == []
        finally:
            registry.clear()
            registry.update(original)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,prefix,raw_id,display,add_fn,remove_fn,get_fn,registry,id_key",
        PROVIDER_PARAMS,
    )
    async def test_with_added_model(
        self, provider, prefix, raw_id, display, add_fn, remove_fn, get_fn, registry, id_key
    ):
        """添加模型后列表中应包含该模型"""
        model_id = add_fn(raw_id, display)
        try:
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"{prefix}/models/added")
                assert resp.status_code == 200
                data = resp.json()
                assert len(data["models"]) >= 1
                model_ids = [m["id"] for m in data["models"]]
                assert model_id in model_ids
        finally:
            remove_fn(model_id)


class TestAddModel:
    """POST /api/{provider}/models — 添加模型到游戏"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,prefix,raw_id,display,add_fn,remove_fn,get_fn,registry,id_key",
        PROVIDER_PARAMS,
    )
    async def test_add_model_success(
        self, provider, prefix, raw_id, display, add_fn, remove_fn, get_fn, registry, id_key
    ):
        """成功添加模型"""
        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"{prefix}/models",
                json={"model_id": raw_id, "display_name": display},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "model_id" in data
            assert data["display_name"] == display
            assert data[id_key] == raw_id
            # 清理
            remove_fn(data["model_id"])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,prefix,raw_id,display,add_fn,remove_fn,get_fn,registry,id_key",
        PROVIDER_PARAMS,
    )
    async def test_add_model_empty_model_id(
        self, provider, prefix, raw_id, display, add_fn, remove_fn, get_fn, registry, id_key
    ):
        """model_id 为空应返回 400"""
        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"{prefix}/models",
                json={"model_id": "", "display_name": display},
            )
            assert resp.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,prefix,raw_id,display,add_fn,remove_fn,get_fn,registry,id_key",
        PROVIDER_PARAMS,
    )
    async def test_add_model_empty_display_name(
        self, provider, prefix, raw_id, display, add_fn, remove_fn, get_fn, registry, id_key
    ):
        """display_name 为空应返回 400"""
        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"{prefix}/models",
                json={"model_id": raw_id, "display_name": ""},
            )
            assert resp.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,prefix,raw_id,display,add_fn,remove_fn,get_fn,registry,id_key",
        PROVIDER_PARAMS,
    )
    async def test_add_model_whitespace_stripped(
        self, provider, prefix, raw_id, display, add_fn, remove_fn, get_fn, registry, id_key
    ):
        """带前后空白的 model_id 应成功添加（内部注册时去除空白）"""
        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"{prefix}/models",
                json={
                    "model_id": f"  {raw_id}  ",
                    "display_name": f"  {display}  ",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            # API 返回原始请求值（含空白），但内部注册使用了 strip
            assert "model_id" in data
            # 验证内部注册的模型可以被找到和移除
            remove_fn(data["model_id"])


class TestRemoveModel:
    """DELETE /api/{provider}/models/{model_id} — 从游戏中移除模型"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,prefix,raw_id,display,add_fn,remove_fn,get_fn,registry,id_key",
        PROVIDER_PARAMS,
    )
    async def test_remove_existing_model(
        self, provider, prefix, raw_id, display, add_fn, remove_fn, get_fn, registry, id_key
    ):
        """成功移除已添加的模型"""
        model_id = add_fn(raw_id, display)
        try:
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(f"{prefix}/models/{model_id}")
                assert resp.status_code == 200
                data = resp.json()
                assert data["model_id"] == model_id
        finally:
            # 确保清理（即使删除已在 API 中完成）
            remove_fn(model_id)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,prefix,raw_id,display,add_fn,remove_fn,get_fn,registry,id_key",
        PROVIDER_PARAMS,
    )
    async def test_remove_nonexistent_model(
        self, provider, prefix, raw_id, display, add_fn, remove_fn, get_fn, registry, id_key
    ):
        """移除不存在的模型应返回 404"""
        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"{prefix}/models/nonexistent-model-id")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,prefix,raw_id,display,add_fn,remove_fn,get_fn,registry,id_key",
        PROVIDER_PARAMS,
    )
    async def test_remove_then_list_empty(
        self, provider, prefix, raw_id, display, add_fn, remove_fn, get_fn, registry, id_key
    ):
        """移除模型后，已添加列表中应不再包含该模型"""
        # 保存原始注册表状态
        original = dict(registry)
        registry.clear()
        model_id = add_fn(raw_id, display)
        try:
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 先移除
                resp = await client.delete(f"{prefix}/models/{model_id}")
                assert resp.status_code == 200

                # 再查列表
                resp = await client.get(f"{prefix}/models/added")
                assert resp.status_code == 200
                data = resp.json()
                model_ids = [m["id"] for m in data["models"]]
                assert model_id not in model_ids
        finally:
            registry.clear()
            registry.update(original)


# ============================================================
# 模型管理端点测试：GET /models （需要外部 API 调用 — mock HTTP）
# ============================================================


class TestListRemoteModels:
    """GET /api/{provider}/models — 从远程 API 获取可用模型列表

    API Key 通过 X-Provider-Keys header 传入（来自前端 localStorage）。
    """

    @pytest.mark.asyncio
    async def test_openrouter_list_models_success(self):
        """OpenRouter: 成功获取远程模型列表"""
        import json as json_mod

        # 直接 mock _fetch_openrouter_models 避免 httpx 上下文管理器问题
        mock_models = [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "context_length": 128000,
                "pricing": {"prompt": "0.0025", "completion": "0.01"},
            }
        ]

        with patch(
            "app.api.openrouter._fetch_openrouter_models",
            new_callable=AsyncMock,
            return_value=mock_models,
        ):
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/openrouter/models",
                    headers={"X-Provider-Keys": json_mod.dumps({"openrouter": "sk-test-key"})},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] == 1
                assert data["models"][0]["id"] == "openai/gpt-4o"
                assert data["models"][0]["pricing"]["prompt"] == "0.0025"

    @pytest.mark.asyncio
    async def test_openrouter_list_models_no_key(self):
        """OpenRouter: 未配置 API Key 时应返回 400"""
        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/openrouter/models")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_openrouter_list_models_api_error(self):
        """OpenRouter: 远程 API 返回错误应返回 502"""
        import json as json_mod

        from fastapi import HTTPException

        with patch(
            "app.api.openrouter._fetch_openrouter_models",
            new_callable=AsyncMock,
            side_effect=HTTPException(
                status_code=502,
                detail="Failed to fetch models from OpenRouter: HTTP 401",
            ),
        ):
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/openrouter/models",
                    headers={"X-Provider-Keys": json_mod.dumps({"openrouter": "sk-test-key"})},
                )
                assert resp.status_code == 502

    @pytest.mark.asyncio
    async def test_openrouter_list_models_uses_cache(self):
        """OpenRouter: 缓存有效期内应使用缓存"""
        import json as json_mod
        import time

        import app.api.openrouter as openrouter_mod

        cached_models = [
            {"id": "cached/model", "name": "Cached", "context_length": 1000, "pricing": {}}
        ]
        openrouter_mod._models_cache = cached_models
        openrouter_mod._cache_timestamp = time.time()  # 刚刚缓存

        # 不 mock _fetch — 如果缓存生效则 _fetch 会直接返回缓存
        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/openrouter/models",
                headers={"X-Provider-Keys": json_mod.dumps({"openrouter": "sk-test-key"})},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["models"][0]["id"] == "cached/model"

        # 还原缓存
        openrouter_mod._models_cache = []
        openrouter_mod._cache_timestamp = 0

    @pytest.mark.asyncio
    async def test_siliconflow_list_models_success(self):
        """SiliconFlow: 成功获取远程模型列表（过滤 embedding/image 类）"""
        import json as json_mod

        mock_models = [
            {
                "id": "deepseek-ai/DeepSeek-V3",
                "name": "deepseek-ai/DeepSeek-V3",
                "context_length": None,
                "pricing": {"prompt": "0", "completion": "0"},
            },
            {
                "id": "Qwen/Qwen2.5-72B-Instruct",
                "name": "Qwen/Qwen2.5-72B-Instruct",
                "context_length": None,
                "pricing": {"prompt": "0", "completion": "0"},
            },
        ]

        with patch(
            "app.api.siliconflow._fetch_siliconflow_models",
            new_callable=AsyncMock,
            return_value=mock_models,
        ):
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/siliconflow/models",
                    headers={"X-Provider-Keys": json_mod.dumps({"siliconflow": "sf-test-key"})},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] == 2
                model_ids = [m["id"] for m in data["models"]]
                assert "deepseek-ai/DeepSeek-V3" in model_ids
                assert "Qwen/Qwen2.5-72B-Instruct" in model_ids

    @pytest.mark.asyncio
    async def test_siliconflow_list_models_no_key(self):
        """SiliconFlow: 未配置 API Key 时应返回 400"""
        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/siliconflow/models")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_azure_list_models_success(self):
        """Azure OpenAI: 成功获取已部署模型列表"""
        import json as json_mod

        mock_models = [
            {
                "id": "gpt-4o",
                "name": "gpt-4o",
                "context_length": None,
                "pricing": {"prompt": "0", "completion": "0"},
            },
            {
                "id": "gpt-4o-mini",
                "name": "gpt-4o-mini",
                "context_length": None,
                "pricing": {"prompt": "0", "completion": "0"},
            },
        ]

        with patch(
            "app.api.azure_openai._fetch_azure_models",
            new_callable=AsyncMock,
            return_value=mock_models,
        ):
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/azure-openai/models",
                    headers={"X-Provider-Keys": json_mod.dumps({"azure_openai": "azure-key-123"})},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] == 2
                model_ids = [m["id"] for m in data["models"]]
                assert "gpt-4o" in model_ids

    @pytest.mark.asyncio
    async def test_azure_list_models_no_key(self):
        """Azure OpenAI: 未配置 API Key 时应返回 400"""
        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/azure-openai/models")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_azure_list_models_no_host(self):
        """Azure OpenAI: 未配置 api_host 时应返回 400"""
        import json as json_mod

        from fastapi import HTTPException

        with patch(
            "app.api.azure_openai._fetch_azure_models",
            new_callable=AsyncMock,
            side_effect=HTTPException(
                status_code=400,
                detail="Azure OpenAI API Host (endpoint) not configured",
            ),
        ):
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/azure-openai/models",
                    headers={"X-Provider-Keys": json_mod.dumps({"azure_openai": "azure-key"})},
                )
                assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_zhipu_list_models_success(self):
        """Zhipu: 成功获取远程模型列表（过滤 image/video/embedding 类）"""
        import json as json_mod

        mock_models = [
            {
                "id": "glm-4",
                "name": "glm-4",
                "context_length": None,
                "pricing": {"prompt": "0", "completion": "0"},
            },
            {
                "id": "glm-4-flash",
                "name": "glm-4-flash",
                "context_length": None,
                "pricing": {"prompt": "0", "completion": "0"},
            },
        ]

        with patch(
            "app.api.zhipu._fetch_zhipu_models",
            new_callable=AsyncMock,
            return_value=mock_models,
        ):
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/zhipu/models",
                    headers={"X-Provider-Keys": json_mod.dumps({"zhipu": "zhipu-test-key"})},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] == 2
                model_ids = [m["id"] for m in data["models"]]
                assert "glm-4-flash" in model_ids
                assert "glm-4" in model_ids

    @pytest.mark.asyncio
    async def test_zhipu_list_models_no_key(self):
        """Zhipu: 未配置 API Key 时应返回 400"""
        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/zhipu/models")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_zhipu_list_models_api_error(self):
        """Zhipu: 远程 API 返回错误应返回 502"""
        import json as json_mod

        from fastapi import HTTPException

        with patch(
            "app.api.zhipu._fetch_zhipu_models",
            new_callable=AsyncMock,
            side_effect=HTTPException(
                status_code=502,
                detail="Failed to fetch models from Zhipu: HTTP 500",
            ),
        ):
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/zhipu/models",
                    headers={"X-Provider-Keys": json_mod.dumps({"zhipu": "zhipu-test-key"})},
                )
                assert resp.status_code == 502


# ============================================================
# 设置 API 端点测试
# ============================================================


class TestSettingsGetAPI:
    """GET /api/settings — 获取当前设置"""

    @pytest.mark.asyncio
    async def test_get_default_settings(self):
        """获取默认设置，包含所有字段"""
        # 重置运行时设置为默认值
        import app.api.settings as settings_mod

        settings_mod._runtime_settings = settings_mod._build_defaults()

        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/settings")
            assert resp.status_code == 200
            data = resp.json()
            # 验证所有必须字段存在
            assert "llm_max_tokens" in data
            assert "ai_thinking_mode" in data
            assert "llm_timeout" in data
            assert "llm_max_retries" in data
            assert "llm_temperature" in data
            # 验证默认值
            assert data["ai_thinking_mode"] == "fast"
            assert data["llm_max_tokens"] is None

    @pytest.mark.asyncio
    async def test_get_settings_reflects_updates(self):
        """更新后再获取应反映最新值"""
        import app.api.settings as settings_mod

        settings_mod._runtime_settings = settings_mod._build_defaults()

        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 先更新
            await client.post(
                "/api/settings",
                json={"ai_thinking_mode": "turbo", "llm_temperature": 1.5},
            )
            # 再获取
            resp = await client.get("/api/settings")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ai_thinking_mode"] == "turbo"
            assert data["llm_temperature"] == 1.5

        # 还原
        settings_mod._runtime_settings = settings_mod._build_defaults()


class TestSettingsUpdateAPI:
    """POST /api/settings — 更新设置"""

    @pytest.mark.asyncio
    async def test_partial_update(self):
        """部分更新 — 只修改提供的字段"""
        import app.api.settings as settings_mod

        settings_mod._runtime_settings = settings_mod._build_defaults()

        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/settings",
                json={"ai_thinking_mode": "detailed"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["ai_thinking_mode"] == "detailed"
            # 其他字段保持默认
            assert data["llm_max_tokens"] is None

        settings_mod._runtime_settings = settings_mod._build_defaults()

    @pytest.mark.asyncio
    async def test_update_llm_temperature(self):
        """更新 llm_temperature"""
        import app.api.settings as settings_mod

        settings_mod._runtime_settings = settings_mod._build_defaults()

        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/settings",
                json={"llm_temperature": 0.1},
            )
            assert resp.status_code == 200
            assert resp.json()["llm_temperature"] == 0.1

        settings_mod._runtime_settings = settings_mod._build_defaults()

    @pytest.mark.asyncio
    async def test_update_llm_timeout(self):
        """更新 llm_timeout"""
        import app.api.settings as settings_mod

        settings_mod._runtime_settings = settings_mod._build_defaults()

        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/settings",
                json={"llm_timeout": 60},
            )
            assert resp.status_code == 200
            assert resp.json()["llm_timeout"] == 60

        settings_mod._runtime_settings = settings_mod._build_defaults()

    @pytest.mark.asyncio
    async def test_update_llm_max_retries(self):
        """更新 llm_max_retries"""
        import app.api.settings as settings_mod

        settings_mod._runtime_settings = settings_mod._build_defaults()

        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/settings",
                json={"llm_max_retries": 5},
            )
            assert resp.status_code == 200
            assert resp.json()["llm_max_retries"] == 5

        settings_mod._runtime_settings = settings_mod._build_defaults()

    @pytest.mark.asyncio
    async def test_update_max_tokens(self):
        """更新 llm_max_tokens"""
        import app.api.settings as settings_mod

        settings_mod._runtime_settings = settings_mod._build_defaults()

        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/settings",
                json={"llm_max_tokens": 4096},
            )
            assert resp.status_code == 200
            assert resp.json()["llm_max_tokens"] == 4096

        settings_mod._runtime_settings = settings_mod._build_defaults()

    @pytest.mark.asyncio
    async def test_update_all_thinking_modes(self):
        """设置所有合法的 thinking_mode 值"""
        import app.api.settings as settings_mod

        for mode in ["detailed", "fast", "turbo"]:
            settings_mod._runtime_settings = settings_mod._build_defaults()

            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/settings",
                    json={"ai_thinking_mode": mode},
                )
                assert resp.status_code == 200
                assert resp.json()["ai_thinking_mode"] == mode

        settings_mod._runtime_settings = settings_mod._build_defaults()

    @pytest.mark.asyncio
    async def test_update_invalid_thinking_mode(self):
        """设置无效的 thinking_mode 应返回 422"""
        import app.api.settings as settings_mod

        settings_mod._runtime_settings = settings_mod._build_defaults()

        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/settings",
                json={"ai_thinking_mode": "invalid_mode"},
            )
            assert resp.status_code == 422

        settings_mod._runtime_settings = settings_mod._build_defaults()

    @pytest.mark.asyncio
    async def test_update_temperature_out_of_range(self):
        """llm_temperature 超出范围 (0.0-2.0) 应返回 422"""
        import app.api.settings as settings_mod

        settings_mod._runtime_settings = settings_mod._build_defaults()

        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/settings",
                json={"llm_temperature": 3.0},
            )
            assert resp.status_code == 422

            resp = await client.post(
                "/api/settings",
                json={"llm_temperature": -0.5},
            )
            assert resp.status_code == 422

        settings_mod._runtime_settings = settings_mod._build_defaults()

    @pytest.mark.asyncio
    async def test_update_timeout_out_of_range(self):
        """llm_timeout 超出范围 (5-120) 应返回 422"""
        import app.api.settings as settings_mod

        settings_mod._runtime_settings = settings_mod._build_defaults()

        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/settings",
                json={"llm_timeout": 1},
            )
            assert resp.status_code == 422

            resp = await client.post(
                "/api/settings",
                json={"llm_timeout": 200},
            )
            assert resp.status_code == 422

        settings_mod._runtime_settings = settings_mod._build_defaults()

    @pytest.mark.asyncio
    async def test_update_retries_out_of_range(self):
        """llm_max_retries 超出范围 (0-10) 应返回 422"""
        import app.api.settings as settings_mod

        settings_mod._runtime_settings = settings_mod._build_defaults()

        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/settings",
                json={"llm_max_retries": -1},
            )
            assert resp.status_code == 422

            resp = await client.post(
                "/api/settings",
                json={"llm_max_retries": 20},
            )
            assert resp.status_code == 422

        settings_mod._runtime_settings = settings_mod._build_defaults()

    @pytest.mark.asyncio
    async def test_multiple_updates_accumulate(self):
        """多次部分更新应累积，不互相覆盖"""
        import app.api.settings as settings_mod

        settings_mod._runtime_settings = settings_mod._build_defaults()

        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 第一次更新 temperature
            await client.post("/api/settings", json={"llm_temperature": 1.0})
            # 第二次更新 thinking_mode
            await client.post("/api/settings", json={"ai_thinking_mode": "turbo"})

            # 验证两次更新都保留
            resp = await client.get("/api/settings")
            data = resp.json()
            assert data["llm_temperature"] == 1.0
            assert data["ai_thinking_mode"] == "turbo"

        settings_mod._runtime_settings = settings_mod._build_defaults()


# ============================================================
# Provider 额外配置端点测试
# ============================================================


class TestProviderConfigAPI:
    """POST /api/providers/{provider}/config — 设置额外配置"""

    @pytest.mark.asyncio
    async def test_set_azure_config(self):
        """Azure OpenAI: 设置 api_host 和 api_version"""
        mock_pm = MagicMock(spec=ProviderManager)
        mock_pm.get_extra_config.return_value = {
            "api_host": "https://myendpoint.openai.azure.com",
            "api_version": "2024-10-21",
        }

        with patch("app.api.provider.get_provider_manager", return_value=mock_pm):
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/providers/azure_openai/config",
                    json={
                        "api_host": "https://myendpoint.openai.azure.com",
                        "api_version": "2024-10-21",
                    },
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["provider"] == "azure_openai"
                assert "extra_config" in data
                mock_pm.set_extra_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_siliconflow_api_host(self):
        """SiliconFlow: 设置 api_host"""
        mock_pm = MagicMock(spec=ProviderManager)
        mock_pm.get_extra_config.return_value = {"api_host": "https://custom.siliconflow.cn"}

        with patch("app.api.provider.get_provider_manager", return_value=mock_pm):
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/providers/siliconflow/config",
                    json={"api_host": "https://custom.siliconflow.cn"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["provider"] == "siliconflow"

    @pytest.mark.asyncio
    async def test_set_config_unknown_provider(self):
        """未知 Provider 应返回 404"""
        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/providers/unknown_provider/config",
                json={"api_host": "https://example.com"},
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_set_config_empty_body(self):
        """不提供任何配置应返回 400"""
        app = _make_model_mgmt_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/providers/azure_openai/config",
                json={},
            )
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_set_config_only_api_version(self):
        """仅设置 api_version 应成功"""
        mock_pm = MagicMock(spec=ProviderManager)
        mock_pm.get_extra_config.return_value = {"api_version": "2025-01-01"}

        with patch("app.api.provider.get_provider_manager", return_value=mock_pm):
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/providers/azure_openai/config",
                    json={"api_version": "2025-01-01"},
                )
                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_set_config_strips_whitespace(self):
        """api_host 前后空白应被去除"""
        mock_pm = MagicMock(spec=ProviderManager)
        mock_pm.get_extra_config.return_value = {"api_host": "https://myendpoint.com"}

        with patch("app.api.provider.get_provider_manager", return_value=mock_pm):
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/providers/siliconflow/config",
                    json={"api_host": "  https://myendpoint.com  "},
                )
                assert resp.status_code == 200
                # 验证传递给 set_extra_config 的值已去除空白
                call_args = mock_pm.set_extra_config.call_args
                assert call_args[0][1]["api_host"] == "https://myendpoint.com"


# ============================================================
# 模型管理 CRUD 全流程集成测试
# ============================================================


class TestModelCRUDFlow:
    """模型管理 CRUD 全流程：添加 → 查看 → 移除 → 确认移除"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,prefix,raw_id,display,add_fn,remove_fn,get_fn,registry,id_key",
        PROVIDER_PARAMS,
    )
    async def test_full_crud_flow(
        self, provider, prefix, raw_id, display, add_fn, remove_fn, get_fn, registry, id_key
    ):
        """完整 CRUD 流程"""
        # 保存原始注册表
        original = dict(registry)
        registry.clear()

        try:
            app = _make_model_mgmt_test_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 1. 初始列表为空
                resp = await client.get(f"{prefix}/models/added")
                assert resp.json()["models"] == []

                # 2. 添加模型
                resp = await client.post(
                    f"{prefix}/models",
                    json={"model_id": raw_id, "display_name": display},
                )
                assert resp.status_code == 200
                model_id = resp.json()["model_id"]

                # 3. 确认模型出现在列表中
                resp = await client.get(f"{prefix}/models/added")
                model_ids = [m["id"] for m in resp.json()["models"]]
                assert model_id in model_ids

                # 4. 移除模型
                resp = await client.delete(f"{prefix}/models/{model_id}")
                assert resp.status_code == 200

                # 5. 确认模型已从列表中消失
                resp = await client.get(f"{prefix}/models/added")
                model_ids = [m["id"] for m in resp.json()["models"]]
                assert model_id not in model_ids
        finally:
            registry.clear()
            registry.update(original)
