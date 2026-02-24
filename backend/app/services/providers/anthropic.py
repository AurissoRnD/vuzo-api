import json
import time
import uuid
from typing import AsyncIterator

from app.models.database import get_http_client
from app.models.schemas import ChatCompletionRequest, ProviderUsageResult
from app.services.providers.base import BaseProvider

ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"

ANTHROPIC_MODELS = {
    "claude-sonnet-4-20250514",
    "claude-haiku-4-5",
    "claude-opus-4-5",
}


class AnthropicProvider(BaseProvider):

    def model_supported(self, model: str) -> bool:
        return model in ANTHROPIC_MODELS

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> ProviderUsageResult:
        client = get_http_client()

        payload = self._build_payload(request, stream=False)

        resp = await client.post(
            f"{ANTHROPIC_BASE_URL}/messages",
            json=payload,
            headers=self._headers(api_key),
        )
        resp.raise_for_status()
        data = resp.json()

        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        return ProviderUsageResult(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_response=self._normalize_response(data, request.model, input_tokens, output_tokens),
        )

    async def chat_completion_stream(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> AsyncIterator[tuple[str, ProviderUsageResult | None]]:
        client = get_http_client()

        payload = self._build_payload(request, stream=True)
        usage_result: ProviderUsageResult | None = None
        input_tokens = 0
        output_tokens = 0
        stream_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())

        async with client.stream(
            "POST",
            f"{ANTHROPIC_BASE_URL}/messages",
            json=payload,
            headers=self._headers(api_key),
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue

                data_str = line[6:]
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                event_type = chunk.get("type", "")

                if event_type == "message_start":
                    msg_usage = chunk.get("message", {}).get("usage", {})
                    input_tokens = msg_usage.get("input_tokens", 0)
                    openai_chunk = {
                        "id": stream_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}],
                    }
                    yield f"data: {json.dumps(openai_chunk)}\n\n", None

                elif event_type == "content_block_delta":
                    text = chunk.get("delta", {}).get("text", "")
                    openai_chunk = {
                        "id": stream_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
                    }
                    yield f"data: {json.dumps(openai_chunk)}\n\n", None

                elif event_type == "message_delta":
                    delta_usage = chunk.get("usage", {})
                    output_tokens = delta_usage.get("output_tokens", 0)
                    usage_result = ProviderUsageResult(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        provider_response=chunk,
                    )
                    openai_chunk = {
                        "id": stream_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    }
                    yield f"data: {json.dumps(openai_chunk)}\n\n", None

                elif event_type == "message_stop":
                    yield "data: [DONE]\n\n", usage_result

    def _normalize_response(self, data: dict, model: str, input_tokens: int, output_tokens: int) -> dict:
        text = ""
        content_blocks = data.get("content", [])
        for block in content_blocks:
            if block.get("type") == "text":
                text += block.get("text", "")

        stop_reason = data.get("stop_reason", "end_turn")
        finish_reason = "stop" if stop_reason in ("end_turn", "max_tokens") else stop_reason

        return {
            "id": f"chatcmpl-{data.get('id', uuid.uuid4().hex[:24])}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": finish_reason,
            }],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }

    def _headers(self, api_key: str) -> dict:
        return {
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

    def _build_payload(self, request: ChatCompletionRequest, stream: bool) -> dict:
        system_msg = None
        messages = []
        for m in request.messages:
            if m.role == "system":
                system_msg = m.content if isinstance(m.content, str) else str(m.content)
            else:
                messages.append({"role": m.role, "content": m.content})

        payload: dict = {
            "model": request.model,
            "messages": messages,
            "stream": stream,
        }
        if system_msg:
            payload["system"] = system_msg
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        else:
            payload["max_tokens"] = 4096
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop is not None:
            payload["stop_sequences"] = (
                request.stop if isinstance(request.stop, list) else [request.stop]
            )
        return payload
