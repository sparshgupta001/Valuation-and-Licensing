"""API lifecycle and workflow graph tests."""

import asyncio
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.core.config import Settings
from app.database.models import Assessment, Document, DocumentRole
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


def test_only_target_patent_documents_feed_claim_extraction() -> None:
    """Product documentation stays independent from patent profile extraction."""

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
