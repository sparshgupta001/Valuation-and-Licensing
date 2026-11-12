"""Schema validation tests for optional inputs and review metadata."""

from app.schemas.assessment import AssessmentCreate, CommercialInfo
from app.schemas.common import InputValue, SourceTag
from app.schemas.intelligence import ClaimAssessment, ClaimChartRow, CompetitorTarget
import pytest


def test_commercial_info_is_optional_and_tracks_provenance() -> None:
    """Screen 2 accepts no answers and preserves source tags when provided."""

    assert CommercialInfo().model_dump(exclude_none=True) == {}
    info = CommercialInfo(annual_revenue=InputValue(value=1_000_000, source=SourceTag.USER))
    assert info.annual_revenue is not None
    assert info.annual_revenue.source is SourceTag.USER


def test_input_source_must_match_value_presence() -> None:
    """Missing fields cannot smuggle a value without an origin."""

    with pytest.raises(ValueError):
        InputValue(value=100, source=SourceTag.MISSING)


def test_assessment_and_claim_chart_schema_validation() -> None:
    """Core fields and claim-chart review requirements validate as typed values."""

    assessment = AssessmentCreate(title="Widget patent", application_number="US-123")
    assert assessment.title == "Widget patent"
    row = ClaimChartRow(
        claim_number="1",
        limitation="a processor",
        assessment=ClaimAssessment.GAP,
        explanation="No evidence supplied.",
    )
    assert row.needs_human_review is True


def test_similarity_alone_cannot_qualify_a_licensing_target() -> None:
    """Outreach eligibility requires commercial evidence, not only similarity."""

    with pytest.raises(ValueError):
        CompetitorTarget(
            company_name="Example Co.",
            similarity_score=0.99,
            explanation="Similarity only.",
            eligible_for_outreach=True,
        )
