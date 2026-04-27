"""Tests for GET /v1/models and GET /v1/models/{model_name} (app/routers/models_list.py)."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app

CLIENT = TestClient(app)

MOCK_MODELS = [
    {
        "provider": "moonshot",
        "model_name": "kimi-k2.6",
        "input_price_per_million": 0.14,
        "output_price_per_million": 0.14,
        "vuzo_markup_percent": 20.0,
        "is_active": True,
    }
]


class TestListModels:
    def test_returns_200(self):
        with patch("app.routers.models_list.get_all_models", return_value=MOCK_MODELS):
            resp = CLIENT.get("/v1/models")
        assert resp.status_code == 200

    def test_returns_list(self):
        with patch("app.routers.models_list.get_all_models", return_value=MOCK_MODELS):
            resp = CLIENT.get("/v1/models")
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 1

    def test_markup_applied_to_prices(self):
        with patch("app.routers.models_list.get_all_models", return_value=MOCK_MODELS):
            resp = CLIENT.get("/v1/models")
        model = resp.json()[0]
        # 0.14 * 1.20 = 0.168
        assert model["vuzo_input_price_per_million"] == pytest.approx(0.168, abs=1e-4)
        assert model["vuzo_output_price_per_million"] == pytest.approx(0.168, abs=1e-4)

    def test_response_shape(self):
        with patch("app.routers.models_list.get_all_models", return_value=MOCK_MODELS):
            resp = CLIENT.get("/v1/models")
        model = resp.json()[0]
        assert "provider" in model
        assert "model_name" in model
        assert "input_price_per_million" in model
        assert "vuzo_markup_percent" in model

    def test_empty_catalog_returns_empty_list(self):
        with patch("app.routers.models_list.get_all_models", return_value=[]):
            resp = CLIENT.get("/v1/models")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetSingleModel:
    def test_known_model_returns_200(self):
        with patch("app.routers.models_list.get_all_models", return_value=MOCK_MODELS):
            resp = CLIENT.get("/v1/models/kimi-k2.6")
        assert resp.status_code == 200
        assert resp.json()["model_name"] == "kimi-k2.6"

    def test_unknown_model_returns_404(self):
        with patch("app.routers.models_list.get_all_models", return_value=MOCK_MODELS):
            resp = CLIENT.get("/v1/models/gpt-99")
        assert resp.status_code == 404

    def test_404_detail_mentions_get_models(self):
        with patch("app.routers.models_list.get_all_models", return_value=MOCK_MODELS):
            resp = CLIENT.get("/v1/models/nonexistent")
        assert "/v1/models" in resp.json()["detail"]
