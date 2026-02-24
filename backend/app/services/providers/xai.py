import json
from typing import AsyncIterator

from app.models.database import get_http_client
from app.models.schemas import ChatCompletionRequest, ProviderUsageResult
from app.services.providers.base import BaseProvider

XAI_BASE_URL = "https://api.x.ai/v1"

XAI_MODELS = {
    "grok-3",
    "grok-3-mini",
    "grok-2",
}


class XAIProvider(BaseProvider):
    """
    xAI Grok provider. Uses an OpenAI-compatible API format,
    so request/response handling mirrors the OpenAI provider.
    """

    def model_supported(self, model: str) -> bool:
        return model in XAI_MODELS

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> ProviderUsageResult:
        client = get_http_client()

        payload = self._build_payload(request, stream=False)

        resp = await client.post(
            f"{XAI_BASE_URL}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        usage = data.get("usage", {})
        return ProviderUsageResult(
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            provider_response=data,
        )

    async def chat_completion_stream(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> AsyncIterator[tuple[str, ProviderUsageResult | None]]:
        client = get_http_client()

        payload = self._build_payload(request, stream=True)
        payload["stream_options"] = {"include_usage": True}

        usage_result: ProviderUsageResult | None = None

        async with client.stream(
            "POST",
            f"{XAI_BASE_URL}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    yield "data: [DONE]\n\n", usage_result
                    break

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if "usage" in chunk and chunk["usage"]:
                    u = chunk["usage"]
                    usage_result = ProviderUsageResult(
                        input_tokens=u.get("prompt_tokens", 0),
                        output_tokens=u.get("completion_tokens", 0),
                        provider_response=chunk,
                    )

                yield f"data: {data_str}\n\n", None

    def _build_payload(self, request: ChatCompletionRequest, stream: bool) -> dict:
        payload: dict = {
            "model": request.model,
            "messages": [m.model_dump(exclude_none=True) for m in request.messages],
            "stream": stream,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.stop is not None:
            payload["stop"] = request.stop
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty
        return payload
