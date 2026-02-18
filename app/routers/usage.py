from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.models.schemas import UsageLogItem, UsageSummary, DailyUsageItem
from app.dependencies import get_current_user_id
from app.services.usage_service import get_usage_logs, get_usage_summary, get_daily_usage

router = APIRouter()


@router.get("", response_model=list[UsageLogItem])
async def list_usage(
    model: Optional[str] = Query(None, description="Filter by model name"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    start_date: Optional[str] = Query(None, description="ISO date start (e.g. 2026-02-11T00:00:00Z)"),
    end_date: Optional[str] = Query(None, description="ISO date end (e.g. 2026-02-18T23:59:59Z)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
):
    """Get paginated usage logs with optional filters."""
    return get_usage_logs(
        user_id=user_id,
        model=model,
        provider=provider,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=UsageSummary)
async def usage_summary(
    start_date: Optional[str] = Query(None, description="ISO date start"),
    end_date: Optional[str] = Query(None, description="ISO date end"),
    user_id: str = Depends(get_current_user_id),
):
    """Get aggregated usage summary, optionally scoped to a date range."""
    return get_usage_summary(user_id, start_date=start_date, end_date=end_date)


@router.get("/daily", response_model=list[DailyUsageItem])
async def daily_usage(
    model: Optional[str] = Query(None, description="Filter by model name"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    start_date: Optional[str] = Query(None, description="ISO date start"),
    end_date: Optional[str] = Query(None, description="ISO date end"),
    user_id: str = Depends(get_current_user_id),
):
    """Get usage aggregated by day and model."""
    return get_daily_usage(
        user_id=user_id,
        model=model,
        provider=provider,
        start_date=start_date,
        end_date=end_date,
    )
