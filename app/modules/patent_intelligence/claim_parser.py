"""Conservative, rule-based extraction and decomposition of numbered claims."""

import json
import re

from app.schemas.patent import Claim

_CLAIMS_HEADING = re.compile(
    r"(?im)^\s*(?:what\s+is\s+claimed\s+is|claims(?:\s*\(\s*\d+\s*\))?)\s*:?\s*(.*)$"
)
_CLAIM_START = re.compile(r"(?m)^\s*(\d{1,3})\s*[.)]\s+")
_DEPENDENCY = re.compile(
    r"\bclaims?\s+(?:numbers?\s+)?(\d+(?:\s*(?:-|to|,|and|or)\s*\d+)*)\b",
    re.IGNORECASE,
)
_NON_CLAIM_HEADING = re.compile(
    r"(?im)^\s*(?:abstract|background|summary|brief\s+description|detailed\s+description|description|drawings|field\s+of\s+the\s+invention)\s*:?\s*$"
)


def _find_claim_section(source: str) -> tuple[str, bool]:
    """Return text after a recognized claims heading and heading ambiguity."""

    match = _CLAIMS_HEADING.search(source)
    if match is None:
        return "", bool(source.strip())

    # Inline claim text after the heading is valid (e.g. "What is claimed is: 1.").
    section_start = match.start(1)
    heading_remainder = match.group(1)
    if re.match(r"\s*\d{1,3}\s*[.)]\s+", heading_remainder):
        section = "\n" + heading_remainder + source[match.end():]
    else:
        section = source[section_start:]
    boundary = _NON_CLAIM_HEADING.search(section)
    if boundary:
        section = section[:boundary.start()]
    return section, False


def _dependency_numbers(claim_text: str) -> list[str]:
    """Extract explicit claim references without inferring unstated dependencies."""

    dependencies: list[str] = []
    for match in _DEPENDENCY.finditer(claim_text):
        reference_text = match.group(1)
        range_matches = list(re.finditer(r"(\d+)\s*(?:-|to)\s*(\d+)", reference_text))
        range_spans: set[tuple[int, int]] = set()
        for range_match in range_matches:
            first, last = map(int, range_match.groups())
            if last >= first and last - first <= 100:
                dependencies.extend(str(number) for number in range(first, last + 1))
                range_spans.add(range_match.span())
        remainder = list(reference_text)
        for start, end in range_spans:
            remainder[start:end] = " " * (end - start)
        dependencies.extend(re.findall(r"\d+", "".join(remainder)))
    # Preserve source order while removing repeated references.
    return list(dict.fromkeys(dependencies))


def _split_limitations(claim_text: str) -> list[str]:
    """Split after semicolons and trim segment edges without dropping punctuation or words."""

    parts = re.split(r"(?<=;)", claim_text)
    limitations = [part.strip() for part in parts if part.strip()]
    if not limitations:
        return [claim_text]
    return limitations


def extract_claims(source: str) -> tuple[list[Claim], bool]:
    """Extract numbered claims from an explicitly headed claims section.

    The Boolean result indicates that extraction could not be considered fully
    reliable (for example, a missing heading, no numbered claims, or numbering
    gaps). Parsed claim wording is otherwise kept intact apart from outer space.
    """

    structured_claims, structured_ambiguous = _extract_json_claims(source)
    if structured_claims is not None:
        return structured_claims, structured_ambiguous

    section, ambiguous = _find_claim_section(source)
    if not section.strip():
        return [], True

    starts = list(_CLAIM_START.finditer(section))
    if not starts:
        return [], True

    claims: list[Claim] = []
    seen_numbers: set[str] = set()
    previous_number: int | None = None
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(section)
        number = start.group(1)
        text = section[start.end():end].strip()
        if not text:
            ambiguous = True
            continue

        dependencies = _dependency_numbers(text)
        number_value = int(number)
        claim_ambiguous = number in seen_numbers or (
            previous_number is not None and number_value != previous_number + 1
        )
        if dependencies and any(dependency == number for dependency in dependencies):
            claim_ambiguous = True
        claims.append(Claim(
            claim_number=number,
            text=text,
            independent=not dependencies,
            depends_on=dependencies,
            limitations=_split_limitations(text),
            confidence=0.0,
            evidence=[],
            needs_human_review=True,
        ))
        ambiguous = ambiguous or claim_ambiguous
        seen_numbers.add(number)
        previous_number = number_value

    return claims, ambiguous or not claims


def _extract_json_claims(source: str) -> tuple[list[Claim] | None, bool]:
    """Read explicitly structured claim entries from JSON patent uploads."""

    if not source.lstrip().startswith(("{", "[")):
        return None, False
    try:
        payload = json.loads(source)
    except (json.JSONDecodeError, TypeError):
        return None, True
    entries = payload.get("claims") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return None, True

    claims: list[Claim] = []
    ambiguous = not entries
    for entry in entries:
        if not isinstance(entry, dict):
            ambiguous = True
            continue
        number = entry.get("claim_number", entry.get("number"))
        text = entry.get("text")
        if not isinstance(number, (str, int)) or not isinstance(text, str) or not text.strip():
            ambiguous = True
            continue
        number = str(number)
        text = text.strip()
        dependencies = _dependency_numbers(text)
        claims.append(Claim(
            claim_number=number,
            text=text,
            independent=not dependencies,
            depends_on=dependencies,
            limitations=_split_limitations(text),
            confidence=0.0,
            evidence=[],
            needs_human_review=True,
        ))
    numbers = [claim.claim_number for claim in claims]
    try:
        numeric_numbers = [int(number) for number in numbers]
        ambiguous = ambiguous or len(set(numbers)) != len(numbers) or any(
            current != previous + 1 for previous, current in zip(numeric_numbers, numeric_numbers[1:])
        )
    except ValueError:
        ambiguous = True
    return claims, ambiguous or not claims
