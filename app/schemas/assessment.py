"""Assessment creation and optional commercial input schemas."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import InputValue


class AssessmentCreate(BaseModel):
    """Screen 1: core patent and licensing objective information."""

    title: str = Field(min_length=1, max_length=500)
    application_number: str = Field(min_length=1, max_length=120)
    technology_domain: str | None = None
    owner_name: str | None = None
    filing_date: date | None = None
    jurisdiction: str | None = None
    current_status: str | None = None
    licensing_objective: str | None = None


class CommercialInfo(BaseModel):
    """Screen 2: all fields are optional and include input provenance."""

    product_description: InputValue | None = None
    target_markets: InputValue | None = None
    market_size: InputValue | None = None
    annual_revenue: InputValue | None = None
    forecast_revenue: InputValue | None = None
    forecast_cash_flows: InputValue | None = None
    gross_margin: InputValue | None = None
    royalty_rate: InputValue | None = None
    discount_rate: InputValue | None = None
    tax_rate: InputValue | None = None
    development_cost: InputValue | None = None
    reproduction_cost: InputValue | None = None
    commercialization_cost: InputValue | None = None
    comparable_agreements: InputValue | None = None
    known_competitors: InputValue | None = None
    design_around_cost: InputValue | None = None
    incremental_margin: InputValue | None = None
    additional_context: InputValue | None = None

    model_config = ConfigDict(extra="forbid")


class ReviewCorrection(BaseModel):
    """Human correction or review acknowledgement for one result area."""

    step: str = Field(min_length=1)
    correction: dict[str, object] = Field(default_factory=dict)
    reviewer_note: str | None = None
