"""API lifecycle and workflow graph tests."""

import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import sqlalchemy as sa
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.core.config import Settings
from app.database.models import Assessment, Document, DocumentRole
from app.main import create_app
from app.schemas.assessment import AssessmentCreate, CommercialInfo
from app.workflows.assessment_graph import STEP_NAMES, WorkflowOutcome, run_assessment_workflow


class FixedEmbeddingProvider:
    """Deterministic vectors for integration tests without loading a model."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * 383 for _ in texts]


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
            content=(
                b"Claims\n"
                b"1. A device comprising a sensor; and a controller.\n"
                b"2. The device of claim 1, wherein the controller stores data."
            ),
            headers={"content-type": "text/plain"},
        )
        assert uploaded.status_code == 201
        assert uploaded.json()["role"] == "target_patent"
        started = client.post(f"/api/v1/assessments/{assessment_id}/start")
        assert started.status_code == 200
        assert started.json()["state"] == "review_required"
        result = client.get(f"/api/v1/assessments/{assessment_id}/results")
        assert result.status_code == 200
        assert result.json()["report"]["recommendations"]["title"] == "Recommendations"
        assert [claim["claim_number"] for claim in result.json()["patent_profile"]["claims"]] == ["1", "2"]
        assert [chart["claim_number"] for chart in result.json()["claim_charts"]] == ["1"]
        assert "1 independent and 1 dependent" in result.json()["report"]["patent_intelligence"]["summary"]
        reviewed = client.post(
            f"/api/v1/assessments/{assessment_id}/review",
            json={"step": "claim_chart", "correction": {}, "reviewer_note": "Reviewed."},
        )
        assert reviewed.json()["state"] == "completed"
        assert reviewed.json()["human_review_pending"] is False


def test_upload_roles_validate_return_and_persist() -> None:
    """Uploads default compatibly and accept each supported role."""

    app = create_app(Settings(), database_url="sqlite://")
    roles = [role.value for role in DocumentRole]
    with TestClient(app) as client:
        created = client.post("/api/v1/assessments", json={"title": "A patent", "application_number": "US-role"})
        assessment_id = created.json()["assessment_id"]

        for index, role in enumerate(roles):
            uploaded = client.post(
                f"/api/v1/assessments/{assessment_id}/documents",
                params={"filename": f"document-{index}.txt", "role": role},
                content=f"role {role}".encode(),
                headers={"content-type": "text/plain"},
            )
            assert uploaded.status_code == 201
            assert uploaded.json()["role"] == role

        invalid = client.post(
            f"/api/v1/assessments/{assessment_id}/documents",
            params={"filename": "invalid.txt", "role": "unknown"},
            content=b"invalid role",
            headers={"content-type": "text/plain"},
        )
        assert invalid.status_code == 422

    with app.state.session_factory() as session:
        stored_roles = [document.role for document in session.query(Document).order_by(Document.filename)]
    assert stored_roles == roles


def test_document_model_defaults_role_for_legacy_python_writes() -> None:
    """Creating a Document without role uses its Python-side compatibility default."""

    app = create_app(Settings(), database_url="sqlite://")
    with app.state.session_factory() as session:
        assessment = Assessment(title="A", application_number="US-default")
        session.add(assessment)
        session.flush()
        document = Document(
            assessment_id=assessment.id,
            filename="legacy.txt",
            content_type="text/plain",
            size_bytes=4,
            content=b"text",
        )
        session.add(document)
        session.commit()
        assert document.role == "target_patent"


def test_only_target_patent_documents_feed_claim_extraction(monkeypatch) -> None:
    """Product documentation stays independent from patent profile extraction."""

    monkeypatch.setattr(
        "app.modules.claim_chart.service.LocalEmbeddingProvider",
        FixedEmbeddingProvider,
    )
    app = create_app(Settings(), database_url="sqlite://")
    with TestClient(app) as client:
        created = client.post("/api/v1/assessments", json={"title": "A patent", "application_number": "US-filter"})
        assessment_id = created.json()["assessment_id"]
        patent = client.post(
            f"/api/v1/assessments/{assessment_id}/documents",
            params={"filename": "patent.txt", "role": "target_patent"},
            content=b"Claims\n1. A patented device comprising a sensor.",
            headers={"content-type": "text/plain"},
        )
        product = client.post(
            f"/api/v1/assessments/{assessment_id}/documents",
            params={"filename": "product.txt", "role": "product_documentation"},
            content=b"Claims\n1. A product-only controller.",
            headers={"content-type": "text/plain"},
        )
        assert patent.status_code == product.status_code == 201
        started = client.post(f"/api/v1/assessments/{assessment_id}/start")
        assert started.status_code == 200
        results = client.get(f"/api/v1/assessments/{assessment_id}/results").json()

    assert [claim["text"] for claim in results["patent_profile"]["claims"]] == [
        "A patented device comprising a sensor."
    ]


def test_claim_charts_retrieve_only_current_assessment_evidence_roles(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.claim_chart.service.LocalEmbeddingProvider",
        FixedEmbeddingProvider,
    )
    app = create_app(Settings(), database_url="sqlite://")
    with TestClient(app) as client:
        current = client.post(
            "/api/v1/assessments",
            json={"title": "Current patent", "application_number": "US-current"},
        ).json()["assessment_id"]
        other = client.post(
            "/api/v1/assessments",
            json={"title": "Other assessment", "application_number": "US-other"},
        ).json()["assessment_id"]

        uploads = [
            (current, "patent.txt", "target_patent", "Claims\n1. A device comprising a sensor; and a controller."),
            (current, "product.txt", "product_documentation", "A product has a sensor and controller."),
            (current, "prior.txt", "reference_prior_art", "A reference describes a sensor."),
            (other, "foreign.txt", "product_documentation", "Foreign assessment-only content."),
        ]
        for assessment_id, filename, role, text_body in uploads:
            uploaded = client.post(
                f"/api/v1/assessments/{assessment_id}/documents",
                params={"filename": filename, "role": role},
                content=text_body.encode(),
                headers={"content-type": "text/plain"},
            )
            assert uploaded.status_code == 201

        started = client.post(f"/api/v1/assessments/{current}/start")
        assert started.status_code == 200
        results = client.get(f"/api/v1/assessments/{current}/results").json()

    assert [chart["claim_number"] for chart in results["claim_charts"]] == ["1"]
    rows = results["claim_charts"][0]["rows"]
    assert len(rows) == 2
    assert all(row["assessment"] == "GAP" for row in rows)
    assert all(row["confidence"] == 0.0 and row["needs_human_review"] for row in rows)
    assert all(row["retrieval_status"] == "available" for row in rows)
    evidence = [item for row in rows for item in row["evidence"]]
    assert {item["document_name"] for item in evidence} == {"product.txt", "prior.txt"}
    assert all(item["assessment_id"] == current for item in evidence)
    assert all(item["document_role"] in {"product_documentation", "reference_prior_art"} for item in evidence)
    assert all(item["passage"] in {"A product has a sensor and controller.", "A reference describes a sensor."} for item in evidence)
    assert all(item["similarity_score"] == 1.0 for item in evidence)


def test_ordinary_and_langgraph_workflows_pass_evidence_documents(monkeypatch) -> None:
    from app.workflows import assessment_graph

    calls: list[tuple[str, object]] = []
    evidence_documents = [SimpleNamespace(assessment_id="workflow-1", role="product_documentation")]

    async def record_chart_call(profile, *, assessment_id, evidence_documents):
        calls.append((assessment_id, evidence_documents))
        return []

    monkeypatch.setattr(assessment_graph, "build_claim_charts", record_chart_call)
    assessment = AssessmentCreate(title="Workflow patent", application_number="US-workflow")
    commercial_info = CommercialInfo()
    patent_text = "Claims\n1. A device comprising a sensor."

    async def exercise_ordinary_workflow() -> None:
        await assessment_graph.run_assessment_workflow(
            "workflow-1",
            assessment,
            commercial_info,
            patent_text=patent_text,
            evidence_documents=evidence_documents,
        )

    asyncio.run(exercise_ordinary_workflow())
    assert calls == [("workflow-1", evidence_documents)]

    pytest.importorskip("langgraph.graph")
    graph = assessment_graph.build_langgraph()

    async def exercise_langgraph() -> None:
        await graph.ainvoke({
            "assessment_id": "workflow-1",
            "assessment": assessment,
            "commercial_info": commercial_info,
            "patent_text": patent_text,
            "evidence_documents": evidence_documents,
        })

    asyncio.run(exercise_langgraph())
    assert calls == [("workflow-1", evidence_documents), ("workflow-1", evidence_documents)]


def test_document_role_migration_preserves_existing_data_and_downgrades() -> None:
    """The additive migration backfills old rows and downgrade preserves their data."""

    migration_path = Path(__file__).parents[2] / "migrations" / "versions" / "0002_document_role.py"
    spec = importlib.util.spec_from_file_location("migration_0002_document_role", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE documents (id VARCHAR(36) PRIMARY KEY, filename VARCHAR(500), content BLOB)"
        ))
        connection.execute(text("INSERT INTO documents (id, filename, content) VALUES ('doc-1', 'old.txt', X'74657874')"))
        operations = Operations(MigrationContext.configure(connection))
        original_op = migration.op
        migration.op = operations
        try:
            migration.upgrade()
            row = connection.execute(text("SELECT filename, content, role FROM documents WHERE id='doc-1'")).one()
            assert row == ("old.txt", b"text", "target_patent")
            connection.execute(text(
                "INSERT INTO documents (id, filename, content) VALUES ('doc-2', 'new.txt', X'6e6577')"
            ))
            new_row = connection.execute(text("SELECT role FROM documents WHERE id='doc-2'")).one()
            assert new_row == ("target_patent",)
            assert "role" in {column["name"] for column in inspect(connection).get_columns("documents")}

            migration.downgrade()
            row_after_downgrade = connection.execute(text("SELECT filename, content FROM documents WHERE id='doc-1'")).one()
            assert row_after_downgrade == ("old.txt", b"text")
            assert "role" not in {column["name"] for column in inspect(connection).get_columns("documents")}
        finally:
            migration.op = original_op
    engine.dispose()


def test_document_role_migration_tolerates_initial_metadata_column() -> None:
    """A fresh-schema role value is not overwritten by the follow-up migration."""

    migration_path = Path(__file__).parents[2] / "migrations" / "versions" / "0002_document_role.py"
    spec = importlib.util.spec_from_file_location("migration_0002_document_role_fresh", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE documents (id VARCHAR(36) PRIMARY KEY, filename VARCHAR(500), content BLOB, role VARCHAR(40) NOT NULL DEFAULT 'target_patent')"
        ))
        connection.execute(text(
            "INSERT INTO documents (id, filename, content, role) VALUES ('doc-1', 'product.txt', X'74657874', 'product_documentation')"
        ))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        row = connection.execute(text("SELECT filename, content, role FROM documents WHERE id='doc-1'")).one()
        assert row == ("product.txt", b"text", "product_documentation")
        migration.downgrade()
        row_after_downgrade = connection.execute(text("SELECT filename, content FROM documents WHERE id='doc-1'")).one()
        assert row_after_downgrade == ("product.txt", b"text")
    engine.dispose()


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
