from collections import defaultdict

from app.models.database import get_supabase


def _apply_date_filters(query, start_date: str | None, end_date: str | None):
    if start_date:
        query = query.gte("created_at", start_date)
    if end_date:
        query = query.lte("created_at", end_date)
    return query


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
    start_date: str | None = None,
    end_date: str | None = None,
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
    query = _apply_date_filters(query, start_date, end_date)

    result = (
        query.order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data or []


def get_usage_summary(
    user_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """
    Get aggregated usage summary for a user.
    Optionally scoped to a date range.
    """
    sb = get_supabase()
    query = (
        sb.table("usage_logs")
        .select("input_tokens, output_tokens, total_tokens, provider_cost, vuzo_cost")
        .eq("user_id", user_id)
    )
    query = _apply_date_filters(query, start_date, end_date)
    result = query.execute()
    rows = result.data or []

    return {
        "total_requests": len(rows),
        "total_input_tokens": sum(r["input_tokens"] for r in rows),
        "total_output_tokens": sum(r["output_tokens"] for r in rows),
        "total_tokens": sum(r["total_tokens"] for r in rows),
        "total_provider_cost": sum(float(r["provider_cost"]) for r in rows),
        "total_vuzo_cost": sum(float(r["vuzo_cost"]) for r in rows),
    }


def get_daily_usage(
    user_id: str,
    model: str | None = None,
    provider: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Aggregate usage logs by day + model."""
    sb = get_supabase()
    query = (
        sb.table("usage_logs")
        .select("created_at, model, provider, input_tokens, output_tokens, vuzo_cost")
        .eq("user_id", user_id)
    )
    if model:
        query = query.eq("model", model)
    if provider:
        query = query.eq("provider", provider)
    query = _apply_date_filters(query, start_date, end_date)
    result = query.order("created_at", desc=True).execute()
    rows = result.data or []

    buckets: dict[tuple[str, str, str], dict] = defaultdict(
        lambda: {"total_requests": 0, "input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}
    )
    for r in rows:
        day = r["created_at"][:10]
        key = (day, r["model"], r["provider"])
        b = buckets[key]
        b["total_requests"] += 1
        b["input_tokens"] += r["input_tokens"]
        b["output_tokens"] += r["output_tokens"]
        b["total_cost"] += float(r["vuzo_cost"])

    daily = []
    for (day, mdl, prov), agg in sorted(buckets.items(), key=lambda x: x[0][0], reverse=True):
        daily.append({
            "date": day,
            "model": mdl,
            "provider": prov,
            **agg,
        })
    return daily
