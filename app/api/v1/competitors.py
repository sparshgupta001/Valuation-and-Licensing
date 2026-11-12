"""Competitor intelligence result route."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.database.repositories import get_assessment
from app.schemas.intelligence import CompetitorTarget

router = APIRouter(prefix="/assessments", tags=["competitors"])


@router.get("/{assessment_id}/competitors", response_model=list[CompetitorTarget])
def get_competitors(assessment_id: str, session: Session = Depends(get_session)) -> list[CompetitorTarget]:
    """Return evidence-qualified licensing candidates, if any."""

    assessment = get_assessment(session, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    stored = assessment.results
    if stored is None:
        raise HTTPException(status_code=409, detail="Assessment has not been started.")
    return [CompetitorTarget.model_validate(target) for target in stored.get("competitors", [])]
