"""Map optional commercial form values to the deterministic valuation engine."""

from typing import Any

from app.modules.valuation.engine import calculate_valuation
from app.schemas.assessment import CommercialInfo
from app.schemas.valuation import FinancialInputs, ValuationResult


def _value(commercial: CommercialInfo, field_name: str) -> Any:
    """Read a non-missing optional screen 2 input value."""

    wrapper = getattr(commercial, field_name)
    if wrapper is None or wrapper.source.value == "missing":
        return None
    return wrapper.value


def financial_inputs_from_commercial(commercial: CommercialInfo) -> FinancialInputs:
    """Extract only user/extractor-supplied financial inputs; infer no hidden values."""

    def number(name: str) -> float | None:
        value = _value(commercial, name)
        return float(value) if value is not None else None

    def vector(name: str) -> list[float]:
        value = _value(commercial, name)
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"{name} must be a list of numbers")
        return [float(item) for item in value]

    return FinancialInputs(
        forecast_cash_flows=vector("forecast_cash_flows"),
        forecast_revenue=vector("forecast_revenue"),
        discount_rate=number("discount_rate"),
        royalty_rate=number("royalty_rate"),
        tax_rate=number("tax_rate"),
        reproduction_cost=number("reproduction_cost"),
    )


def value_assessment(assessment_id: str, commercial: CommercialInfo) -> ValuationResult:
    """Run the deterministic valuation engine using supplied commercial inputs."""

    return calculate_valuation(assessment_id, financial_inputs_from_commercial(commercial))
