"""Tests for the Supabase-backed rate limiter middleware."""
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.requests import Request

from app.middleware.rate_limiter import RateLimiterMiddleware


def _make_app(rpm_limit: int = 3):
    """Build a minimal Starlette app wrapped with RateLimiterMiddleware."""
    async def homepage(request: Request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(RateLimiterMiddleware)
    return app


def _auth_header(prefix: str = "aabbccdd") -> dict:
    return {"Authorization": f"Bearer vz-{prefix}xyz"}


class TestRateLimiterPassthrough:
    def test_non_vuzo_key_passes_through(self):
        """Requests without a vz- key bypass the rate limiter entirely."""
        with patch("app.middleware.rate_limiter.get_supabase") as mock_sb:
            app = _make_app()
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/", headers={"Authorization": "Bearer sk-openai-key"})
            assert resp.status_code == 200
            mock_sb.assert_not_called()

    def test_no_auth_header_passes_through(self):
        with patch("app.middleware.rate_limiter.get_supabase") as mock_sb:
            app = _make_app()
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/")
            assert resp.status_code == 200
            mock_sb.assert_not_called()


class TestRateLimiterEnforcement:
    def _mock_supabase(self, current_count: int):
        """Return a mock Supabase client that reports `current_count` requests in window."""
        mock_sb = MagicMock()

        count_chain = MagicMock()
        count_chain.execute.return_value = MagicMock(count=current_count)
        mock_sb.table.return_value.select.return_value \
            .eq.return_value.gte.return_value = count_chain

        insert_chain = MagicMock()
        insert_chain.execute.return_value = MagicMock()
        mock_sb.table.return_value.insert.return_value = insert_chain

        delete_chain = MagicMock()
        delete_chain.execute.return_value = MagicMock()
        mock_sb.table.return_value.delete.return_value.lt.return_value = delete_chain

        return mock_sb

    def test_under_limit_allowed(self):
        mock_sb = self._mock_supabase(current_count=30)
        with patch("app.middleware.rate_limiter.get_supabase", return_value=mock_sb):
            app = _make_app()
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/", headers=_auth_header())
            assert resp.status_code == 200

    def test_at_limit_blocked(self):
        mock_sb = self._mock_supabase(current_count=60)
        with patch("app.middleware.rate_limiter.get_supabase", return_value=mock_sb):
            app = _make_app()
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/", headers=_auth_header())
            assert resp.status_code == 429

    def test_429_response_body(self):
        mock_sb = self._mock_supabase(current_count=60)
        with patch("app.middleware.rate_limiter.get_supabase", return_value=mock_sb):
            app = _make_app()
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/", headers=_auth_header())
            body = resp.json()
            assert "error" in body
            assert body["error"]["type"] == "rate_limit_error"

    def test_supabase_failure_allows_request(self):
        """If Supabase is unreachable the request must still succeed (fail open)."""
        mock_sb = MagicMock()
        mock_sb.table.side_effect = Exception("Connection refused")
        with patch("app.middleware.rate_limiter.get_supabase", return_value=mock_sb):
            app = _make_app()
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/", headers=_auth_header())
            assert resp.status_code == 200
