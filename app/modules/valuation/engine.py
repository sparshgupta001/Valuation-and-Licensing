"""Valuation orchestration; all numeric calculations are deterministic Python."""

from app.modules.valuation.calculations import (
    cost_approach_value,
    dcf_value,
    monte_carlo_percentiles,
    patent_strength_score,
    relief_from_royalty_value,
)
from app.schemas.valuation import (
    FinancialInputs,
    MethodResult,
    PercentileRange,
    ValuationResult,
)


def calculate_valuation(assessment_id: str, inputs: FinancialInputs) -> ValuationResult:
    """Run each available method and report missing assumptions transparently."""

    methods: list[MethodResult] = []
    assumptions: list[str] = []
    if inputs.forecast_cash_flows and inputs.discount_rate is not None:
        try:
            dcf = dcf_value(inputs.forecast_cash_flows, inputs.discount_rate, inputs.terminal_growth_rate)
            methods.append(MethodResult(
                method="income_dcf", value=dcf, currency=inputs.currency, available=True,
                notes=["Present value of provided cash flows; terminal value is included only when terminal growth is supplied."],
            ))
            assumptions.append(f"DCF discount rate: {inputs.discount_rate:.4f}.")
        except ValueError as exc:
            methods.append(MethodResult(method="income_dcf", notes=[f"Invalid DCF assumptions: {exc}"]))
    else:
        methods.append(MethodResult(method="income_dcf", notes=["Forecast cash flows and discount rate are required."]))
    if inputs.forecast_revenue and inputs.royalty_rate is not None and inputs.discount_rate is not None:
        methods.append(MethodResult(
            method="relief_from_royalty",
            value=relief_from_royalty_value(inputs.forecast_revenue, inputs.royalty_rate, inputs.discount_rate, inputs.tax_rate or 0.0),
            currency=inputs.currency,
            available=True,
            notes=["After-tax royalty savings discounted over the supplied revenue forecast."],
        ))
    else:
        methods.append(MethodResult(method="relief_from_royalty", notes=["Revenue forecast, royalty rate, and discount rate are required."]))
    if inputs.reproduction_cost is not None:
        methods.append(MethodResult(
            method="cost_approach",
            value=cost_approach_value(inputs.reproduction_cost, inputs.obsolescence_rate),
            currency=inputs.currency,
            available=True,
            notes=[f"Reproduction cost reduced by {inputs.obsolescence_rate:.1%} obsolescence."],
        ))
    else:
        methods.append(MethodResult(method="cost_approach", notes=["Reproduction cost is required."]))

    available_values = [method.value for method in methods if method.available and method.value is not None]
    combined = sum(available_values) / len(available_values) if available_values else None
    if combined is not None:
        p10, p50, p90 = monte_carlo_percentiles(combined)
        percentiles = PercentileRange(p10=p10, p50=p50, p90=p90, currency=inputs.currency)
        assumptions.append("Monte Carlo uses a seeded lognormal distribution with 25% volatility and 10,000 draws.")
    else:
        percentiles = PercentileRange(currency=inputs.currency)
    strength = patent_strength_score(inputs.strength.model_dump())
    assumptions.append("Patent strength is a weighted mean of available expert inputs; it is not an automated legal opinion.")
    return ValuationResult(
        assessment_id=assessment_id,
        methods=methods,
        combined_estimate=combined,
        percentiles=percentiles,
        assumptions=assumptions,
        patent_strength_score=strength,
        confidence=0.0,
        evidence=[],
        needs_human_review=True,
    )
