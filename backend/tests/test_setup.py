"""Tests for /v1/setup/installer and /v1/setup/rotate-key (app/routers/setup.py)."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user_id

INSTALLER_BODY = {"email": "test@example.com", "password": "Password123!", "key_name": "OpenClaw"}


def _make_supabase(
    user_exists: bool = False,
    starter_granted: bool = False,
    key_exists: bool = False,
    internal_user_id: str = "user-123",
):
    """Build a Supabase mock wired for installer/rotate-key scenarios."""
    sb = MagicMock()

    # Auth: sign_in succeeds
    mock_user = MagicMock()
    mock_user.id = "supabase-uid-abc"
    mock_session = MagicMock()
    mock_session.access_token = "access-token-xyz"
    mock_session.refresh_token = "refresh-token-xyz"
    mock_session.expires_in = 3600
    mock_auth_response = MagicMock()
    mock_auth_response.user = mock_user
    mock_auth_response.session = mock_session

    # users table — look up by supabase_auth_id
    user_row = MagicMock()
    user_row.data = [{"id": internal_user_id}] if user_exists else []
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value = user_row

    # credit_transactions — starter grant check
    grant_row = MagicMock()
    grant_row.data = [{"id": "tx-1"}] if starter_granted else []

    # api_keys — existing key check
    key_row = MagicMock()
    key_row.data = [{"id": "key-old"}] if key_exists else []

    # Pre-create table mocks so the same object is returned on every sb.table(name) call
    found_row = MagicMock(data=[{"id": internal_user_id}])

    users_mock = MagicMock()
    users_mock.select.return_value.eq.return_value.execute.side_effect = [user_row, found_row]
    users_mock.insert.return_value.execute.return_value = MagicMock(data=[{"id": internal_user_id}])

    tx_mock = MagicMock()
    tx_mock.select.return_value.eq.return_value.eq.return_value.ilike.return_value.limit.return_value.execute.return_value = grant_row
    tx_mock.insert.return_value.execute.return_value = MagicMock(data=[])

    credits_mock = MagicMock()
    credits_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"balance": 0.0}])
    credits_mock.insert.return_value.execute.return_value = MagicMock(data=[])
    credits_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    keys_mock = MagicMock()
    keys_mock.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = key_row
    keys_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    _table_map = {
        "users": users_mock,
        "credit_transactions": tx_mock,
        "credits": credits_mock,
        "api_keys": keys_mock,
    }
    sb.table.side_effect = lambda name: _table_map.get(name, MagicMock())
    return sb, mock_auth_response


@pytest.fixture
def authed_client():
    app.dependency_overrides[get_current_user_id] = lambda: "user-123"
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestInstallerNewUser:
    def test_new_user_gets_api_key(self):
        sb, auth_resp = _make_supabase(user_exists=False, starter_granted=False, key_exists=False)
        new_key = "vz-sk_newkey123"

        with patch("app.routers.setup.get_supabase", return_value=sb), \
             patch("app.routers.setup.create_api_key", return_value={"key": new_key}), \
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.5"}]), \
             patch("app.routers.setup.create_client") as mock_create:

            mock_create.return_value.auth.sign_in_with_password.side_effect = Exception("not found")
            mock_create.return_value.auth.sign_up.return_value = auth_resp

            resp = TestClient(app).post("/v1/setup/installer", json=INSTALLER_BODY)

        assert resp.status_code == 200
        assert resp.json()["api_key"] == new_key

    def test_new_user_gets_session_tokens(self):
        sb, auth_resp = _make_supabase(user_exists=False, starter_granted=False, key_exists=False)

        with patch("app.routers.setup.get_supabase", return_value=sb), \
             patch("app.routers.setup.create_api_key", return_value={"key": "vz-sk_x"}), \
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.5"}]), \
             patch("app.routers.setup.create_client") as mock_create:

            mock_create.return_value.auth.sign_in_with_password.side_effect = Exception("not found")
            mock_create.return_value.auth.sign_up.return_value = auth_resp

            resp = TestClient(app).post("/v1/setup/installer", json=INSTALLER_BODY)

        assert resp.status_code == 200
        session = resp.json().get("session")
        assert session is not None
        assert session["access_token"] == "access-token-xyz"
        assert session["refresh_token"] == "refresh-token-xyz"

    def test_openclaw_config_shape(self):
        sb, auth_resp = _make_supabase(user_exists=False, starter_granted=False, key_exists=False)

        with patch("app.routers.setup.get_supabase", return_value=sb), \
             patch("app.routers.setup.create_api_key", return_value={"key": "vz-sk_x"}), \
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.5"}]), \
             patch("app.routers.setup.create_client") as mock_create:

            mock_create.return_value.auth.sign_in_with_password.side_effect = Exception("not found")
            mock_create.return_value.auth.sign_up.return_value = auth_resp

            resp = TestClient(app).post("/v1/setup/installer", json=INSTALLER_BODY)

        cfg = resp.json()["openclaw_config"]
        assert cfg["provider_name"] == "vuzo"
        assert "kimi-k2.5" in cfg["models"]
        assert cfg["base_url"].startswith("https://")


class TestInstallerExistingUser:
    def test_existing_key_returns_null_api_key(self):
        """Re-login with existing active key → api_key: null, config unchanged."""
        sb, auth_resp = _make_supabase(user_exists=True, starter_granted=True, key_exists=True)

        with patch("app.routers.setup.get_supabase", return_value=sb), \
             patch("app.routers.setup.create_api_key") as mock_create_key, \
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.5"}]), \
             patch("app.routers.setup.create_client") as mock_create:

            mock_create.return_value.auth.sign_in_with_password.return_value = auth_resp

            resp = TestClient(app).post("/v1/setup/installer", json=INSTALLER_BODY)

        assert resp.status_code == 200
        assert resp.json()["api_key"] is None
        mock_create_key.assert_not_called()


class TestInstallerStarterGrantExploit:
    def test_starter_grant_not_given_twice(self):
        """User who already received the grant and drained to $0 should not get $1 again."""
        sb, auth_resp = _make_supabase(user_exists=True, starter_granted=True, key_exists=False)

        credits_inserted = []

        original_table = sb.table.side_effect

        def track_credits(table_name):
            mock = original_table(table_name)
            if table_name == "credit_transactions":
                original_insert = mock.insert

                def recording_insert(data):
                    credits_inserted.append(data)
                    return original_insert(data)

                mock.insert = recording_insert
            return mock

        sb.table.side_effect = track_credits

        with patch("app.routers.setup.get_supabase", return_value=sb), \
             patch("app.routers.setup.create_api_key", return_value={"key": "vz-sk_new"}), \
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.5"}]), \
             patch("app.routers.setup.create_client") as mock_create:

            mock_create.return_value.auth.sign_in_with_password.return_value = auth_resp

            resp = TestClient(app).post("/v1/setup/installer", json=INSTALLER_BODY)

        assert resp.status_code == 200
        # No starter allowance transaction should have been inserted
        starter_txs = [d for d in credits_inserted if isinstance(d, dict) and "starter allowance" in d.get("description", "")]
        assert len(starter_txs) == 0


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
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.5"}]):

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
             patch("app.routers.setup.get_all_models", return_value=[{"model_name": "kimi-k2.5"}]):

            resp = TestClient(app).post("/v1/setup/rotate-key", json=ROTATE_BODY)

        assert "openclaw_config" in resp.json()
        assert "models" in resp.json()
