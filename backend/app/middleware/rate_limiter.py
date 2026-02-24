import time
from datetime import datetime, timezone, timedelta

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.models.database import get_supabase

_DEFAULT_RPM = 60


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Supabase-backed sliding-window rate limiter keyed by API key prefix.

    Each request writes a row to the `rate_limit_requests` table.
    The count of rows in the last 60 seconds determines whether a request
    is allowed.  Stale rows (> 2 minutes old) are pruned on every hit to
    keep the table small.

    Required Supabase table (run once):

        CREATE TABLE IF NOT EXISTS rate_limit_requests (
            id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
            key_prefix  TEXT        NOT NULL,
            requested_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_rl_prefix_time
            ON rate_limit_requests (key_prefix, requested_at);

    Fail-open: if Supabase is unreachable the request is allowed through so
    that a transient DB outage does not take down the API.
    """

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer vz-"):
            return await call_next(request)

        key_prefix = auth_header[7:15]  # 8 chars after "Bearer "
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=60)
        cleanup_cutoff = now - timedelta(seconds=120)

        try:
            sb = get_supabase()
            window_start_iso = window_start.isoformat()

            count_result = (
                sb.table("rate_limit_requests")
                .select("id", count="exact")
                .eq("key_prefix", key_prefix)
                .gte("requested_at", window_start_iso)
                .execute()
            )
            current_count = count_result.count or 0

            if current_count >= _DEFAULT_RPM:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "message": f"Rate limit exceeded. Max {_DEFAULT_RPM} requests per minute.",
                            "type": "rate_limit_error",
                        }
                    },
                )

            sb.table("rate_limit_requests").insert({
                "key_prefix": key_prefix,
                "requested_at": now.isoformat(),
            }).execute()

            # Best-effort cleanup — ignore failures
            try:
                sb.table("rate_limit_requests") \
                    .delete() \
                    .lt("requested_at", cleanup_cutoff.isoformat()) \
                    .execute()
            except Exception:
                pass

        except Exception:
            # Fail open: don't block requests if Supabase is unavailable
            pass

        return await call_next(request)
