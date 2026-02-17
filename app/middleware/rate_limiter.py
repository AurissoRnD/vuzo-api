import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory sliding-window rate limiter keyed by API key prefix.
    Checks the X-Vuzo-RPM header (set by the proxy router after auth)
    to enforce per-key rate limits.
    """

    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer vz-"):
            return await call_next(request)

        key_prefix = auth_header[7:15]  # "Bearer " is 7 chars, prefix is 8 chars
        now = time.time()
        window = 60.0

        timestamps = self._requests[key_prefix]
        self._requests[key_prefix] = [t for t in timestamps if now - t < window]

        rpm_limit = 60
        if len(self._requests[key_prefix]) >= rpm_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "message": f"Rate limit exceeded. Max {rpm_limit} requests per minute.",
                        "type": "rate_limit_error",
                    }
                },
            )

        self._requests[key_prefix].append(now)
        return await call_next(request)
