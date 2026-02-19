import json
import time
import uuid
from typing import AsyncIterator

from app.models.database import get_http_client
from app.models.schemas import ChatCompletionRequest, ProviderUsageResult
from app.services.providers.base import BaseProvider

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

GOOGLE_MODELS = {
    "gemini-2.0-flash",
    "gemini-3-flash",
}


class GoogleProvider(BaseProvider):

    def model_supported(self, model: str) -> bool:
        return model in GOOGLE_MODELS

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> ProviderUsageResult:
        client = get_http_client()

        payload = self._build_payload(request)

        resp = await client.post(
            f"{GEMINI_BASE_URL}/{request.model}:generateContent?key={api_key}",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

        usage_meta = data.get("usageMetadata", {})
        input_tokens = usage_meta.get("promptTokenCount", 0)
        output_tokens = usage_meta.get("candidatesTokenCount", 0)
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

        payload = self._build_payload(request)
        usage_result: ProviderUsageResult | None = None
        stream_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())

        async with client.stream(
            "POST",
            f"{GEMINI_BASE_URL}/{request.model}:streamGenerateContent?alt=sse&key={api_key}",
            json=payload,
            headers={"Content-Type": "application/json"},
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

                if "usageMetadata" in chunk:
                    um = chunk["usageMetadata"]
                    usage_result = ProviderUsageResult(
                        input_tokens=um.get("promptTokenCount", 0),
                        output_tokens=um.get("candidatesTokenCount", 0),
                        provider_response=chunk,
                    )

                has_finish = False
                finish_reason = None
                for candidate in chunk.get("candidates", []):
                    if candidate.get("finishReason"):
                        has_finish = True
                        finish_reason = "stop"
                        break

                text = ""
                for candidate in chunk.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        text += part.get("text", "")

                openai_chunk = {
                    "id": stream_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": text} if text else {},
                        "finish_reason": finish_reason,
                    }],
                }
                yield f"data: {json.dumps(openai_chunk)}\n\n", (usage_result if has_finish else None)

        yield "data: [DONE]\n\n", None

    def _normalize_response(self, data: dict, model: str, input_tokens: int, output_tokens: int) -> dict:
        text = ""
        finish_reason = "stop"
        candidates = data.get("candidates", [])
        if candidates:
            candidate = candidates[0]
            for part in candidate.get("content", {}).get("parts", []):
                text += part.get("text", "")
            raw_finish = candidate.get("finishReason", "STOP")
            finish_reason = "stop" if raw_finish in ("STOP", "MAX_TOKENS") else raw_finish.lower()

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
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

    def _build_payload(self, request: ChatCompletionRequest) -> dict:
        contents = []
        system_instruction = None

        for m in request.messages:
            if m.role == "system":
                system_instruction = m.content if isinstance(m.content, str) else str(m.content)
            else:
                role = "user" if m.role == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": m.content if isinstance(m.content, str) else str(m.content)}],
                })

        payload: dict = {"contents": contents}

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        generation_config: dict = {}
        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.top_p is not None:
            generation_config["topP"] = request.top_p
        if request.stop is not None:
            generation_config["stopSequences"] = (
                request.stop if isinstance(request.stop, list) else [request.stop]
            )
        if generation_config:
            payload["generationConfig"] = generation_config

        return payload
