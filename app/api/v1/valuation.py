"""Valuation result route."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.database.repositories import get_assessment
from app.schemas.valuation import ValuationResult

router = APIRouter(prefix="/assessments", tags=["valuation"])


@router.get("/{assessment_id}/valuation", response_model=ValuationResult)
def get_valuation(assessment_id: str, session: Session = Depends(get_session)) -> ValuationResult:
    """Return deterministic method results and assumptions."""

    assessment = get_assessment(session, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    valuation = (assessment.results or {}).get("valuation")
    if valuation is None:
        raise HTTPException(status_code=409, detail="Valuation is not available yet.")
    return ValuationResult.model_validate(valuation)
