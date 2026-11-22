"""Assessment lifecycle, upload, status, result, and review routes."""

from pathlib import PurePath

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.database.models import Assessment, Document, DocumentRole
from app.database.repositories import list_step_runs
from app.schemas.assessment import AssessmentCreate, CommercialInfo, ReviewCorrection
from app.schemas.common import AssessmentStatus, StepStatus
from app.schemas.report import AssessmentResults
from app.services.assessment_service import (
    AssessmentNotFoundError,
    apply_review_correction,
    create_assessment,
    require_assessment,
    results_from_assessment,
    save_commercial_info,
    start_assessment,
)

router = APIRouter(prefix="/assessments", tags=["assessments"])


def _not_found(exc: AssessmentNotFoundError) -> HTTPException:
    """Map a missing assessment to an HTTP 404 response."""

    return HTTPException(status_code=404, detail=f"Assessment '{exc.args[0]}' not found.")


@router.post("", status_code=status.HTTP_201_CREATED)
def post_assessment(payload: AssessmentCreate, session: Session = Depends(get_session)) -> dict[str, object]:
    """Create an assessment from screen 1."""

    assessment = create_assessment(session, payload)
    return {"assessment_id": assessment.id, "state": assessment.state}


@router.put("/{assessment_id}/commercial-info")
def put_commercial_info(
    assessment_id: str,
    payload: CommercialInfo,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Save optional screen 2 fields and their source tags."""

    try:
        assessment = save_commercial_info(session, assessment_id, payload)
    except AssessmentNotFoundError as exc:
        raise _not_found(exc) from exc
    return {"assessment_id": assessment.id, "saved_fields": sorted(assessment.commercial_info)}


@router.post("/{assessment_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    assessment_id: str,
    request: Request,
    filename: str = Query(min_length=1),
    role: DocumentRole = Query(default=DocumentRole.TARGET_PATENT),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Store raw patent document bytes; filename is stripped to its final path part."""

    try:
        assessment = require_assessment(session, assessment_id)
    except AssessmentNotFoundError as exc:
        raise _not_found(exc) from exc
    content = await request.body()
    max_bytes = request.app.state.settings.max_upload_bytes
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded document is empty.")
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Document exceeds the {max_bytes} byte limit.")
    safe_name = PurePath(filename.replace("\\", "/")).name
    document = Document(
        assessment_id=assessment.id,
        filename=safe_name,
        content_type=request.headers.get("content-type", "application/octet-stream"),
        role=role.value,
        size_bytes=len(content),
        content=content,
    )
    session.add(document)
    session.commit()
    return {
        "document_id": document.id,
        "filename": document.filename,
        "size_bytes": document.size_bytes,
        "role": document.role,
    }


@router.post("/{assessment_id}/start")
async def start(assessment_id: str, session: Session = Depends(get_session)) -> AssessmentStatus:
    """Run the assessment graph and return its per-step state."""

    try:
        assessment = await start_assessment(session, assessment_id)
    except AssessmentNotFoundError as exc:
        raise _not_found(exc) from exc
    steps = [
        StepStatus(
            name=step.name,
            state=step.state,
            started_at=step.started_at,
            completed_at=step.completed_at,
            error=step.error,
        )
        for step in list_step_runs(session, assessment_id)
    ]
    return AssessmentStatus(
        assessment_id=assessment.id,
        state=assessment.state,
        steps=steps,
        human_review_pending=assessment.human_review_pending,
        updated_at=assessment.updated_at,
    )


@router.get("/{assessment_id}/status")
def get_status(assessment_id: str, session: Session = Depends(get_session)) -> AssessmentStatus:
    """Return overall state and each recorded workflow step."""

    try:
        assessment = require_assessment(session, assessment_id)
    except AssessmentNotFoundError as exc:
        raise _not_found(exc) from exc
    steps = [
        StepStatus(name=step.name, state=step.state, started_at=step.started_at, completed_at=step.completed_at, error=step.error)
        for step in list_step_runs(session, assessment_id)
    ]
    return AssessmentStatus(
        assessment_id=assessment.id,
        state=assessment.state,
        steps=steps,
        human_review_pending=assessment.human_review_pending,
        updated_at=assessment.updated_at,
    )


@router.get("/{assessment_id}/results", response_model=AssessmentResults)
def get_results(assessment_id: str, session: Session = Depends(get_session)) -> AssessmentResults:
    """Return module results and the assembled report."""

    try:
        assessment = require_assessment(session, assessment_id)
    except AssessmentNotFoundError as exc:
        raise _not_found(exc) from exc
    if not assessment.results:
        raise HTTPException(status_code=409, detail="Assessment has not been started.")
    return results_from_assessment(assessment)


@router.post("/{assessment_id}/review")
def review(
    assessment_id: str,
    payload: ReviewCorrection,
    session: Session = Depends(get_session),
) -> AssessmentStatus:
    """Persist a human correction/acknowledgement and close the review checkpoint."""

    try:
        assessment = apply_review_correction(
            session,
            assessment_id,
            step=payload.step,
            correction=payload.correction,
            reviewer_note=payload.reviewer_note,
        )
    except AssessmentNotFoundError as exc:
        raise _not_found(exc) from exc
    return AssessmentStatus(
        assessment_id=assessment.id,
        state=assessment.state,
        human_review_pending=assessment.human_review_pending,
        updated_at=assessment.updated_at,
    )
