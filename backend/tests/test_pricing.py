"""Tests for cost calculation logic (app/utils/pricing.py)."""
import pytest
from app.utils.pricing import calculate_cost


def test_zero_tokens_returns_zero():
    provider_cost, vuzo_cost = calculate_cost(0, 0, 1.0, 2.0, 20.0)
    assert provider_cost == 0.0
    assert vuzo_cost == 0.0


def test_provider_cost_formula():
    # 1M input tokens @ $1.00/M + 1M output tokens @ $2.00/M = $3.00 provider
    provider_cost, _ = calculate_cost(1_000_000, 1_000_000, 1.0, 2.0, 0.0)
    assert provider_cost == pytest.approx(3.0, abs=1e-6)


def test_markup_applied_to_provider_cost():
    # $1.00 provider cost with 20% markup → $1.20 vuzo cost
    provider_cost, vuzo_cost = calculate_cost(1_000_000, 0, 1.0, 0.0, 20.0)
    assert provider_cost == pytest.approx(1.0, abs=1e-6)
    assert vuzo_cost == pytest.approx(1.2, abs=1e-6)


def test_zero_markup():
    provider_cost, vuzo_cost = calculate_cost(500_000, 500_000, 2.0, 4.0, 0.0)
    assert provider_cost == pytest.approx(vuzo_cost, abs=1e-6)


def test_small_token_count_precision():
    # Small request: 100 input + 50 output @ $0.15/$0.60 per million (gpt-4o-mini)
    provider_cost, vuzo_cost = calculate_cost(100, 50, 0.15, 0.60, 20.0)
    expected_provider = (100 * 0.15 + 50 * 0.60) / 1_000_000
    assert provider_cost == pytest.approx(expected_provider, abs=1e-9)
    assert vuzo_cost == pytest.approx(expected_provider * 1.2, abs=1e-9)


def test_returns_floats():
    p, v = calculate_cost(1000, 1000, 1.0, 1.0, 10.0)
    assert isinstance(p, float)
    assert isinstance(v, float)


def test_vuzo_cost_always_gte_provider_cost():
    for markup in [0, 5, 20, 100]:
        p, v = calculate_cost(10_000, 10_000, 1.0, 2.0, markup)
        assert v >= p
