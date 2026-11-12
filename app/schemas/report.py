"""Final report structure and assessment result bundle."""

from pydantic import BaseModel, Field

from app.schemas.intelligence import ClaimChart, CompetitorTarget
from app.schemas.negotiation import NegotiationBrief
from app.schemas.patent import PatentProfile
from app.schemas.valuation import ValuationResult


class ReportSection(BaseModel):
    """Named report section with summary and review metadata."""

    title: str
    summary: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    needs_human_review: bool = True


class AssessmentReport(BaseModel):
    """Complete user-facing report with the requested nine sections."""

    assessment_id: str
    patent_overview: ReportSection
    patent_intelligence: ReportSection
    competitor_landscape: ReportSection
    claim_charts: ReportSection
    ip_valuation: ReportSection
    patent_strength: ReportSection
    licensing_strategy: ReportSection
    negotiation_strategy: ReportSection
    recommendations: ReportSection


class AssessmentResults(BaseModel):
    """Module outputs plus the assembled final report."""

    patent_profile: PatentProfile | None = None
    competitors: list[CompetitorTarget] = Field(default_factory=list)
    claim_charts: list[ClaimChart] = Field(default_factory=list)
    valuation: ValuationResult | None = None
    negotiation: NegotiationBrief | None = None
    report: AssessmentReport | None = None
    errors: list[str] = Field(default_factory=list)
    human_review_corrections: list[dict[str, object]] = Field(default_factory=list)
