"""Shared pytest fixtures for all test modules."""
import os
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Inject dummy env vars before app import so pydantic-settings doesn't raise
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("PROVIDER_ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleTA=")
os.environ.setdefault("MOONSHOT_API_KEY", "sk-test")

from app.main import app  # noqa: E402
from app.dependencies import get_current_user_id  # noqa: E402
from app.models.schemas import AuthContext  # noqa: E402


MOCK_USER_ID = "user-123"
MOCK_KEY_ID = "key-456"

MOCK_AUTH = AuthContext(
    user_id=MOCK_USER_ID,
    api_key_id=MOCK_KEY_ID,
    rate_limit_rpm=60,
)


def override_auth():
    """Dependency override that bypasses real JWT/API key validation."""
    return MOCK_USER_ID


@pytest.fixture
def client():
    """TestClient with auth dependency overridden."""
    app.dependency_overrides[get_current_user_id] = override_auth
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_supabase():
    """Pre-wired Supabase mock covering the most common chained call patterns."""
    sb = MagicMock()
    # Default: empty result for every table query
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    return sb
