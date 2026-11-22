"""Focused tests for conservative patent claim extraction."""

import asyncio
import json

from app.modules.patent_intelligence.claim_parser import extract_claims
from app.modules.patent_intelligence.service import build_patent_profile
from app.schemas.assessment import AssessmentCreate


def test_extracts_independent_and_dependent_claims_with_exact_text() -> None:
    source = """Description\n1. This numbered paragraph is not a claim.\n\nWhat is claimed is:\n1. A device comprising a sensor; and\n   a controller coupled to the sensor.\n2) The device of claim 1, wherein the controller stores data.\n"""
    claims, ambiguous = extract_claims(source)

    assert not ambiguous
    assert len(claims) == 2
    assert claims[0].claim_number == "1"
    assert claims[0].independent is True
    assert claims[0].depends_on == []
    assert claims[0].text == "A device comprising a sensor; and\n   a controller coupled to the sensor."
    assert claims[1].claim_number == "2"
    assert claims[1].independent is False
    assert claims[1].depends_on == ["1"]
    assert claims[1].text == "The device of claim 1, wherein the controller stores data."
    assert claims[0].limitations == ["A device comprising a sensor;", "and\n   a controller coupled to the sensor."]
    assert "".join(claims[0].limitations) != claims[0].text
    assert claims[0].text == "A device comprising a sensor; and\n   a controller coupled to the sensor."


def test_claim_heading_can_share_line_with_first_numbered_claim() -> None:
    claims, ambiguous = extract_claims("What is claimed is: 1. A valve comprising a housing.")
    assert not ambiguous
    assert len(claims) == 1
    assert claims[0].text == "A valve comprising a housing."


def test_extracts_claims_from_existing_structured_json_uploads() -> None:
    source = json.dumps({"claims": [
        {"claim_number": "1", "text": "A valve comprising a housing."},
        {"claim_number": "2", "text": "The valve of claim 1, wherein the housing is metal."},
    ]})
    claims, ambiguous = extract_claims(source)
    assert not ambiguous
    assert [claim.text for claim in claims] == [
        "A valve comprising a housing.",
        "The valve of claim 1, wherein the housing is metal.",
    ]
    assert claims[1].depends_on == ["1"]


def test_semicolons_split_but_commas_are_preserved() -> None:
    source = "Claims\n1. A sensor having a first, second, and third element; and a controller configured to process signals."
    claims, ambiguous = extract_claims(source)
    assert not ambiguous
    assert claims[0].limitations == [
        "A sensor having a first, second, and third element;",
        "and a controller configured to process signals.",
    ]
    assert "".join(claims[0].limitations) != claims[0].text
    assert claims[0].text == source.split("1. ", 1)[1]


def test_trims_limitation_whitespace_without_splitting_commas_or_removing_words() -> None:
    source = "Claims\n1. A unit;  \n and a valve, seal, and port.  "
    claims, ambiguous = extract_claims(source)
    assert not ambiguous
    assert claims[0].text == "A unit;  \n and a valve, seal, and port."
    assert claims[0].limitations == ["A unit;", "and a valve, seal, and port."]
    assert all(part == part.strip() for part in claims[0].limitations)
    assert "and" in claims[0].limitations[1]


def test_missing_or_malformed_claim_sections_do_not_fabricate_claims() -> None:
    claims, ambiguous = extract_claims("1. This is a numbered description paragraph, not under a claims heading.")
    assert claims == []
    assert ambiguous

    claims, ambiguous = extract_claims("Claims\nThis section contains no recognizable numbered claim.")
    assert claims == []
    assert ambiguous


def test_numbering_gaps_flag_ambiguous_extraction() -> None:
    claims, ambiguous = extract_claims("Claims\n1. A first device.\n3. The device of claim 1.")
    assert len(claims) == 2
    assert ambiguous
    assert all(claim.needs_human_review for claim in claims)


def test_profile_returns_no_fabricated_claim_when_extraction_fails() -> None:
    profile = asyncio.run(build_patent_profile(
        AssessmentCreate(title="Patent", application_number="US-1"),
        "No claims section here.",
    ))
    assert profile.claims == []
    assert profile.needs_human_review
