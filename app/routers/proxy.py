import time
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatCompletionRequest, AuthContext
from app.middleware.auth import validate_api_key
from app.services.pricing_service import get_model_pricing, get_provider_api_key
from app.services.billing_service import check_sufficient_balance, deduct_credits
from app.services.usage_service import log_usage
from app.services.providers.openai import OpenAIProvider
from app.services.providers.xai import XAIProvider
from app.services.providers.google import GoogleProvider
from app.services.providers.anthropic import AnthropicProvider
from app.utils.pricing import calculate_cost

router = APIRouter()

_openai = OpenAIProvider()
_xai = XAIProvider()
_google = GoogleProvider()
_anthropic = AnthropicProvider()
_providers = [_openai, _xai, _google, _anthropic]


def _get_provider(model: str):
    for p in _providers:
        if p.model_supported(model):
            return p
    return None


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    auth: AuthContext = Depends(validate_api_key),
):
    pricing = get_model_pricing(request.model)
    provider_name: str = pricing["provider"]

    check_sufficient_balance(auth.user_id)

    provider = _get_provider(request.model)
    if provider is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"No provider found for model '{request.model}'")

    master_key = get_provider_api_key(provider_name)

    if request.stream:
        return StreamingResponse(
            _stream_response(request, provider, master_key, pricing, auth),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    start = time.time()
    result = await provider.chat_completion(request, master_key)
    elapsed_ms = int((time.time() - start) * 1000)

    provider_cost, vuzo_cost = calculate_cost(
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        input_price_per_million=float(pricing["input_price_per_million"]),
        output_price_per_million=float(pricing["output_price_per_million"]),
        vuzo_markup_percent=float(pricing["vuzo_markup_percent"]),
    )

    deduct_credits(
        auth.user_id,
        vuzo_cost,
        f"{request.model}: {result.input_tokens}in + {result.output_tokens}out tokens",
    )

    log_usage(
        user_id=auth.user_id,
        api_key_id=auth.api_key_id,
        provider=provider_name,
        model=request.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        provider_cost=provider_cost,
        vuzo_cost=vuzo_cost,
        response_time_ms=elapsed_ms,
    )

    response_data = result.provider_response
    if "usage" not in response_data:
        response_data["usage"] = {
            "prompt_tokens": result.input_tokens,
            "completion_tokens": result.output_tokens,
            "total_tokens": result.input_tokens + result.output_tokens,
        }

    return response_data


async def _stream_response(request, provider, master_key, pricing, auth: AuthContext):
    start = time.time()
    final_usage = None

    async for chunk_str, usage in provider.chat_completion_stream(request, master_key):
        if usage is not None:
            final_usage = usage
        yield chunk_str

    elapsed_ms = int((time.time() - start) * 1000)

    if final_usage:
        provider_cost, vuzo_cost = calculate_cost(
            input_tokens=final_usage.input_tokens,
            output_tokens=final_usage.output_tokens,
            input_price_per_million=float(pricing["input_price_per_million"]),
            output_price_per_million=float(pricing["output_price_per_million"]),
            vuzo_markup_percent=float(pricing["vuzo_markup_percent"]),
        )

        deduct_credits(
            auth.user_id,
            vuzo_cost,
            f"{request.model}: {final_usage.input_tokens}in + {final_usage.output_tokens}out tokens (stream)",
        )

        log_usage(
            user_id=auth.user_id,
            api_key_id=auth.api_key_id,
            provider=pricing["provider"],
            model=request.model,
            input_tokens=final_usage.input_tokens,
            output_tokens=final_usage.output_tokens,
            provider_cost=provider_cost,
            vuzo_cost=vuzo_cost,
            response_time_ms=elapsed_ms,
        )
