"""Competitor and claim chart output schemas."""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import AIOutputMetadata, EvidenceItem


class ClaimAssessment(StrEnum):
    """Claim chart label; see README for the required review boundary."""

    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    GAP = "GAP"


class CompetitorTarget(AIOutputMetadata):
    """Potential licensing target with independent commercial evidence."""

    company_name: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    company_activity_evidence: list[EvidenceItem] = Field(default_factory=list)
    commercial_relevance_evidence: list[EvidenceItem] = Field(default_factory=list)
    explanation: str
    eligible_for_outreach: bool = False

    @model_validator(mode="after")
    def require_commercial_evidence(self) -> "CompetitorTarget":
        """Prevent patent similarity alone from establishing an outreach target."""

        if self.eligible_for_outreach and not (
            self.company_activity_evidence and self.commercial_relevance_evidence
        ):
            raise ValueError("outreach eligibility requires company activity and commercial relevance evidence")
        return self


class ClaimChartRow(AIOutputMetadata):
    """Evidence-backed assessment of one claim limitation."""

    claim_number: str
    limitation: str
    assessment: ClaimAssessment
    explanation: str


class ClaimChart(BaseModel):
    """Claim chart for one independent claim."""

    claim_number: str
    rows: list[ClaimChartRow] = Field(default_factory=list)
    needs_human_review: bool = True
