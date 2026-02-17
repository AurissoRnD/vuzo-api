from app.models.database import get_supabase


def log_usage(
    user_id: str,
    api_key_id: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    provider_cost: float,
    vuzo_cost: float,
    response_time_ms: int,
    status_code: int = 200,
) -> dict:
    """Log a single request's token usage and cost."""
    sb = get_supabase()
    result = sb.table("usage_logs").insert({
        "user_id": user_id,
        "api_key_id": api_key_id,
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "provider_cost": provider_cost,
        "vuzo_cost": vuzo_cost,
        "response_time_ms": response_time_ms,
        "status_code": status_code,
    }).execute()
    return result.data[0] if result.data else {}


def get_usage_logs(
    user_id: str,
    model: str | None = None,
    provider: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Get paginated usage logs with optional filters."""
    sb = get_supabase()
    query = (
        sb.table("usage_logs")
        .select("*")
        .eq("user_id", user_id)
    )
    if model:
        query = query.eq("model", model)
    if provider:
        query = query.eq("provider", provider)

    result = (
        query.order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data or []


def get_usage_summary(user_id: str) -> dict:
    """
    Get aggregated usage summary for a user.
    Since Supabase client doesn't support raw aggregate SQL easily,
    we fetch all records and aggregate in Python.
    For production, consider a Supabase RPC function.
    """
    sb = get_supabase()
    result = (
        sb.table("usage_logs")
        .select("input_tokens, output_tokens, total_tokens, provider_cost, vuzo_cost")
        .eq("user_id", user_id)
        .execute()
    )
    rows = result.data or []

    summary = {
        "total_requests": len(rows),
        "total_input_tokens": sum(r["input_tokens"] for r in rows),
        "total_output_tokens": sum(r["output_tokens"] for r in rows),
        "total_tokens": sum(r["total_tokens"] for r in rows),
        "total_provider_cost": sum(float(r["provider_cost"]) for r in rows),
        "total_vuzo_cost": sum(float(r["vuzo_cost"]) for r in rows),
    }
    return summary
