"""Assessment-scoped, in-memory semantic retrieval over evidence passages."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from typing import Iterable, Protocol

from app.ai.embeddings import EMBEDDING_DIMENSION, EmbeddingProvider
from app.ingestion.chunking import DocumentChunk, chunk_document_segments
from app.ingestion.document_loader import extract_document_segments

_EVIDENCE_ROLES = frozenset({"product_documentation", "reference_prior_art"})
_VALID_ROLES = _EVIDENCE_ROLES | {"target_patent"}


class AssessmentDocument(Protocol):
    """Minimum document fields needed to create an evidence index."""

    assessment_id: str
    id: str
    filename: str
    content_type: str
    role: str
    content: bytes


@dataclass(frozen=True)
class RetrievedEvidence:
    """Exact source passage and provenance, ranked by similarity only."""

    assessment_id: str
    document_id: str
    document_name: str
    document_role: str
    page_number: int | None
    source_locator: str
    start_offset: int
    end_offset: int
    passage: str
    similarity_score: float


@dataclass(frozen=True)
class _IndexedPassage:
    chunk: DocumentChunk
    unit_embedding: tuple[float, ...]


class EvidenceRetriever:
    """Reusable in-memory evidence index bound to exactly one assessment.

    Documents are filtered by assessment ID before their role, filename, or
    content is accessed. Only product documentation and prior-art documents
    become evidence passages; target patents are never embedded here.
    """

    def __init__(
        self,
        assessment_id: str,
        documents: Iterable[AssessmentDocument],
        embedding_provider: EmbeddingProvider,
        *,
        batch_size: int = 64,
        chunk_size: int = 1200,
        overlap: int = 200,
    ) -> None:
        if not isinstance(assessment_id, str):
            raise TypeError("assessment_id must be a non-empty string")
        if not assessment_id.strip() or assessment_id != assessment_id.strip():
            raise ValueError("assessment_id must be a non-empty, trimmed string")
        if not callable(getattr(embedding_provider, "embed", None)):
            raise TypeError("embedding_provider must implement embed(texts)")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")

        self.assessment_id = assessment_id
        self.embedding_provider = embedding_provider
        self.batch_size = batch_size
        self._chunks = self._collect_chunks(
            documents,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        self._index: tuple[_IndexedPassage, ...] | None = None
        self._index_lock = Lock()

    def _collect_chunks(
        self,
        documents: Iterable[AssessmentDocument],
        *,
        chunk_size: int,
        overlap: int,
    ) -> tuple[DocumentChunk, ...]:
        eligible: list[AssessmentDocument] = []
        for document in documents:
            document_assessment_id = getattr(document, "assessment_id", None)
            if document_assessment_id != self.assessment_id:
                continue
            role = _role_value(getattr(document, "role", None))
            if role in _EVIDENCE_ROLES:
                eligible.append(document)

        chunks: list[DocumentChunk] = []
        for document in sorted(eligible, key=lambda item: str(item.id)):
            segments = extract_document_segments(
                document.filename,
                document.content_type,
                document.content,
            )
            chunks.extend(chunk_document_segments(
                segments,
                document_id=document.id,
                document_name=document.filename,
                document_role=_role_value(document.role),
                chunk_size=chunk_size,
                overlap=overlap,
            ))
        return tuple(sorted(
            chunks,
            key=lambda chunk: (
                chunk.document_id,
                chunk.source_locator,
                chunk.start_offset,
            ),
        ))

    def _build_index(self) -> tuple[_IndexedPassage, ...]:
        if not self._chunks:
            return ()

        indexed: list[_IndexedPassage] = []
        passages = [chunk.passage for chunk in self._chunks]
        for start in range(0, len(passages), self.batch_size):
            batch_chunks = self._chunks[start : start + self.batch_size]
            batch_texts = passages[start : start + self.batch_size]
            embeddings = self.embedding_provider.embed(batch_texts)
            if not isinstance(embeddings, (list, tuple)) or len(embeddings) != len(batch_chunks):
                raise ValueError("embedding provider returned an unexpected corpus batch length")
            for chunk, embedding in zip(batch_chunks, embeddings, strict=True):
                unit = _unit_vector(embedding)
                if unit is not None:
                    indexed.append(_IndexedPassage(chunk=chunk, unit_embedding=unit))
        return tuple(indexed)

    def _ensure_index(self) -> tuple[_IndexedPassage, ...]:
        if self._index is None:
            with self._index_lock:
                if self._index is None:
                    self._index = self._build_index()
        return self._index

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        roles: Iterable[str | StrEnum] | str | StrEnum | None = None,
    ) -> list[RetrievedEvidence]:
        """Return exact passages ranked by cosine similarity to ``query``.

        Similarity is a discovery signal only; it does not indicate that a
        patent limitation is satisfied or establish claim coverage.
        """

        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if not query.strip() or limit <= 0:
            return []

        allowed_roles = _requested_roles(roles)
        index = self._ensure_index()
        if not index:
            return []

        query_embeddings = self.embedding_provider.embed([query])
        if query_embeddings is None or (
            isinstance(query_embeddings, (list, tuple)) and not query_embeddings
        ):
            return []
        if not isinstance(query_embeddings, (list, tuple)) or len(query_embeddings) != 1:
            raise ValueError("embedding provider returned an unexpected query batch length")
        query_vector = _unit_vector(query_embeddings[0])
        if query_vector is None:
            return []

        ranked: list[RetrievedEvidence] = []
        for item in index:
            chunk = item.chunk
            if chunk.document_role not in allowed_roles:
                continue
            similarity = math.fsum(
                query_value * passage_value
                for query_value, passage_value in zip(query_vector, item.unit_embedding, strict=True)
            )
            # Unit-vector rounding can produce a tiny excursion outside cosine's range.
            similarity = max(-1.0, min(1.0, similarity))
            ranked.append(RetrievedEvidence(
                assessment_id=self.assessment_id,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                document_role=chunk.document_role,
                page_number=chunk.page_number,
                source_locator=chunk.source_locator,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                passage=chunk.passage,
                similarity_score=similarity,
            ))

        ranked.sort(key=lambda result: (
            -result.similarity_score,
            result.document_id,
            result.source_locator,
            result.start_offset,
        ))
        return ranked[:limit]


def _role_value(role: object) -> str | None:
    """Normalize a role enum or string without accepting unknown roles."""

    value = getattr(role, "value", role)
    return value if isinstance(value, str) and value in _VALID_ROLES else None


def _requested_roles(
    roles: Iterable[str | StrEnum] | str | StrEnum | None,
) -> frozenset[str]:
    """Validate role filters while making target patents unselectable."""

    if roles is None:
        return _EVIDENCE_ROLES
    if isinstance(roles, str):
        role_values = [roles]
    else:
        try:
            role_values = list(roles)
        except TypeError as exc:
            raise TypeError("roles must be an iterable of document roles") from exc

    normalized: set[str] = set()
    for role in role_values:
        value = _role_value(role)
        if value is None:
            raise ValueError(f"unsupported document role: {role!r}")
        if value in _EVIDENCE_ROLES:
            normalized.add(value)
    return frozenset(normalized)


def _unit_vector(embedding: object) -> tuple[float, ...] | None:
    """Validate and normalize a vector; return None for missing/unusable ones."""

    if embedding is None:
        return None
    if hasattr(embedding, "tolist"):
        embedding = embedding.tolist()
    if not isinstance(embedding, (list, tuple)):
        raise ValueError("embedding provider returned a non-vector value")
    if not embedding:
        return None
    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"embedding provider must return {EMBEDDING_DIMENSION}-dimensional vectors"
        )
    try:
        values = [float(value) for value in embedding]
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError("embedding provider returned non-numeric values") from exc
    if not all(math.isfinite(value) for value in values):
        return None

    scale = max(abs(value) for value in values)
    if scale == 0.0:
        return None
    scaled_values = [value / scale for value in values]
    norm = math.sqrt(math.fsum(value * value for value in scaled_values))
    return tuple(value / norm for value in scaled_values)
