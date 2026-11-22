"""Claim chart scope and report-summary tests."""

import asyncio

from app.modules.claim_chart.service import build_claim_charts
from app.reports.builder import build_report
from app.schemas.assessment import AssessmentCreate
from app.schemas.patent import Claim, PatentProfile
from app.schemas.report import AssessmentResults


def make_profile(claims: list[Claim]) -> PatentProfile:
    return PatentProfile(
        title="Example patent",
        application_number="US-123",
        claims=claims,
        needs_human_review=True,
    )


def make_claim_results() -> tuple[PatentProfile, list]:
    profile = make_profile([
        Claim(
            claim_number="1",
            text="A device comprising a sensor; and a controller.",
            independent=True,
            limitations=["A device comprising a sensor;", "and a controller."],
        ),
        Claim(
            claim_number="2",
            text="The device of claim 1, wherein the controller stores data.",
            independent=False,
            depends_on=["1"],
            limitations=["The device of claim 1, wherein the controller stores data."],
        ),
    ])
    charts = asyncio.run(build_claim_charts(profile))
    return profile, charts


def test_claim_charts_include_independent_claims_only() -> None:
    profile, charts = make_claim_results()

    assert [claim.claim_number for claim in profile.claims] == ["1", "2"]
    assert [chart.claim_number for chart in charts] == ["1"]
    assert all(row.claim_number == "1" for chart in charts for row in chart.rows)


def test_report_counts_parsed_independent_dependent_and_charted_claims() -> None:
    profile, charts = make_claim_results()
    results = AssessmentResults(patent_profile=profile, claim_charts=charts)
    report = build_report(
        "assessment-1",
        AssessmentCreate(title="Example patent", application_number="US-123"),
        results,
    )

    summary = report.patent_intelligence.summary
    assert "Parsed 2 claim(s)" in summary
    assert "1 independent and 1 dependent" in summary
    assert "1 independent claim(s) charted" in summary
    assert "1 dependent claim(s) were extracted but are not independently charted" in summary
    assert "Evidence retrieval and matching are not configured" in summary
    assert "Evidence retrieval and matching are not configured" in report.claim_charts.summary


def test_report_does_not_suggest_dependent_claims_exist_when_none_were_parsed() -> None:
    profile = make_profile([
        Claim(claim_number="1", text="A device.", independent=True, limitations=["A device."])
    ])
    charts = asyncio.run(build_claim_charts(profile))
    report = build_report(
        "assessment-4",
        AssessmentCreate(title="Independent only", application_number="US-101"),
        AssessmentResults(patent_profile=profile, claim_charts=charts),
    )

    assert "0 dependent" in report.patent_intelligence.summary
    assert "No dependent claims were parsed" in report.patent_intelligence.summary


def test_report_explains_when_no_claims_were_parsed() -> None:
    profile = make_profile([])
    report = build_report(
        "assessment-2",
        AssessmentCreate(title="Unparsed patent", application_number="US-456"),
        AssessmentResults(patent_profile=profile),
    )

    assert "No numbered claims were parsed" in report.patent_intelligence.summary
    assert "0 parsed, 0 independent, 0 dependent; 0 independent charts" in report.patent_intelligence.summary
    assert "Evidence retrieval and matching are not configured" in report.patent_intelligence.summary
    assert "Extraction is a placeholder" not in report.patent_intelligence.summary


def test_report_handles_unavailable_profile_without_inventing_claim_counts() -> None:
    report = build_report(
        "assessment-3",
        AssessmentCreate(title="Missing profile", application_number="US-789"),
        AssessmentResults(),
    )

    assert "Patent profile is unavailable" in report.patent_intelligence.summary
    assert "Claim counts cannot be confirmed" in report.patent_intelligence.summary
