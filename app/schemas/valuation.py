"""Valuation method inputs and results."""

from pydantic import BaseModel, Field

from app.schemas.common import AIOutputMetadata


class MethodResult(BaseModel):
    """Single deterministic method output or an explicit missing-input result."""

    method: str
    value: float | None = None
    currency: str = "USD"
    available: bool = False
    notes: list[str] = Field(default_factory=list)


class PercentileRange(BaseModel):
    """Monte Carlo valuation distribution percentiles."""

    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    currency: str = "USD"


class PatentStrengthInputs(BaseModel):
    """Optional 0–100 input scores for the documented strength rubric."""

    novelty: float | None = Field(default=None, ge=0.0, le=100.0)
    claim_breadth: float | None = Field(default=None, ge=0.0, le=100.0)
    legal_status: float | None = Field(default=None, ge=0.0, le=100.0)
    evidence_quality: float | None = Field(default=None, ge=0.0, le=100.0)
    commercial_relevance: float | None = Field(default=None, ge=0.0, le=100.0)


class FinancialInputs(BaseModel):
    """Numeric inputs for deterministic valuation methods."""

    forecast_cash_flows: list[float] = Field(default_factory=list)
    forecast_revenue: list[float] = Field(default_factory=list)
    discount_rate: float | None = Field(default=None, gt=-1.0)
    terminal_growth_rate: float | None = Field(default=None, gt=-1.0)
    royalty_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    tax_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    reproduction_cost: float | None = Field(default=None, ge=0.0)
    obsolescence_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    currency: str = "USD"
    strength: PatentStrengthInputs = Field(default_factory=PatentStrengthInputs)


class ValuationResult(AIOutputMetadata):
    """Combined valuation methods, range, assumptions, and strength score."""

    assessment_id: str
    methods: list[MethodResult] = Field(default_factory=list)
    combined_estimate: float | None = None
    percentiles: PercentileRange = Field(default_factory=PercentileRange)
    assumptions: list[str] = Field(default_factory=list)
    patent_strength_score: float | None = None
    strength_score_rubric: str = "Weighted mean of available inputs: novelty 25%, claim breadth 25%, legal status 20%, evidence quality 15%, commercial relevance 15%; available weights are renormalized."
