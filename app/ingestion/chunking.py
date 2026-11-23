"""Deterministic, provenance-preserving text chunking for extracted documents."""

from dataclasses import dataclass

from app.ingestion.extracted_document import ExtractedTextSegment


@dataclass(frozen=True)
class DocumentChunk:
    """An exact source substring plus the metadata needed to cite its origin."""

    document_id: str
    document_name: str
    document_role: str
    source_locator: str
    page_number: int | None
    start_offset: int
    end_offset: int
    passage: str


def chunk_document_segments(
    segments: list[ExtractedTextSegment],
    *,
    document_id: str,
    document_name: str,
    document_role: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[DocumentChunk]:
    """Split segments into exact character slices with deterministic overlap.

    Offsets are relative to each source segment. Each chunk keeps that segment's
    page or logical locator, so overlapping passages remain traceable.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    chunks: list[DocumentChunk] = []
    step = chunk_size - overlap
    for segment in segments:
        text = segment.text
        if not text.strip():
            continue
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            passage = text[start:end]
            if passage.strip():
                locator = f"{segment.source_locator}:chars:{start}-{end}"
                chunks.append(DocumentChunk(
                    document_id=document_id,
                    document_name=document_name,
                    document_role=document_role,
                    source_locator=locator,
                    page_number=segment.page_number,
                    start_offset=start,
                    end_offset=end,
                    passage=passage,
                ))
            if end == len(text):
                break
            start += step
    return chunks
