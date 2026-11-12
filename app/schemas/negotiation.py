"""Negotiation scenario output schemas."""

from pydantic import BaseModel, Field

from app.schemas.common import AIOutputMetadata


class NegotiationBrief(AIOutputMetadata):
    """Deterministic royalty corridor with a reviewable narrative brief."""

    assessment_id: str
    royalty_base: str | None = None
    opening_offer_rate: float | None = None
    target_low_rate: float | None = None
    target_high_rate: float | None = None
    scenario_analysis: list[str] = Field(default_factory=list)
    negotiation_points: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = []
