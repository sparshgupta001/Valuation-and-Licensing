"""Deterministic DCF, relief-from-royalty, cost, and Monte Carlo calculations."""

from collections.abc import Sequence

import numpy as np


def dcf_value(
    cash_flows: Sequence[float], discount_rate: float, terminal_growth_rate: float | None = None
) -> float:
    """Calculate present value of annual cash flows with an optional terminal value."""

    if discount_rate <= -1.0:
        raise ValueError("discount_rate must be greater than -1")
    if terminal_growth_rate is not None and terminal_growth_rate >= discount_rate:
        raise ValueError("terminal_growth_rate must be lower than discount_rate")
    periods = np.arange(1, len(cash_flows) + 1, dtype=float)
    values = np.asarray(cash_flows, dtype=float)
    present_value = float(np.sum(values / np.power(1.0 + discount_rate, periods)))
    if terminal_growth_rate is not None and len(values):
        terminal_value = values[-1] * (1.0 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
        present_value += float(terminal_value / (1.0 + discount_rate) ** len(values))
    return present_value


def relief_from_royalty_value(
    revenues: Sequence[float], royalty_rate: float, discount_rate: float, tax_rate: float = 0.0
) -> float:
    """Calculate after-tax royalty savings discounted over the revenue forecast."""

    if not 0.0 <= royalty_rate <= 1.0 or not 0.0 <= tax_rate <= 1.0:
        raise ValueError("royalty_rate and tax_rate must be between 0 and 1")
    if discount_rate <= -1.0:
        raise ValueError("discount_rate must be greater than -1")
    periods = np.arange(1, len(revenues) + 1, dtype=float)
    savings = np.asarray(revenues, dtype=float) * royalty_rate * (1.0 - tax_rate)
    return float(np.sum(savings / np.power(1.0 + discount_rate, periods)))


def cost_approach_value(reproduction_cost: float, obsolescence_rate: float = 0.0) -> float:
    """Estimate value as reproduction cost less the specified obsolescence rate."""

    if reproduction_cost < 0.0 or not 0.0 <= obsolescence_rate <= 1.0:
        raise ValueError("cost must be nonnegative and obsolescence_rate must be between 0 and 1")
    return reproduction_cost * (1.0 - obsolescence_rate)


def monte_carlo_percentiles(
    base_value: float,
    *,
    simulations: int = 10_000,
    volatility: float = 0.25,
    seed: int = 17,
) -> tuple[float, float, float]:
    """Sample a lognormal value range and return P10, P50, and P90."""

    if base_value < 0.0 or simulations < 1 or volatility < 0.0:
        raise ValueError("base_value, simulations, and volatility must be nonnegative/positive")
    if base_value == 0.0:
        return 0.0, 0.0, 0.0
    generator = np.random.default_rng(seed)
    samples = generator.lognormal(mean=np.log(base_value), sigma=volatility, size=simulations)
    p10, p50, p90 = np.percentile(samples, [10, 50, 90])
    return float(p10), float(p50), float(p90)


STRENGTH_WEIGHTS: dict[str, float] = {
    "novelty": 0.25,
    "claim_breadth": 0.25,
    "legal_status": 0.20,
    "evidence_quality": 0.15,
    "commercial_relevance": 0.15,
}


def patent_strength_score(scores: dict[str, float | None]) -> float | None:
    """Return the weighted mean of available 0–100 rubric dimensions."""

    observed = [(STRENGTH_WEIGHTS[name], score) for name, score in scores.items() if name in STRENGTH_WEIGHTS and score is not None]
    if not observed:
        return None
    if any(not 0.0 <= score <= 100.0 for _, score in observed):
        raise ValueError("strength scores must be between 0 and 100")
    total_weight = sum(weight for weight, _ in observed)
    return float(sum(weight * score for weight, score in observed) / total_weight)
