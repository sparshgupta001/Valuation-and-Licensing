"""Small explicit repository functions; callers own the transaction/session."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Assessment, Document, StepRun


def get_assessment(session: Session, assessment_id: str) -> Assessment | None:
    """Return one assessment by identifier."""

    return session.get(Assessment, assessment_id)


def list_documents(session: Session, assessment_id: str) -> list[Document]:
    """Return documents uploaded for an assessment."""

    return list(session.scalars(select(Document).where(Document.assessment_id == assessment_id)))


def list_step_runs(session: Session, assessment_id: str) -> list[StepRun]:
    """Return workflow steps in creation order."""

    return list(session.scalars(select(StepRun).where(StepRun.assessment_id == assessment_id).order_by(StepRun.id)))
