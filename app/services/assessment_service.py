"""Assessment lifecycle use case and workflow persistence."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.models import Assessment, DocumentRole, StepRun
from app.database.repositories import get_assessment, list_documents
from app.ingestion.document_loader import extract_document_text
from app.schemas.assessment import AssessmentCreate, CommercialInfo
from app.schemas.common import AssessmentState, StepState
from app.schemas.report import AssessmentResults
from app.workflows.assessment_graph import run_assessment_workflow


class AssessmentNotFoundError(LookupError):
    """Raised when an assessment identifier is not persisted."""


def create_assessment(session: Session, payload: AssessmentCreate) -> Assessment:
    """Persist the screen 1 assessment fields and return the new entity."""

    assessment = Assessment(
        title=payload.title,
        application_number=payload.application_number,
        input_data=payload.model_dump(mode="json"),
        commercial_info={},
        state=AssessmentState.CREATED.value,
    )
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


def require_assessment(session: Session, assessment_id: str) -> Assessment:
    """Fetch an assessment or raise a service-level not-found error."""

    assessment = get_assessment(session, assessment_id)
    if assessment is None:
        raise AssessmentNotFoundError(assessment_id)
    return assessment


def save_commercial_info(session: Session, assessment_id: str, payload: CommercialInfo) -> Assessment:
    """Save optional screen 2 information and preserve source tags."""

    assessment = require_assessment(session, assessment_id)
    assessment.commercial_info = payload.model_dump(mode="json", exclude_none=True)
    assessment.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(assessment)
    return assessment


async def start_assessment(session: Session, assessment_id: str) -> Assessment:
    """Extract uploaded document text, run the graph, and persist partial results."""

    assessment = require_assessment(session, assessment_id)
    assessment.state = AssessmentState.RUNNING.value
    assessment.human_review_pending = True
    session.commit()

    screen_one = AssessmentCreate.model_validate(assessment.input_data)
    commercial = CommercialInfo.model_validate(assessment.commercial_info or {})
    documents = list_documents(session, assessment_id)
    document_text: list[str] = []
    input_errors: list[str] = []
    for document in documents:
        if document.role != DocumentRole.TARGET_PATENT.value:
            continue
        try:
            document_text.append(extract_document_text(document.filename, document.content_type, document.content))
        except Exception as exc:
            input_errors.append(f"document {document.filename}: {type(exc).__name__}: {exc}")

    outcome = await run_assessment_workflow(
        assessment_id,
        screen_one,
        commercial,
        patent_text="\n\n".join(document_text),
        evidence_documents=[
            document
            for document in documents
            if document.role in {
                DocumentRole.PRODUCT_DOCUMENTATION.value,
                DocumentRole.REFERENCE_PRIOR_ART.value,
            }
        ],
    )
    result = outcome["results"]
    result.errors.extend(input_errors)
    assessment.results = result.model_dump(mode="json")
    assessment.state = (
        AssessmentState.PARTIAL.value if result.errors else AssessmentState.REVIEW_REQUIRED.value
    )
    assessment.human_review_pending = outcome["human_review_pending"]
    assessment.updated_at = datetime.now(timezone.utc)

    assessment.step_runs.clear()
    session.flush()
    for step in outcome["steps"]:
        session.add(StepRun(
            assessment_id=assessment_id,
            name=step.name,
            state=step.state.value,
            started_at=step.started_at,
            completed_at=step.completed_at,
            error=step.error,
        ))
    session.commit()
    session.refresh(assessment)
    return assessment


def apply_review_correction(
    session: Session,
    assessment_id: str,
    *,
    step: str,
    correction: dict[str, object],
    reviewer_note: str | None,
) -> Assessment:
    """Append a human correction and close the pending review checkpoint."""

    assessment = require_assessment(session, assessment_id)
    results = dict(assessment.results or {})
    corrections = list(results.get("human_review_corrections", []))
    corrections.append({
        "step": step,
        "correction": correction,
        "reviewer_note": reviewer_note,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    })
    results["human_review_corrections"] = corrections
    assessment.results = results
    assessment.human_review_pending = False
    assessment.state = AssessmentState.COMPLETED.value
    assessment.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(assessment)
    return assessment


def results_from_assessment(assessment: Assessment) -> AssessmentResults:
    """Validate persisted module outputs into the public result schema."""

    return AssessmentResults.model_validate(assessment.results or {})
