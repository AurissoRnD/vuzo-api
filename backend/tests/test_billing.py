"""Tests for billing service and GET /v1/billing/* routes (app/services/billing_service.py)."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user_id
from app.services.billing_service import check_sufficient_balance, deduct_credits, add_credits


def _sb_with_balance(balance: float) -> MagicMock:
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"balance": balance}]
    )
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "tx-1"}])
    return sb


class TestCheckSufficientBalance:
    def test_sufficient_balance_returns_balance(self):
        sb = _sb_with_balance(5.0)
        with patch("app.services.billing_service.get_supabase", return_value=sb):
            balance = check_sufficient_balance("user-1")
        assert balance == 5.0

    def test_zero_balance_raises_402(self):
        sb = _sb_with_balance(0.0)
        with patch("app.services.billing_service.get_supabase", return_value=sb):
            with pytest.raises(HTTPException) as exc_info:
                check_sufficient_balance("user-1")
        assert exc_info.value.status_code == 402

    def test_below_min_raises_402(self):
        sb = _sb_with_balance(0.0005)
        with patch("app.services.billing_service.get_supabase", return_value=sb):
            with pytest.raises(HTTPException) as exc_info:
                check_sufficient_balance("user-1", min_amount=0.001)
        assert exc_info.value.status_code == 402

    def test_no_credits_row_raises_402(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
        with patch("app.services.billing_service.get_supabase", return_value=sb):
            with pytest.raises(HTTPException) as exc_info:
                check_sufficient_balance("user-new")
        assert exc_info.value.status_code == 402


class TestDeductCredits:
    def test_deducts_amount_correctly(self):
        sb = _sb_with_balance(1.0)
        updated_balance = None

        def capture_update(data):
            nonlocal updated_balance
            updated_balance = data.get("balance")
            mock = MagicMock()
            mock.eq.return_value.execute.return_value = MagicMock(data=[])
            return mock

        sb.table.return_value.update.side_effect = capture_update

        with patch("app.services.billing_service.get_supabase", return_value=sb):
            new_balance = deduct_credits("user-1", 0.25, "test usage")

        assert new_balance == pytest.approx(0.75, abs=1e-6)

    def test_returns_new_balance(self):
        sb = _sb_with_balance(2.0)
        with patch("app.services.billing_service.get_supabase", return_value=sb):
            result = deduct_credits("user-1", 0.5, "usage")
        assert result == pytest.approx(1.5, abs=1e-6)


class TestAddCredits:
    def test_adds_amount_and_returns_new_balance(self):
        sb = _sb_with_balance(1.0)
        with patch("app.services.billing_service.get_supabase", return_value=sb):
            new_balance, tx_id = add_credits("user-1", 5.0)
        assert new_balance == pytest.approx(6.0, abs=1e-6)

    def test_returns_transaction_id(self):
        sb = _sb_with_balance(0.0)
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "tx-abc"}])
        with patch("app.services.billing_service.get_supabase", return_value=sb):
            _, tx_id = add_credits("user-1", 10.0)
        assert tx_id == "tx-abc"


class TestBillingRoutes:
    @pytest.fixture
    def client(self):
        app.dependency_overrides[get_current_user_id] = lambda: "user-123"
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_get_balance_returns_200(self, client):
        sb = _sb_with_balance(3.50)
        with patch("app.services.billing_service.get_supabase", return_value=sb):
            resp = client.get("/v1/billing/balance")
        assert resp.status_code == 200
        assert resp.json()["balance"] == pytest.approx(3.50, abs=1e-4)

    def test_get_balance_unauthenticated_returns_401(self):
        resp = TestClient(app).get("/v1/billing/balance")
        assert resp.status_code in (401, 403)
