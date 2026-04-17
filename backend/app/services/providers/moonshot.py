import json
import time
from typing import AsyncIterator

import httpx
from fastapi import HTTPException

from app.models.database import get_http_client
from app.models.schemas import ChatCompletionRequest, ProviderUsageResult
from app.services.providers.base import BaseProvider

MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"

MOONSHOT_MODELS = {
    "kimi-k2.5",
}


class MoonshotProvider(BaseProvider):

    def model_supported(self, model: str) -> bool:
        return model in MOONSHOT_MODELS

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> ProviderUsageResult:
        client = get_http_client()

        payload = self._build_payload(request, stream=False)

        try:
            resp = await client.post(
                f"{MOONSHOT_BASE_URL}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            try:
                detail = exc.response.json()
            except Exception:
                detail = exc.response.text or "Moonshot upstream error"
            raise HTTPException(status_code=502, detail={"upstream_status": status, "upstream_error": detail})
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Could not reach Moonshot: {exc}")

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

        usage_result: ProviderUsageResult | None = None

        try:
            stream_ctx = client.stream(
                "POST",
                f"{MOONSHOT_BASE_URL}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
        except httpx.RequestError as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\ndata: [DONE]\n\n", None
            return

        async with stream_ctx as resp:
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                try:
                    detail = exc.response.json()
                except Exception:
                    detail = exc.response.text or "Moonshot upstream error"
                yield f"data: {json.dumps({'error': {'upstream_status': status, 'upstream_error': detail}})}\n\ndata: [DONE]\n\n", None
                return

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
