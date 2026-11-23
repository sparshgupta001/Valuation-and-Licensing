"""Tests for structured document extraction and legacy text compatibility."""

from io import BytesIO

import fitz
from docx import Document as DocxDocument

from app.ingestion.document_loader import extract_document_segments, extract_document_text
from app.ingestion.pdf_parser import extract_pdf_pages


def make_pdf(*page_texts: str) -> bytes:
    pdf = fitz.open()
    for page_text in page_texts:
        page = pdf.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)
    content = pdf.tobytes()
    pdf.close()
    return content


def test_pdf_pages_keep_real_one_based_page_numbers_and_legacy_join(monkeypatch) -> None:
    content = make_pdf("First page", "", "Third page")
    monkeypatch.setattr("app.ingestion.ocr.extract_image_text", lambda _image: "OCR page two")

    pages = extract_pdf_pages(content)

    assert [page.page_number for page in pages] == [1, 2, 3]
    assert [page.source_locator for page in pages] == ["page:1", "page:2", "page:3"]
    assert [page.text.strip() for page in pages] == ["First page", "OCR page two", "Third page"]
    assert extract_document_text("patent.pdf", "application/pdf", content) == "\n".join(
        page.text for page in pages
    )


def test_empty_pdf_and_blank_pdf_page_are_safe(monkeypatch) -> None:
    assert extract_pdf_pages(b"") == []
    assert extract_document_text("empty.pdf", "application/pdf", b"") == ""

    content = make_pdf("")
    monkeypatch.setattr("app.ingestion.ocr.extract_image_text", lambda _image: "")
    pages = extract_pdf_pages(content)
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].text == ""


def test_txt_segments_keep_exact_text_and_no_fake_page_number() -> None:
    content = "First line\r\nSecond line — exact.".encode("utf-8")
    segments = extract_document_segments("guide.txt", "text/plain", content)

    assert len(segments) == 1
    assert segments[0].text == content.decode("utf-8")
    assert segments[0].source_locator == "text"
    assert segments[0].page_number is None
    assert extract_document_text("guide.txt", "text/plain", content) == segments[0].text


def test_docx_segments_keep_paragraph_locators_and_no_fake_pages() -> None:
    doc = DocxDocument()
    doc.add_paragraph("First paragraph")
    doc.add_paragraph("Second paragraph")
    buffer = BytesIO()
    doc.save(buffer)

    segments = extract_document_segments("guide.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", buffer.getvalue())

    assert [segment.text for segment in segments] == ["First paragraph", "Second paragraph"]
    assert [segment.source_locator for segment in segments] == ["paragraph:0", "paragraph:1"]
    assert all(segment.page_number is None for segment in segments)
    assert extract_document_text(
        "guide.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        buffer.getvalue(),
    ) == "First paragraph\nSecond paragraph"


def test_empty_text_and_docx_return_no_segments() -> None:
    assert extract_document_segments("empty.txt", "text/plain", b"") == []

    doc = DocxDocument()
    buffer = BytesIO()
    doc.save(buffer)
    assert extract_document_segments("empty.docx", "application/docx", buffer.getvalue()) == []
