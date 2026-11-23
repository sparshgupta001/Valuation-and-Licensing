"""Claim chart scope and report-summary tests."""

import asyncio

import pytest

from app.ai.retrieval import RetrievedEvidence
from app.modules.claim_chart import service as claim_chart_service
from app.modules.claim_chart.service import build_claim_charts
from app.reports.builder import build_report
from app.schemas.assessment import AssessmentCreate
from app.schemas.intelligence import ClaimAssessment, ClaimChartEvidence, EvidenceRetrievalStatus
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
    assert "retrieval was unavailable" in summary
    assert "retrieval was unavailable" in report.claim_charts.summary


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
    assert "Evidence retrieval was not run" in report.patent_intelligence.summary
    assert "Extraction is a placeholder" not in report.patent_intelligence.summary


def test_report_handles_unavailable_profile_without_inventing_claim_counts() -> None:
    report = build_report(
        "assessment-3",
        AssessmentCreate(title="Missing profile", application_number="US-789"),
        AssessmentResults(),
    )

    assert "Patent profile is unavailable" in report.patent_intelligence.summary
    assert "Claim counts cannot be confirmed" in report.patent_intelligence.summary


def test_retrieval_runs_per_limitation_and_one_index_is_reused(monkeypatch) -> None:
    calls: list[tuple[str, tuple[str, ...]]] = []
    instances: list[object] = []

    class FakeRetriever:
        def __init__(self, assessment_id, documents, provider) -> None:
            assert assessment_id == "assessment-1"
            assert documents == ["evidence document"]
            assert provider is sentinel_provider
            instances.append(self)

        def search(self, query: str, *, roles):
            calls.append((query, tuple(roles)))
            if query == "A device comprising a sensor;":
                return [RetrievedEvidence(
                    assessment_id="assessment-1",
                    document_id="doc-1",
                    document_name="manual.pdf",
                    document_role="product_documentation",
                    page_number=4,
                    source_locator="page:4:chars:12-41",
                    start_offset=12,
                    end_offset=41,
                    passage="The controller includes a sensor;",
                    similarity_score=0.91,
                )]
            return []

    sentinel_provider = object()
    monkeypatch.setattr(claim_chart_service, "EvidenceRetriever", FakeRetriever)
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

    charts = asyncio.run(build_claim_charts(
        profile,
        assessment_id="assessment-1",
        evidence_documents=["evidence document"],
        embedding_provider=sentinel_provider,
    ))

    assert len(instances) == 1
    assert calls == [
        ("A device comprising a sensor;", ("product_documentation", "reference_prior_art")),
        ("and a controller.", ("product_documentation", "reference_prior_art")),
    ]
    assert [chart.claim_number for chart in charts] == ["1"]
    first, second = charts[0].rows
    assert first.assessment is ClaimAssessment.GAP
    assert first.confidence == 0.0
    assert first.needs_human_review is True
    assert first.retrieval_status is EvidenceRetrievalStatus.AVAILABLE
    assert first.evidence[0].model_dump() == {
        "document_name": "manual.pdf",
        "page": 4,
        "passage": "The controller includes a sensor;",
        "source_type": "document",
        "uri": None,
        "assessment_id": "assessment-1",
        "document_id": "doc-1",
        "document_role": "product_documentation",
        "source_locator": "page:4:chars:12-41",
        "start_offset": 12,
        "end_offset": 41,
        "similarity_score": 0.91,
    }
    assert second.evidence == []
    assert second.retrieval_status is EvidenceRetrievalStatus.NO_RESULTS
    assert second.assessment is ClaimAssessment.GAP
    assert second.confidence == 0.0


@pytest.mark.parametrize("failure_location", ["constructor", "search"])
def test_retrieval_failures_keep_provisional_gap_rows(monkeypatch, failure_location: str) -> None:
    class FailingRetriever:
        def __init__(self, *_args) -> None:
            if failure_location == "constructor":
                raise RuntimeError("model unavailable")

        def search(self, *_args, **_kwargs):
            raise RuntimeError("retrieval failed")

    monkeypatch.setattr(claim_chart_service, "EvidenceRetriever", FailingRetriever)
    profile = make_profile([
        Claim(
            claim_number="1",
            text="A device with a sensor and controller.",
            independent=True,
            limitations=["a sensor", "controller"],
        )
    ])

    charts = asyncio.run(build_claim_charts(
        profile,
        assessment_id="assessment-1",
        evidence_documents=[object()],
        embedding_provider=object(),
    ))

    assert len(charts[0].rows) == 2
    assert all(row.evidence == [] for row in charts[0].rows)
    assert all(row.assessment is ClaimAssessment.GAP for row in charts[0].rows)
    assert all(row.confidence == 0.0 for row in charts[0].rows)
    assert all(row.needs_human_review for row in charts[0].rows)
    assert all(row.retrieval_status is EvidenceRetrievalStatus.UNAVAILABLE for row in charts[0].rows)


def test_report_distinguishes_available_empty_and_unavailable_retrieval() -> None:
    profile = make_profile([
        Claim(claim_number="1", text="A device.", independent=True, limitations=["A device."])
    ])
    chart = asyncio.run(build_claim_charts(
        profile,
        assessment_id="assessment-1",
        evidence_documents=[],
    ))[0]
    empty_report = build_report(
        "assessment-1",
        AssessmentCreate(title="Patent", application_number="US-1"),
        AssessmentResults(patent_profile=profile, claim_charts=[chart]),
    )
    assert "retrieval completed with no relevant passages" in empty_report.claim_charts.summary

    chart.rows[0].retrieval_status = EvidenceRetrievalStatus.AVAILABLE
    chart.rows[0].evidence = [ClaimChartEvidence(
        passage="verbatim source text",
        similarity_score=0.7,
    )]
    available_report = build_report(
        "assessment-1",
        AssessmentCreate(title="Patent", application_number="US-1"),
        AssessmentResults(patent_profile=profile, claim_charts=[chart]),
    )
    assert "1 similarity-ranked passage(s)" in available_report.claim_charts.summary
    assert "do not establish coverage" in available_report.claim_charts.summary
    assert "1 similarity-ranked passage(s)" in available_report.patent_intelligence.summary

    unavailable_chart = asyncio.run(build_claim_charts(profile))[0]
    unavailable_report = build_report(
        "assessment-1",
        AssessmentCreate(title="Patent", application_number="US-1"),
        AssessmentResults(patent_profile=profile, claim_charts=[unavailable_chart]),
    )
    assert "retrieval was unavailable" in unavailable_report.claim_charts.summary
    assert "retrieval was unavailable" in unavailable_report.patent_intelligence.summary


def test_model_loading_failure_keeps_gap_rows(monkeypatch) -> None:
    class FailingModelProvider:
        def embed(self, _texts: list[str]) -> list[list[float]]:
            raise RuntimeError("model could not load")

    monkeypatch.setattr(claim_chart_service, "LocalEmbeddingProvider", FailingModelProvider)
    profile = make_profile([
        Claim(claim_number="1", text="A device.", independent=True, limitations=["A device."])
    ])
    document = type("EvidenceDocument", (), {
        "assessment_id": "assessment-1",
        "id": "doc-1",
        "filename": "manual.txt",
        "content_type": "text/plain",
        "role": "product_documentation",
        "content": b"A real passage.",
    })()

    charts = asyncio.run(build_claim_charts(
        profile,
        assessment_id="assessment-1",
        evidence_documents=[document],
    ))

    row = charts[0].rows[0]
    assert row.assessment is ClaimAssessment.GAP
    assert row.confidence == 0.0
    assert row.evidence == []
    assert row.needs_human_review is True
    assert row.retrieval_status is EvidenceRetrievalStatus.UNAVAILABLE
