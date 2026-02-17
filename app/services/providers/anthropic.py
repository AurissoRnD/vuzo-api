import json
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
        return ProviderUsageResult(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            provider_response=data,
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

        async with client.stream(
            "POST",
            f"{ANTHROPIC_BASE_URL}/messages",
            json=payload,
            headers=self._headers(api_key),
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    if line.startswith("event: "):
                        yield f"{line}\n", None
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

                if event_type == "message_delta":
                    delta_usage = chunk.get("usage", {})
                    output_tokens = delta_usage.get("output_tokens", 0)
                    usage_result = ProviderUsageResult(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        provider_response=chunk,
                    )

                sse_line = f"data: {data_str}\n\n"
                yield sse_line, (
                    usage_result if event_type == "message_stop" else None
                )

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
