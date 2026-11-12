"""Patent profile and claim schemas."""

from pydantic import BaseModel, Field

from app.schemas.common import AIOutputMetadata


class Claim(BaseModel):
    """A patent claim with extracted limitations and review metadata."""

    claim_number: str
    text: str
    independent: bool
    depends_on: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    needs_human_review: bool = True


class PatentProfile(AIOutputMetadata):
    """Structured patent profile produced by Patent Intelligence."""

    title: str
    application_number: str
    abstract: str | None = None
    owner_name: str | None = None
    inventors: list[str] = Field(default_factory=list)
    filing_date: str | None = None
    jurisdiction: str | None = None
    current_status: str | None = None
    technology_domain: str | None = None
    claims: list[Claim] = Field(default_factory=list)
    technical_features: list[str] = Field(default_factory=list)
