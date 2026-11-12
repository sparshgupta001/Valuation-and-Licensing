"""Patent intelligence result route."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.database.repositories import get_assessment
from app.schemas.patent import PatentProfile

router = APIRouter(prefix="/assessments", tags=["patents"])


@router.get("/{assessment_id}/patent", response_model=PatentProfile)
def get_patent_profile(assessment_id: str, session: Session = Depends(get_session)) -> PatentProfile:
    """Return the extracted patent profile for an assessment."""

    assessment = get_assessment(session, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    profile = (assessment.results or {}).get("patent_profile")
    if profile is None:
        raise HTTPException(status_code=409, detail="Patent profile is not available yet.")
    return PatentProfile.model_validate(profile)
