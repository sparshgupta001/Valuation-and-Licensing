"""Document-type dispatcher for PDF, DOCX, and text/JSON uploads."""

from pathlib import PurePath

from app.ingestion.pdf_parser import extract_pdf_text


def extract_document_text(filename: str, content_type: str, content: bytes) -> str:
    """Extract text from common patent document types using lazy optional imports."""

    suffix = PurePath(filename).suffix.lower()
    if suffix == ".pdf" or content_type == "application/pdf":
        text = extract_pdf_text(content)
        return text
    if suffix == ".docx" or "wordprocessingml" in content_type:
        try:
            from docx import Document as DocxDocument
        except ImportError as exc:
            raise RuntimeError("Install python-docx to parse DOCX files.") from exc
        import io

        return "\n".join(paragraph.text for paragraph in DocxDocument(io.BytesIO(content)).paragraphs)
    if suffix in {".txt", ".json", ".xml", ".html"} or content_type.startswith("text/"):
        return content.decode("utf-8", errors="replace")
    raise ValueError(f"Unsupported document type for '{filename}'.")
