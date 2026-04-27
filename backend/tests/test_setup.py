"""Tests for /v1/setup/installer and /v1/setup/rotate-key (app/routers/setup.py)."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user_id

REGISTER_BODY = {"type": "register", "email": "new@example.com", "password": "Password123!", "key_name": "OpenClaw"}
LOGIN_BODY    = {"type": "login",    "email": "test@example.com", "password": "Password123!", "key_name": "OpenClaw"}


def _make_session():
    mock_user = MagicMock()
    mock_user.id = "supabase-uid-abc"
    mock_session = MagicMock()
    mock_session.access_token = "access-token-xyz"
    mock_session.refresh_token = "refresh-token-xyz"
    mock_session.expires_in = 3600
    mock_resp = MagicMock()
    mock_resp.user = mock_user
    mock_resp.session = mock_session
    return mock_resp


def _make_supabase(internal_user_id: str = "user-123"):
    sb = MagicMock()

    users_mock = MagicMock()
    users_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    users_mock.insert.return_value.execute.return_value = MagicMock(data=[{"id": internal_user_id}])

    found_row = MagicMock(data=[{"id": internal_user_id}])
    users_mock.select.return_value.eq.return_value.execute.side_effect = [
        MagicMock(data=[]),   # first call: user doesn't exist yet
        found_row,             # second call: look up internal id
    ]

    credits_mock = MagicMock()
    credits_mock.insert.return_value.execute.return_value = MagicMock(data=[])
    credits_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    tx_mock = MagicMock()
    tx_mock.insert.return_value.execute.return_value = MagicMock(data=[])

    keys_mock = MagicMock()
    keys_mock.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    keys_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    _table_map = {
        "users": users_mock,
        "credits": credits_mock,
        "credit_transactions": tx_mock,
        "api_keys": keys_mock,
    }
    sb.table.side_effect = lambda name: _table_map.get(name, MagicMock())
    return sb


def _make_existing_user_supabase(internal_user_id: str = "user-123"):
    """Supabase mock for an existing user — user row already present."""
    sb = MagicMock()

    found_row = MagicMock(data=[{"id": internal_user_id}])

    users_mock = MagicMock()
    users_mock.select.return_value.eq.return_value.execute.return_value = found_row

    keys_mock = MagicMock()
    keys_mock.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "key-old", "token_limit": 500000}]
    )
    keys_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    _table_map = {
        "users": users_mock,
        "api_keys": keys_mock,
    }
    sb.table.side_effect = lambda name: _table_map.get(name, MagicMock())
    return sb


@pytest.fixture
def authed_client():
    app.dependency_overrides[get_current_user_id] = lambda: "user-123"
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestInstallerRegister:
    def test_register_new_user_gets_api_key(self):
        sb = _make_supabase()
        auth_resp = _make_session()

        with patch("app.routers.setup.get_supabase", return_value=sb), \
             patch("app.routers.setup.create_api_key", return_value={"key": "vz-sk_new"}), \
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.6"}]), \
             patch("app.routers.setup.create_client") as mock_create:

            mock_create.return_value.auth.sign_up.return_value = auth_resp
            resp = TestClient(app).post("/v1/setup/installer", json=REGISTER_BODY)

        assert resp.status_code == 200
        assert resp.json()["api_key"] == "vz-sk_new"

    def test_register_returns_session(self):
        sb = _make_supabase()
        auth_resp = _make_session()

        with patch("app.routers.setup.get_supabase", return_value=sb), \
             patch("app.routers.setup.create_api_key", return_value={"key": "vz-sk_new"}), \
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.6"}]), \
             patch("app.routers.setup.create_client") as mock_create:

            mock_create.return_value.auth.sign_up.return_value = auth_resp
            resp = TestClient(app).post("/v1/setup/installer", json=REGISTER_BODY)

        session = resp.json()["session"]
        assert session["access_token"] == "access-token-xyz"
        assert session["refresh_token"] == "refresh-token-xyz"

    def test_register_existing_email_returns_400(self):
        auth_resp = MagicMock()
        auth_resp.user = MagicMock()
        auth_resp.session = None  # Supabase returns no session for duplicate email

        with patch("app.routers.setup.create_client") as mock_create:
            mock_create.return_value.auth.sign_up.return_value = auth_resp
            resp = TestClient(app).post("/v1/setup/installer", json=REGISTER_BODY)

        assert resp.status_code == 400

    def test_register_openclaw_config_shape(self):
        sb = _make_supabase()
        auth_resp = _make_session()

        with patch("app.routers.setup.get_supabase", return_value=sb), \
             patch("app.routers.setup.create_api_key", return_value={"key": "vz-sk_new"}), \
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.6"}]), \
             patch("app.routers.setup.create_client") as mock_create:

            mock_create.return_value.auth.sign_up.return_value = auth_resp
            resp = TestClient(app).post("/v1/setup/installer", json=REGISTER_BODY)

        cfg = resp.json()["openclaw_config"]
        assert cfg["provider_name"] == "vuzo"
        assert "kimi-k2.6" in cfg["models"]


class TestInstallerLogin:
    def test_login_always_rotates_key(self):
        sb = _make_existing_user_supabase()
        auth_resp = _make_session()

        with patch("app.routers.setup.get_supabase", return_value=sb), \
             patch("app.routers.setup.create_api_key", return_value={"key": "vz-sk_rotated"}), \
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.6"}]), \
             patch("app.routers.setup.create_client") as mock_create:

            mock_create.return_value.auth.sign_in_with_password.return_value = auth_resp
            resp = TestClient(app).post("/v1/setup/installer", json=LOGIN_BODY)

        assert resp.status_code == 200
        assert resp.json()["api_key"] == "vz-sk_rotated"

    def test_login_bad_credentials_returns_401(self):
        from supabase import AuthApiError

        with patch("app.routers.setup.create_client") as mock_create:
            mock_create.return_value.auth.sign_in_with_password.side_effect = AuthApiError("Invalid", 400, {})
            resp = TestClient(app).post("/v1/setup/installer", json=LOGIN_BODY)

        assert resp.status_code == 401

    def test_login_returns_session(self):
        sb = _make_existing_user_supabase()
        auth_resp = _make_session()

        with patch("app.routers.setup.get_supabase", return_value=sb), \
             patch("app.routers.setup.create_api_key", return_value={"key": "vz-sk_rotated"}), \
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.6"}]), \
             patch("app.routers.setup.create_client") as mock_create:

            mock_create.return_value.auth.sign_in_with_password.return_value = auth_resp
            resp = TestClient(app).post("/v1/setup/installer", json=LOGIN_BODY)

        session = resp.json()["session"]
        assert session["access_token"] == "access-token-xyz"


ROTATE_BODY = {"email": "test@example.com", "password": "Password123!", "key_name": "OpenClaw"}


def _make_rotate_supabase(internal_user_id: str = "user-123"):
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": internal_user_id}]
    )
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    return sb


def _make_rotate_auth():
    mock_user = MagicMock()
    mock_user.id = "supabase-uid-abc"
    mock_response = MagicMock()
    mock_response.user = mock_user
    return mock_response


class TestRotateKey:
    def test_rotate_returns_new_key(self):
        sb = _make_rotate_supabase()
        mock_auth_client = MagicMock()
        mock_auth_client.auth.sign_in_with_password.return_value = _make_rotate_auth()

        with patch("app.routers.setup.get_supabase", return_value=sb), \
             patch("app.routers.setup.create_client", return_value=mock_auth_client), \
             patch("app.routers.setup.create_api_key", return_value={"key": "vz-sk_rotated"}), \
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.6"}]):

            resp = TestClient(app).post("/v1/setup/rotate-key", json=ROTATE_BODY)

        assert resp.status_code == 200
        assert resp.json()["api_key"] == "vz-sk_rotated"

    def test_rotate_without_body_returns_422(self):
        resp = TestClient(app).post("/v1/setup/rotate-key")
        assert resp.status_code == 422

    def test_rotate_bad_credentials_returns_401(self):
        from supabase import AuthApiError
        mock_auth_client = MagicMock()
        mock_auth_client.auth.sign_in_with_password.side_effect = AuthApiError("Invalid login", 400, {})

        with patch("app.routers.setup.create_client", return_value=mock_auth_client):
            resp = TestClient(app).post("/v1/setup/rotate-key", json=ROTATE_BODY)

        assert resp.status_code == 401

    def test_rotate_response_includes_openclaw_config(self):
        sb = _make_rotate_supabase()
        mock_auth_client = MagicMock()
        mock_auth_client.auth.sign_in_with_password.return_value = _make_rotate_auth()

        with patch("app.routers.setup.get_supabase", return_value=sb), \
             patch("app.routers.setup.create_client", return_value=mock_auth_client), \
             patch("app.routers.setup.create_api_key", return_value={"key": "vz-sk_rotated"}), \
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.6"}]):

            resp = TestClient(app).post("/v1/setup/rotate-key", json=ROTATE_BODY)

        assert "openclaw_config" in resp.json()
        assert "models" in resp.json()
