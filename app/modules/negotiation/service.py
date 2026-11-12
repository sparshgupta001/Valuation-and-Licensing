"""Deterministic royalty corridor calculation and narrative brief stub."""

from app.schemas.assessment import CommercialInfo
from app.schemas.negotiation import NegotiationBrief
from app.schemas.valuation import ValuationResult


def _number(commercial: CommercialInfo, name: str) -> float | None:
    """Read an explicitly supplied numeric commercial input."""

    wrapped = getattr(commercial, name)
    if wrapped is None or wrapped.source.value == "missing" or wrapped.value is None:
        return None
    return float(wrapped.value)


def royalty_corridor(
    valuation: float | None,
    annual_royalty_base: float | None,
    incremental_margin: float | None,
    design_around_cost: float | None,
    comparable_rate: float | None,
) -> tuple[float, float, float] | None:
    """Calculate opening, low, and high rates using an explicit five-year corridor rule."""

    required = (valuation, annual_royalty_base, incremental_margin, design_around_cost)
    if any(value is None for value in required):
        return None
    assert valuation is not None and annual_royalty_base is not None
    assert incremental_margin is not None and design_around_cost is not None
    if annual_royalty_base <= 0.0 or min(valuation, design_around_cost) < 0.0:
        raise ValueError("valuation and design-around cost must be nonnegative and base must be positive")
    # Target is a five-year equivalent share of the royalty base. The floor
    # reflects avoided design-around cost and the cap limits incremental margin.
    value_rate = valuation / (annual_royalty_base * 5.0)
    floor_rate = design_around_cost / (annual_royalty_base * 5.0)
    cap_rate = incremental_margin * 0.25
    if comparable_rate is not None:
        value_rate = (value_rate + comparable_rate) / 2.0
        floor_rate = max(floor_rate, comparable_rate * 0.8)
        cap_rate = min(cap_rate, comparable_rate * 1.2)
    low = min(floor_rate, cap_rate)
    high = max(low, min(cap_rate, max(value_rate, low)))
    opening = high * 1.1
    return opening, low, high


async def build_negotiation_brief(
    assessment_id: str,
    valuation: ValuationResult,
    commercial: CommercialInfo,
) -> NegotiationBrief:
    """Build a reviewable negotiation brief with deterministic rates and stub narrative."""

    base_value = _number(commercial, "annual_revenue")
    margin = _number(commercial, "incremental_margin")
    design_cost = _number(commercial, "design_around_cost")
    comparable = _number(commercial, "royalty_rate")
    corridor = royalty_corridor(valuation.combined_estimate, base_value, margin, design_cost, comparable)
    missing = [
        name for name, value in (
            ("combined valuation", valuation.combined_estimate),
            ("annual revenue / royalty base", base_value),
            ("incremental margin", margin),
            ("design-around cost", design_cost),
        ) if value is None
    ]
    return NegotiationBrief(
        assessment_id=assessment_id,
        royalty_base="annual revenue" if base_value is not None else None,
        opening_offer_rate=corridor[0] if corridor else None,
        target_low_rate=corridor[1] if corridor else None,
        target_high_rate=corridor[2] if corridor else None,
        scenario_analysis=["TODO: add sensitivity cases for base, low, and high commercial assumptions."],
        negotiation_points=["TODO: generate evidence-backed narrative after comparable agreements are configured."],
        missing_inputs=missing,
        confidence=0.0,
        evidence=[],
        needs_human_review=True,
    )
