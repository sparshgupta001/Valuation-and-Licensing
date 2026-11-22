"""Internal structured text records produced by document extraction."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedTextSegment:
    """A source text segment with a real page number or stable logical locator."""

    text: str
    source_locator: str
    page_number: int | None = None
