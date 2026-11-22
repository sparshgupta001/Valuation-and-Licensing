"""Tests for deterministic overlapping chunks and provenance retention."""

import pytest

from app.ingestion.chunking import chunk_document_segments
from app.ingestion.extracted_document import ExtractedTextSegment


def test_chunks_are_exact_overlapping_slices_with_document_metadata() -> None:
    text = "0123456789ABCDEFGHIJ"
    segment = ExtractedTextSegment(text=text, source_locator="page:4", page_number=4)

    chunks = chunk_document_segments(
        [segment],
        document_id="doc-7",
        document_name="reference.pdf",
        document_role="reference_prior_art",
        chunk_size=10,
        overlap=3,
    )

    assert [(chunk.start_offset, chunk.end_offset, chunk.passage) for chunk in chunks] == [
        (0, 10, text[0:10]),
        (7, 17, text[7:17]),
        (14, 20, text[14:20]),
    ]
    assert all(chunk.document_id == "doc-7" for chunk in chunks)
    assert all(chunk.document_name == "reference.pdf" for chunk in chunks)
    assert all(chunk.document_role == "reference_prior_art" for chunk in chunks)
    assert all(chunk.page_number == 4 for chunk in chunks)
    assert [chunk.source_locator for chunk in chunks] == [
        "page:4:chars:0-10",
        "page:4:chars:7-17",
        "page:4:chars:14-20",
    ]
    assert chunks[0].passage[-3:] == chunks[1].passage[:3]
    assert chunks[1].passage[-3:] == chunks[2].passage[:3]


def test_paragraph_and_text_locators_and_roles_are_preserved() -> None:
    segments = [
        ExtractedTextSegment("Paragraph text", "paragraph:2"),
        ExtractedTextSegment("Text file body", "text", page_number=None),
    ]
    chunks = chunk_document_segments(
        segments,
        document_id="doc-8",
        document_name="product.docx",
        document_role="product_documentation",
        chunk_size=100,
        overlap=10,
    )

    assert [chunk.passage for chunk in chunks] == ["Paragraph text", "Text file body"]
    assert [chunk.source_locator for chunk in chunks] == [
        "paragraph:2:chars:0-14",
        "text:chars:0-14",
    ]
    assert all(chunk.page_number is None for chunk in chunks)
    assert all(chunk.document_role == "product_documentation" for chunk in chunks)


def test_empty_and_blank_segments_produce_no_chunks() -> None:
    segments = [
        ExtractedTextSegment("", "page:1", page_number=1),
        ExtractedTextSegment(" \n\t", "paragraph:0"),
    ]
    assert chunk_document_segments(
        segments,
        document_id="doc-9",
        document_name="blank.pdf",
        document_role="reference_prior_art",
    ) == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (10, -1), (10, 10)],
)
def test_invalid_chunk_parameters_are_rejected(chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_document_segments(
            [ExtractedTextSegment("text", "text")],
            document_id="doc-10",
            document_name="file.txt",
            document_role="reference_prior_art",
            chunk_size=chunk_size,
            overlap=overlap,
        )
