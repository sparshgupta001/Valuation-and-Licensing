"""Patent profile generation from assessment details and supplied source text."""

from app.modules.patent_intelligence.claim_parser import extract_claims
from app.schemas.assessment import AssessmentCreate
from app.schemas.patent import PatentProfile


async def build_patent_profile(assessment: AssessmentCreate, document_text: str = "") -> PatentProfile:
    """Build a profile from supplied details and claims actually found in source text."""

    claims, extraction_ambiguous = extract_claims(document_text)
    return PatentProfile(
        title=assessment.title,
        application_number=assessment.application_number,
        owner_name=assessment.owner_name,
        filing_date=assessment.filing_date.isoformat() if assessment.filing_date else None,
        jurisdiction=assessment.jurisdiction,
        current_status=assessment.current_status,
        technology_domain=assessment.technology_domain,
        claims=claims,
        technical_features=[],
        confidence=0.0,
        evidence=[],
        needs_human_review=extraction_ambiguous or any(claim.needs_human_review for claim in claims),
    )
