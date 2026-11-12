"""Shared evidence, provenance, and status schema types."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceTag(StrEnum):
    """Origin marker for values entered on screen 2."""

    USER = "user"
    EXTRACTED = "extracted"
    MISSING = "missing"


class EvidenceItem(BaseModel):
    """A traceable source passage or user-provided evidence reference."""

    document_name: str = ""
    page: int | None = Field(default=None, ge=1)
    passage: str = ""
    source_type: str = "document"
    uri: str | None = None


class AIOutputMetadata(BaseModel):
    """Required quality and review metadata on AI-assisted output models."""

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    needs_human_review: bool = True


class InputValue(BaseModel):
    """Optional screen 2 value and its origin."""

    value: Any | None = None
    source: SourceTag = SourceTag.MISSING
    evidence: list[EvidenceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_provenance(self) -> "InputValue":
        """Keep missing values and provenance tags consistent."""

        if self.source is SourceTag.MISSING and self.value is not None:
            raise ValueError("a value tagged 'missing' must not contain a value")
        if self.source is not SourceTag.MISSING and self.value is None:
            raise ValueError("user or extracted provenance requires a value")
        return self


class StepState(StrEnum):
    """Lifecycle state for one workflow node."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class AssessmentState(StrEnum):
    """Lifecycle state for an assessment request."""

    CREATED = "created"
    RUNNING = "running"
    REVIEW_REQUIRED = "review_required"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class StepStatus(BaseModel):
    """Recorded execution details for a workflow step."""

    name: str
    state: StepState
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class AssessmentStatus(BaseModel):
    """API status response including per-step execution states."""

    assessment_id: str
    state: AssessmentState
    steps: list[StepStatus] = Field(default_factory=list)
    human_review_pending: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
