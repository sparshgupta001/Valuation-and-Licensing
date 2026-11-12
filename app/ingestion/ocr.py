"""OCR fallback adapter with a lazy pytesseract import."""


def extract_image_text(image_bytes: bytes) -> str:
    """Recognize image text when Tesseract and pytesseract are configured."""

    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Install pytesseract and Pillow and configure the Tesseract binary.") from exc
    import io

    return str(pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes))))
