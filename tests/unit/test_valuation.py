"""Tests for deterministic valuation calculations."""

import pytest

from app.modules.valuation.calculations import (
    cost_approach_value,
    dcf_value,
    monte_carlo_percentiles,
    patent_strength_score,
    relief_from_royalty_value,
)
from app.modules.valuation.engine import calculate_valuation
from app.schemas.valuation import FinancialInputs


def test_calculation_methods_return_expected_values() -> None:
    """Verify transparent DCF, RFR, cost, and Monte Carlo math."""

    assert dcf_value([100.0, 100.0], 0.1) == pytest.approx(173.553719)
    assert relief_from_royalty_value([100.0], 0.05, 0.1, 0.2) == pytest.approx(3.636364)
    assert cost_approach_value(100.0, 0.25) == pytest.approx(75.0)
    p10, p50, p90 = monte_carlo_percentiles(100.0, simulations=3_000, seed=3)
    assert p10 < p50 < p90


def test_terminal_growth_must_be_below_discount_rate() -> None:
    """Reject a terminal-growth assumption that makes the DCF undefined."""

    with pytest.raises(ValueError):
        dcf_value([100.0], 0.05, 0.05)


def test_engine_records_missing_methods_and_strength_score() -> None:
    """Return explicit unavailable methods rather than filling assumptions silently."""

    result = calculate_valuation(
        "assessment-1",
        FinancialInputs(reproduction_cost=100.0, strength={"novelty": 80.0, "legal_status": 60.0}),
    )
    assert result.methods[0].available is False
    assert result.methods[2].value == pytest.approx(100.0)
    assert result.patent_strength_score == pytest.approx((0.25 * 80 + 0.20 * 60) / 0.45)
    assert result.percentiles.p10 is not None
