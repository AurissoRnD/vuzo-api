import time
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatCompletionRequest, AuthContext
from app.middleware.auth import validate_api_key
from app.services.pricing_service import get_model_pricing, get_provider_api_key
from app.services.billing_service import check_sufficient_balance, deduct_credits, get_total_topups
from app.services.usage_service import log_usage
from app.services.providers.moonshot import MoonshotProvider
from app.services.ws_manager import manager as ws_manager
from app.utils.pricing import calculate_cost

router = APIRouter()

_moonshot = MoonshotProvider()
_providers = [_moonshot]

_LOW_BALANCE_PCT = 0.20            # warn when balance < 20% of total lifetime topups
_LOW_TOKEN_PCT = 0.90              # warn when 90% of token limit used


def _get_provider(model: str):
    for p in _providers:
        if p.model_supported(model):
            return p
    return None


async def _broadcast_usage(
    auth: AuthContext,
    model: str,
    input_tokens: int,
    output_tokens: int,
    vuzo_cost: float,
    new_balance: float,
):
    """Push usage event + threshold alerts to the user's WebSocket if connected."""
    if not ws_manager.is_connected(auth.user_id):
        return

    total_tokens = input_tokens + output_tokens

    await ws_manager.send(auth.user_id, {
        "type": "usage",
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost": round(vuzo_cost, 6),
        "balance": round(new_balance, 6),
    })

    # Token limit alerts
    if auth.token_limit:
        new_tokens_used = auth.tokens_used + total_tokens
        pct = new_tokens_used / auth.token_limit

        if new_tokens_used >= auth.token_limit:
            await ws_manager.send(auth.user_id, {
                "type": "out_of_tokens",
                "tokens_used": new_tokens_used,
                "token_limit": auth.token_limit,
                "message": "Token limit reached. Top up to continue.",
            })
        elif pct >= _LOW_TOKEN_PCT and auth.tokens_used / auth.token_limit < _LOW_TOKEN_PCT:
            await ws_manager.send(auth.user_id, {
                "type": "low_tokens",
                "tokens_used": new_tokens_used,
                "token_limit": auth.token_limit,
                "percent_used": round(pct * 100, 1),
                "message": f"You have used {round(pct * 100, 1)}% of your token limit.",
            })

    # Balance alerts — threshold is 20% of lifetime topups
    total_topups = get_total_topups(auth.user_id)
    low_balance_threshold = total_topups * _LOW_BALANCE_PCT

    if new_balance < low_balance_threshold:
        await ws_manager.send(auth.user_id, {
            "type": "low_balance",
            "balance": round(new_balance, 6),
            "threshold": round(low_balance_threshold, 2),
            "message": f"Your balance is below ${low_balance_threshold:.2f}. Top up to avoid interruption.",
        })


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

    new_balance = deduct_credits(
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

    await _broadcast_usage(
        auth=auth,
        model=request.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        vuzo_cost=vuzo_cost,
        new_balance=new_balance,
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

        new_balance = deduct_credits(
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

        await _broadcast_usage(
            auth=auth,
            model=request.model,
            input_tokens=final_usage.input_tokens,
            output_tokens=final_usage.output_tokens,
            vuzo_cost=vuzo_cost,
            new_balance=new_balance,
        )
