"""Claim chart result route."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.database.repositories import get_assessment
from app.schemas.intelligence import ClaimChart

router = APIRouter(prefix="/assessments", tags=["claim charts"])


@router.get("/{assessment_id}/claim-charts", response_model=list[ClaimChart])
def get_claim_charts(assessment_id: str, session: Session = Depends(get_session)) -> list[ClaimChart]:
    """Return reviewable claim chart rows."""

    assessment = get_assessment(session, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    stored = assessment.results
    if stored is None:
        raise HTTPException(status_code=409, detail="Assessment has not been started.")
    return [ClaimChart.model_validate(chart) for chart in stored.get("claim_charts", [])]
