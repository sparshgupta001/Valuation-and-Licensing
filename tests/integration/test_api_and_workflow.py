"""API lifecycle and workflow graph tests."""

import asyncio

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.schemas.assessment import AssessmentCreate, CommercialInfo
from app.workflows.assessment_graph import STEP_NAMES, WorkflowOutcome, run_assessment_workflow


def test_health_endpoint() -> None:
    """The application factory exposes health without external services."""

    app = create_app(Settings(), database_url="sqlite://")
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_assessment_api_runs_end_to_end() -> None:
    """Create, start, inspect, and review a placeholder assessment through HTTP."""

    app = create_app(Settings(), database_url="sqlite://")
    with TestClient(app) as client:
        created = client.post("/api/v1/assessments", json={"title": "A patent", "application_number": "US-1"})
        assessment_id = created.json()["assessment_id"]
        uploaded = client.post(
            f"/api/v1/assessments/{assessment_id}/documents",
            params={"filename": "patent.txt"},
            content=b"Example patent text.",
            headers={"content-type": "text/plain"},
        )
        assert uploaded.status_code == 201
        started = client.post(f"/api/v1/assessments/{assessment_id}/start")
        assert started.status_code == 200
        assert started.json()["state"] == "review_required"
        result = client.get(f"/api/v1/assessments/{assessment_id}/results")
        assert result.status_code == 200
        assert result.json()["report"]["recommendations"]["title"] == "Recommendations"
        reviewed = client.post(
            f"/api/v1/assessments/{assessment_id}/review",
            json={"step": "claim_chart", "correction": {}, "reviewer_note": "Reviewed."},
        )
        assert reviewed.json()["state"] == "completed"
        assert reviewed.json()["human_review_pending"] is False


def test_graph_parallel_branches_and_dependency_order() -> None:
    """Three branches start together; dependent stages wait for their inputs."""

    async def execute() -> WorkflowOutcome:
        """Run one assessment graph fixture."""

        return await run_assessment_workflow(
            "graph-test",
            AssessmentCreate(title="Patent", application_number="US-42"),
            CommercialInfo(),
        )

    outcome = asyncio.run(execute())
    steps = outcome["steps"]
    by_name = {step.name: step for step in steps}
    assert tuple(step.name for step in steps) == STEP_NAMES
    assert by_name["patent_intelligence"].completed_at <= by_name["competitor_intelligence"].started_at
    assert by_name["patent_intelligence"].completed_at <= by_name["claim_chart"].started_at
    assert by_name["patent_intelligence"].completed_at <= by_name["valuation"].started_at
    assert max(
        by_name[name].started_at for name in ("competitor_intelligence", "claim_chart", "valuation")
    ) <= min(
        by_name[name].completed_at for name in ("competitor_intelligence", "claim_chart", "valuation")
    )
    assert by_name["negotiation"].started_at >= max(
        by_name["competitor_intelligence"].completed_at, by_name["valuation"].completed_at
    )
    assert by_name["report_builder"].started_at >= max(
        by_name["negotiation"].completed_at, by_name["claim_chart"].completed_at
    )
    assert by_name["human_review_checkpoint"].started_at >= by_name["report_builder"].completed_at
