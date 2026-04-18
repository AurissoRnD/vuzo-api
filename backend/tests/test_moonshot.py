"""Tests for Moonshot provider error handling (app/services/providers/moonshot.py).

Focuses on the recently added httpx error → HTTPException conversion so that
upstream failures surface as proper 502/503 responses instead of bare 500s.
"""
import json
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.services.providers.moonshot import MoonshotProvider
from app.models.schemas import ChatCompletionRequest, ChatMessage


def _request(stream: bool = False) -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model="kimi-k2.5",
        messages=[ChatMessage(role="user", content="ping")],
        stream=stream,
        max_tokens=8,
    )


def _mock_http_client(status: int, body: dict | str) -> MagicMock:
    """Return a mock httpx.AsyncClient whose post() raises or returns the given status."""
    client = MagicMock()
    if isinstance(body, dict):
        raw_body = json.dumps(body).encode()
    else:
        raw_body = body.encode()

    if status >= 400:
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = body if isinstance(body, dict) else {}
        resp.text = body if isinstance(body, str) else json.dumps(body)
        error = httpx.HTTPStatusError("upstream error", request=MagicMock(), response=resp)
        client.post = AsyncMock(side_effect=error)
    else:
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = body
        resp.raise_for_status = MagicMock()
        client.post = AsyncMock(return_value=resp)

    return client


class TestMoonshotModelSupport:
    def test_kimi_k25_supported(self):
        assert MoonshotProvider().model_supported("kimi-k2.5")

    def test_unknown_model_not_supported(self):
        assert not MoonshotProvider().model_supported("gpt-4o")

    def test_empty_string_not_supported(self):
        assert not MoonshotProvider().model_supported("")


class TestMoonshotChatCompletion:
    @pytest.mark.asyncio
    async def test_success_returns_usage_result(self):
        response_body = {
            "id": "chatcmpl-abc",
            "choices": [{"message": {"role": "assistant", "content": "pong"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
        }
        client = _mock_http_client(200, response_body)

        with patch("app.services.providers.moonshot.get_http_client", return_value=client):
            result = await MoonshotProvider().chat_completion(_request(), "sk-valid")

        assert result.input_tokens == 5
        assert result.output_tokens == 1
        assert result.provider_response["id"] == "chatcmpl-abc"

    @pytest.mark.asyncio
    async def test_401_raises_502(self):
        error_body = {"error": {"message": "Invalid Authentication", "type": "invalid_authentication_error"}}
        client = _mock_http_client(401, error_body)

        with patch("app.services.providers.moonshot.get_http_client", return_value=client):
            with pytest.raises(HTTPException) as exc_info:
                await MoonshotProvider().chat_completion(_request(), "sk-bad")

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail["upstream_status"] == 401

    @pytest.mark.asyncio
    async def test_429_raises_502(self):
        error_body = {"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}}
        client = _mock_http_client(429, error_body)

        with patch("app.services.providers.moonshot.get_http_client", return_value=client):
            with pytest.raises(HTTPException) as exc_info:
                await MoonshotProvider().chat_completion(_request(), "sk-test")

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail["upstream_status"] == 429

    @pytest.mark.asyncio
    async def test_request_error_raises_503(self):
        client = MagicMock()
        client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch("app.services.providers.moonshot.get_http_client", return_value=client):
            with pytest.raises(HTTPException) as exc_info:
                await MoonshotProvider().chat_completion(_request(), "sk-test")

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_missing_usage_defaults_to_zero(self):
        response_body = {
            "id": "chatcmpl-xyz",
            "choices": [{"message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
        }
        client = _mock_http_client(200, response_body)

        with patch("app.services.providers.moonshot.get_http_client", return_value=client):
            result = await MoonshotProvider().chat_completion(_request(), "sk-valid")

        assert result.input_tokens == 0
        assert result.output_tokens == 0


class TestMoonshotBuildPayload:
    def test_required_fields_present(self):
        req = _request()
        payload = MoonshotProvider()._build_payload(req, stream=False)
        assert payload["model"] == "kimi-k2.5"
        assert payload["stream"] is False
        assert len(payload["messages"]) == 1

    def test_optional_fields_omitted_when_none(self):
        req = ChatCompletionRequest(
            model="kimi-k2.5",
            messages=[ChatMessage(role="user", content="ping")],
        )
        payload = MoonshotProvider()._build_payload(req, stream=False)
        assert "temperature" not in payload
        assert "max_tokens" not in payload

    def test_max_tokens_included_when_set(self):
        req = _request()
        req.max_tokens = 16
        payload = MoonshotProvider()._build_payload(req, stream=False)
        assert payload["max_tokens"] == 16

    def test_stream_flag_forwarded(self):
        req = _request(stream=True)
        payload = MoonshotProvider()._build_payload(req, stream=True)
        assert payload["stream"] is True
