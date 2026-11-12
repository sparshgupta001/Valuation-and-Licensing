"""Negotiation brief result route."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.database.repositories import get_assessment
from app.schemas.negotiation import NegotiationBrief

router = APIRouter(prefix="/assessments", tags=["negotiation"])


@router.get("/{assessment_id}/negotiation", response_model=NegotiationBrief)
def get_negotiation(assessment_id: str, session: Session = Depends(get_session)) -> NegotiationBrief:
    """Return royalty corridor and negotiation summary."""

    assessment = get_assessment(session, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    negotiation = (assessment.results or {}).get("negotiation")
    if negotiation is None:
        raise HTTPException(status_code=409, detail="Negotiation result is not available yet.")
    return NegotiationBrief.model_validate(negotiation)
