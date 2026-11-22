"""SQLAlchemy entities for assessments, documents, workflow steps, and vectors."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class DocumentRole(StrEnum):
    """Classification used to keep patent and evidence documents separate."""

    TARGET_PATENT = "target_patent"
    PRODUCT_DOCUMENTATION = "product_documentation"
    REFERENCE_PRIOR_ART = "reference_prior_art"

try:
    from pgvector.sqlalchemy import Vector

    _embedding_type = Vector(384).with_variant(JSON, "sqlite")
except ImportError:
    _embedding_type = JSON


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


class Assessment(Base):
    """Persisted screen 1 inputs, screen 2 inputs, state, and workflow results."""

    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(500))
    application_number: Mapped[str] = mapped_column(String(120), index=True)
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    commercial_info: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(40), default="created")
    human_review_pending: Mapped[bool] = mapped_column(default=False)
    results: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)
    documents: Mapped[list["Document"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")
    step_runs: Mapped[list["StepRun"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")


class Document(Base):
    """Uploaded source document metadata and bytes (placeholder storage backend)."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(
        String(40),
        default=DocumentRole.TARGET_PATENT.value,
        server_default=DocumentRole.TARGET_PATENT.value,
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(Integer)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    assessment: Mapped[Assessment] = relationship(back_populates="documents")


class StepRun(Base):
    """Latest workflow execution record for an assessment step."""

    __tablename__ = "step_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[Assessment] = relationship(back_populates="step_runs")


class EmbeddingRecord(Base):
    """Vector and source text row; PostgreSQL uses pgvector when installed."""

    __tablename__ = "embedding_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    assessment_id: Mapped[str | None] = mapped_column(ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True, index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Any] = mapped_column(_embedding_type)
    model_name: Mapped[str] = mapped_column(String(200), default="stub")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
