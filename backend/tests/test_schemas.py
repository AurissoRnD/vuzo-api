"""Tests for Pydantic schema validation (app/models/schemas.py)."""
import pytest
from pydantic import ValidationError

from app.models.schemas import (
    ChatMessage,
    ChatCompletionRequest,
    TopUpRequest,
    ModelPricingItem,
)


class TestChatMessage:
    def test_valid_user_message(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_valid_system_message(self):
        msg = ChatMessage(role="system", content="You are helpful.")
        assert msg.role == "system"

    def test_none_content_allowed(self):
        msg = ChatMessage(role="assistant", content=None)
        assert msg.content is None


class TestChatCompletionRequest:
    def _base(self, **kwargs):
        defaults = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hi"}],
        }
        defaults.update(kwargs)
        return ChatCompletionRequest(**defaults)

    def test_minimal_valid_request(self):
        req = self._base()
        assert req.model == "gpt-4o-mini"
        assert len(req.messages) == 1

    def test_stream_defaults_to_false(self):
        req = self._base()
        assert req.stream is False

    def test_optional_fields_default_to_none(self):
        req = self._base()
        assert req.temperature is None
        assert req.max_tokens is None
        assert req.stop is None

    def test_stop_as_string(self):
        req = self._base(stop="\n")
        assert req.stop == "\n"

    def test_stop_as_list(self):
        req = self._base(stop=["\n", "END"])
        assert req.stop == ["\n", "END"]

    def test_missing_model_raises(self):
        with pytest.raises(ValidationError):
            ChatCompletionRequest(messages=[{"role": "user", "content": "hi"}])

    def test_missing_messages_raises(self):
        with pytest.raises(ValidationError):
            ChatCompletionRequest(model="gpt-4o")


class TestTopUpRequest:
    def test_valid_amount(self):
        req = TopUpRequest(amount=10.0)
        assert req.amount == 10.0

    def test_zero_amount_rejected(self):
        with pytest.raises(ValidationError):
            TopUpRequest(amount=0)

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            TopUpRequest(amount=-5.0)


class TestModelPricingItem:
    def test_valid_item(self):
        item = ModelPricingItem(
            provider="openai",
            model_name="gpt-4o-mini",
            input_price_per_million=0.15,
            output_price_per_million=0.60,
            vuzo_input_price_per_million=0.18,
            vuzo_output_price_per_million=0.72,
            vuzo_markup_percent=20.0,
        )
        assert item.provider == "openai"
        assert item.vuzo_markup_percent == 20.0
