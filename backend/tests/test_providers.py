"""Tests for provider response normalisation (Google + Anthropic).

These tests exercise the pure _normalize_response() helpers directly —
no HTTP calls, no Supabase, no env vars required.
"""
import time
import pytest
from unittest.mock import patch

from app.services.providers.google import GoogleProvider
from app.services.providers.anthropic import AnthropicProvider


# ── Google / Gemini ─────────────────────────────────────────────────────────

class TestGoogleNormalize:
    def setup_method(self):
        self.provider = GoogleProvider()
        self.model = "gemini-2.0-flash"

    def _native(self, text="Hello!", finish="STOP", input_tok=10, output_tok=5):
        return {
            "candidates": [{
                "content": {"parts": [{"text": text}]},
                "finishReason": finish,
            }],
            "usageMetadata": {
                "promptTokenCount": input_tok,
                "candidatesTokenCount": output_tok,
            },
        }

    def test_returns_openai_shape(self):
        out = self.provider._normalize_response(self._native(), self.model, 10, 5)
        assert out["object"] == "chat.completion"
        assert "choices" in out
        assert "usage" in out
        assert out["choices"][0]["message"]["role"] == "assistant"

    def test_text_extracted_correctly(self):
        out = self.provider._normalize_response(self._native("Howdy"), self.model, 1, 1)
        assert out["choices"][0]["message"]["content"] == "Howdy"

    def test_finish_reason_stop(self):
        out = self.provider._normalize_response(self._native(finish="STOP"), self.model, 1, 1)
        assert out["choices"][0]["finish_reason"] == "stop"

    def test_finish_reason_max_tokens(self):
        out = self.provider._normalize_response(self._native(finish="MAX_TOKENS"), self.model, 1, 1)
        assert out["choices"][0]["finish_reason"] == "stop"

    def test_usage_fields(self):
        out = self.provider._normalize_response(self._native(input_tok=20, output_tok=8), self.model, 20, 8)
        assert out["usage"]["prompt_tokens"] == 20
        assert out["usage"]["completion_tokens"] == 8
        assert out["usage"]["total_tokens"] == 28

    def test_id_prefixed_with_chatcmpl(self):
        out = self.provider._normalize_response(self._native(), self.model, 1, 1)
        assert out["id"].startswith("chatcmpl-")

    def test_model_field_preserved(self):
        out = self.provider._normalize_response(self._native(), self.model, 1, 1)
        assert out["model"] == self.model

    def test_empty_candidates(self):
        out = self.provider._normalize_response({"candidates": [], "usageMetadata": {}}, self.model, 0, 0)
        assert out["choices"][0]["message"]["content"] == ""

    def test_multipart_text_concatenated(self):
        data = {
            "candidates": [{
                "content": {"parts": [{"text": "Hello"}, {"text": " world"}]},
                "finishReason": "STOP",
            }],
        }
        out = self.provider._normalize_response(data, self.model, 0, 0)
        assert out["choices"][0]["message"]["content"] == "Hello world"


# ── Anthropic / Claude ───────────────────────────────────────────────────────

class TestAnthropicNormalize:
    def setup_method(self):
        self.provider = AnthropicProvider()
        self.model = "claude-sonnet-4-20250514"

    def _native(self, text="Hi there!", stop_reason="end_turn", input_tok=12, output_tok=6):
        return {
            "id": "msg_abc123",
            "content": [{"type": "text", "text": text}],
            "stop_reason": stop_reason,
            "usage": {"input_tokens": input_tok, "output_tokens": output_tok},
        }

    def test_returns_openai_shape(self):
        out = self.provider._normalize_response(self._native(), self.model, 12, 6)
        assert out["object"] == "chat.completion"
        assert "choices" in out
        assert "usage" in out

    def test_text_extracted_correctly(self):
        out = self.provider._normalize_response(self._native("Sure!"), self.model, 1, 1)
        assert out["choices"][0]["message"]["content"] == "Sure!"

    def test_finish_reason_end_turn_maps_to_stop(self):
        out = self.provider._normalize_response(self._native(stop_reason="end_turn"), self.model, 1, 1)
        assert out["choices"][0]["finish_reason"] == "stop"

    def test_finish_reason_max_tokens_maps_to_stop(self):
        out = self.provider._normalize_response(self._native(stop_reason="max_tokens"), self.model, 1, 1)
        assert out["choices"][0]["finish_reason"] == "stop"

    def test_usage_fields(self):
        out = self.provider._normalize_response(self._native(input_tok=30, output_tok=15), self.model, 30, 15)
        assert out["usage"]["prompt_tokens"] == 30
        assert out["usage"]["completion_tokens"] == 15
        assert out["usage"]["total_tokens"] == 45

    def test_id_uses_anthropic_msg_id(self):
        out = self.provider._normalize_response(self._native(), self.model, 1, 1)
        assert out["id"] == "chatcmpl-msg_abc123"

    def test_model_field_preserved(self):
        out = self.provider._normalize_response(self._native(), self.model, 1, 1)
        assert out["model"] == self.model

    def test_non_text_blocks_ignored(self):
        data = {
            "id": "msg_xyz",
            "content": [
                {"type": "tool_use", "id": "tool1", "name": "search", "input": {}},
                {"type": "text", "text": "Here is the answer"},
            ],
            "stop_reason": "end_turn",
        }
        out = self.provider._normalize_response(data, self.model, 5, 5)
        assert out["choices"][0]["message"]["content"] == "Here is the answer"

    def test_empty_content(self):
        data = {"id": "msg_empty", "content": [], "stop_reason": "end_turn"}
        out = self.provider._normalize_response(data, self.model, 0, 0)
        assert out["choices"][0]["message"]["content"] == ""
