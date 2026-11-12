"""PDF text extraction with a lazy PyMuPDF import."""


def extract_pdf_text(content: bytes) -> str:
    """Extract PDF text, invoking the optional OCR adapter for scanned pages."""

    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Install PyMuPDF to parse PDF files.") from exc
    with fitz.open(stream=content, filetype="pdf") as document:
        page_text: list[str] = []
        for page in document:
            text = page.get_text("text")
            if not text.strip():
                from app.ingestion.ocr import extract_image_text

                text = extract_image_text(page.get_pixmap().tobytes("png"))
            page_text.append(text)
        return "\n".join(page_text)
