from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.models.schemas import UsageLogItem, UsageSummary
from app.dependencies import get_current_user_id
from app.services.usage_service import get_usage_logs, get_usage_summary

router = APIRouter()


@router.get("", response_model=list[UsageLogItem])
async def list_usage(
    model: Optional[str] = Query(None, description="Filter by model name"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
):
    """Get paginated usage logs with optional filters."""
    return get_usage_logs(
        user_id=user_id,
        model=model,
        provider=provider,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=UsageSummary)
async def usage_summary(user_id: str = Depends(get_current_user_id)):
    """Get aggregated usage summary for the authenticated user."""
    return get_usage_summary(user_id)
