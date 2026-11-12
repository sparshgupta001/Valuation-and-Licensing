"""Patent profile interface and placeholder implementation."""

from app.schemas.assessment import AssessmentCreate
from app.schemas.common import EvidenceItem
from app.schemas.patent import Claim, PatentProfile


async def build_patent_profile(assessment: AssessmentCreate, document_text: str = "") -> PatentProfile:
    """Build a reviewable profile; replace the stub with evidence-grounded extraction."""

    extracted = bool(document_text.strip())
    evidence = [EvidenceItem(document_name="uploaded source", passage="TODO: attach page-level extracted evidence.")] if extracted else []
    claim = Claim(
        claim_number="1",
        text="TODO: extract independent claim text from the patent document.",
        independent=True,
        limitations=[],
        confidence=0.0,
        evidence=[],
        needs_human_review=True,
    )
    return PatentProfile(
        title=assessment.title,
        application_number=assessment.application_number,
        owner_name=assessment.owner_name,
        filing_date=assessment.filing_date.isoformat() if assessment.filing_date else None,
        jurisdiction=assessment.jurisdiction,
        current_status=assessment.current_status,
        technology_domain=assessment.technology_domain,
        claims=[claim],
        technical_features=[],
        confidence=0.0,
        evidence=evidence,
        needs_human_review=True,
    )
