"""PDF text extraction with a lazy PyMuPDF import."""

from app.ingestion.extracted_document import ExtractedTextSegment


def extract_pdf_pages(content: bytes) -> list[ExtractedTextSegment]:
    """Extract one record per PDF page, keeping OCR text on its original page."""

    if not content:
        return []

    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Install PyMuPDF to parse PDF files.") from exc
    with fitz.open(stream=content, filetype="pdf") as document:
        pages: list[ExtractedTextSegment] = []
        for page_index, page in enumerate(document):
            page_number = page_index + 1
            text = page.get_text("text")
            if not text.strip():
                from app.ingestion.ocr import extract_image_text

                text = extract_image_text(page.get_pixmap().tobytes("png"))
            pages.append(ExtractedTextSegment(
                text=text,
                source_locator=f"page:{page_number}",
                page_number=page_number,
            ))
        return pages


def extract_pdf_text(content: bytes) -> str:
    """Return the legacy joined PDF text, preserving the prior page separator."""

    return "\n".join(page.text for page in extract_pdf_pages(content))
