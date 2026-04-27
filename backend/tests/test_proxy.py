"""Tests for POST /v1/chat/completions (app/routers/proxy.py)."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.middleware.auth import validate_api_key
from app.models.schemas import AuthContext, ProviderUsageResult

MOCK_AUTH = AuthContext(user_id="user-123", api_key_id="key-456", rate_limit_rpm=60)

MOCK_PRICING = {
    "provider": "moonshot",
    "model_name": "kimi-k2.6",
    "input_price_per_million": 0.14,
    "output_price_per_million": 0.14,
    "vuzo_markup_percent": 20.0,
}

MOCK_PROVIDER_RESPONSE = {
    "id": "chatcmpl-test",
    "object": "chat.completion",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "pong"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
}

CHAT_BODY = {
    "model": "kimi-k2.6",
    "messages": [{"role": "user", "content": "Say: pong"}],
    "stream": False,
    "max_tokens": 8,
}


async def _mock_auth():
    return MOCK_AUTH


@pytest.fixture
def client():
    app.dependency_overrides[validate_api_key] = _mock_auth
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestChatCompletionsSuccess:
    def test_returns_200_with_provider_response(self, client):
        mock_result = ProviderUsageResult(
            input_tokens=5,
            output_tokens=1,
            provider_response=MOCK_PROVIDER_RESPONSE,
        )
        with patch("app.routers.proxy.get_model_pricing", return_value=MOCK_PRICING), \
             patch("app.routers.proxy.check_sufficient_balance", return_value=1.0), \
             patch("app.routers.proxy.get_provider_api_key", return_value="sk-master"), \
             patch("app.routers.proxy.deduct_credits"), \
             patch("app.routers.proxy.log_usage"), \
             patch("app.routers.proxy._get_provider") as mock_get_provider:

            mock_provider = MagicMock()
            mock_provider.chat_completion = AsyncMock(return_value=mock_result)
            mock_get_provider.return_value = mock_provider

            resp = client.post("/v1/chat/completions", json=CHAT_BODY)

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "chatcmpl-test"

    def test_usage_added_when_missing_from_provider(self, client):
        response_without_usage = {k: v for k, v in MOCK_PROVIDER_RESPONSE.items() if k != "usage"}
        mock_result = ProviderUsageResult(
            input_tokens=5, output_tokens=1, provider_response=response_without_usage
        )
        with patch("app.routers.proxy.get_model_pricing", return_value=MOCK_PRICING), \
             patch("app.routers.proxy.check_sufficient_balance", return_value=1.0), \
             patch("app.routers.proxy.get_provider_api_key", return_value="sk-master"), \
             patch("app.routers.proxy.deduct_credits"), \
             patch("app.routers.proxy.log_usage"), \
             patch("app.routers.proxy._get_provider") as mock_get_provider:

            mock_provider = MagicMock()
            mock_provider.chat_completion = AsyncMock(return_value=mock_result)
            mock_get_provider.return_value = mock_provider

            resp = client.post("/v1/chat/completions", json=CHAT_BODY)

        assert resp.status_code == 200
        assert "usage" in resp.json()
        assert resp.json()["usage"]["prompt_tokens"] == 5


class TestChatCompletionsErrors:
    def test_unknown_model_returns_400(self, client):
        from fastapi import HTTPException
        with patch("app.routers.proxy.get_model_pricing",
                   side_effect=HTTPException(status_code=400, detail="Model not found")):
            resp = client.post("/v1/chat/completions", json={**CHAT_BODY, "model": "unknown-model"})
        assert resp.status_code == 400

    def test_insufficient_credits_returns_402(self, client):
        from fastapi import HTTPException
        with patch("app.routers.proxy.get_model_pricing", return_value=MOCK_PRICING), \
             patch("app.routers.proxy.check_sufficient_balance",
                   side_effect=HTTPException(status_code=402, detail="Insufficient credits")):
            resp = client.post("/v1/chat/completions", json=CHAT_BODY)
        assert resp.status_code == 402

    def test_no_provider_returns_400(self, client):
        with patch("app.routers.proxy.get_model_pricing", return_value=MOCK_PRICING), \
             patch("app.routers.proxy.check_sufficient_balance", return_value=1.0), \
             patch("app.routers.proxy.get_provider_api_key", return_value="sk-master"), \
             patch("app.routers.proxy._get_provider", return_value=None):
            resp = client.post("/v1/chat/completions", json=CHAT_BODY)
        assert resp.status_code == 400

    def test_upstream_502_propagated(self, client):
        from fastapi import HTTPException
        with patch("app.routers.proxy.get_model_pricing", return_value=MOCK_PRICING), \
             patch("app.routers.proxy.check_sufficient_balance", return_value=1.0), \
             patch("app.routers.proxy.get_provider_api_key", return_value="sk-master"), \
             patch("app.routers.proxy._get_provider") as mock_get_provider:

            mock_provider = MagicMock()
            mock_provider.chat_completion = AsyncMock(
                side_effect=HTTPException(
                    status_code=502,
                    detail={"upstream_status": 401, "upstream_error": "Invalid Auth"}
                )
            )
            mock_get_provider.return_value = mock_provider

            resp = client.post("/v1/chat/completions", json=CHAT_BODY)

        assert resp.status_code == 502

    def test_missing_model_field_returns_422(self, client):
        resp = client.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "hi"}]})
        assert resp.status_code == 422

    def test_missing_messages_field_returns_422(self, client):
        resp = client.post("/v1/chat/completions", json={"model": "kimi-k2.6"})
        assert resp.status_code == 422
