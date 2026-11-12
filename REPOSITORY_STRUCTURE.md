# Repository structure

Each entry includes its purpose. Generated Python cache files are omitted.

```text
skits-strategos-backend/
├── .env.example — environment variable template for local and container runs
├── .gitignore — excludes local environments, caches, databases, and artifacts
├── Dockerfile — builds the Python API image with OCR binary support
├── README.md — setup, routes, architecture, tests, boundaries, and next steps
├── REPOSITORY_STRUCTURE.md — this file-by-file inventory
├── alembic.ini — Alembic migration configuration
├── docker-compose.yml — API and pgvector PostgreSQL services
├── requirements.txt — pinned Python runtime and test dependencies
├── app/ — FastAPI application and domain code
│   ├── __init__.py — application package marker
│   ├── main.py — application factory, database initialization, and health route
│   ├── ai/ — replaceable AI, embedding, retrieval, and reranking interfaces
│   │   ├── __init__.py — AI package marker
│   │   ├── embeddings.py — embedding provider protocol and offline stub
│   │   ├── llm_provider.py — LLM interface and placeholder provider
│   │   ├── reranker.py — evidence reranking interface
│   │   └── retrieval.py — evidence retrieval interface
│   ├── api/ — HTTP dependencies and versioned route modules
│   │   ├── __init__.py — API package marker
│   │   ├── deps.py — request-scoped SQLAlchemy session dependency
│   │   └── v1/ — version 1 endpoints
│   │       ├── __init__.py — v1 package marker
│   │       ├── assessments.py — create, upload, commercial input, run, status, result, and review endpoints
│   │       ├── claim_charts.py — claim chart result endpoint
│   │       ├── competitors.py — licensing target result endpoint
│   │       ├── negotiation.py — negotiation brief endpoint
│   │       ├── patents.py — patent profile endpoint
│   │       └── valuation.py — valuation result endpoint
│   ├── core/ — configuration and security extension points
│   │   ├── __init__.py — core package marker
│   │   ├── config.py — typed environment settings
│   │   └── security.py — authentication dependency placeholder
│   ├── database/ — SQLAlchemy models, sessions, and query helpers
│   │   ├── __init__.py — database package marker
│   │   ├── base.py — declarative model base
│   │   ├── models.py — assessment, document, step, and vector tables
│   │   ├── repositories.py — assessment and workflow query helpers
│   │   └── session.py — engine and session factory
│   ├── ingestion/ — document dispatch and lazy extraction adapters
│   │   ├── __init__.py — ingestion package marker
│   │   ├── document_loader.py — PDF, DOCX, text, and JSON dispatch
│   │   ├── ocr.py — lazy Tesseract image OCR adapter
│   │   └── pdf_parser.py — selectable PDF text and scanned-page OCR fallback
│   ├── modules/ — domain services separated from AI interfaces
│   │   ├── __init__.py — modules package marker
│   │   ├── claim_chart/ — limitation mapping service
│   │   │   ├── __init__.py — claim chart package marker
│   │   │   └── service.py — conservative, reviewable chart placeholder
│   │   ├── competitor_intelligence/ — commercial target discovery
│   │   │   ├── __init__.py — competitor intelligence package marker
│   │   │   └── service.py — target ranking interface with no unsupported candidates
│   │   ├── negotiation/ — deterministic royalty corridor and brief
│   │   │   ├── __init__.py — negotiation package marker
│   │   │   └── service.py — corridor calculator and narrative placeholder
│   │   ├── patent_intelligence/ — patent profile extraction
│   │   │   ├── __init__.py — patent intelligence package marker
│   │   │   └── service.py — reviewable patent profile placeholder
│   │   └── valuation/ — deterministic valuation calculations
│   │       ├── __init__.py — valuation package marker
│   │       ├── calculations.py — DCF, relief-from-royalty, cost, Monte Carlo, and strength math
│   │       ├── engine.py — method assembly and missing-input reporting
│   │       └── service.py — commercial input mapping to valuation engine
│   ├── reports/ — final report assembly
│   │   ├── __init__.py — reports package marker
│   │   └── builder.py — requested nine-section assessment report
│   ├── schemas/ — typed request and response models
│   │   ├── __init__.py — schemas package marker
│   │   ├── assessment.py — screen 1 and optional screen 2 inputs
│   │   ├── common.py — provenance, evidence, workflow, and status types
│   │   ├── intelligence.py — competitor and claim chart outputs
│   │   ├── negotiation.py — negotiation brief schema
│   │   ├── patent.py — patent profile and claim schemas
│   │   ├── report.py — result bundle and report sections
│   │   └── valuation.py — financial inputs and valuation results
│   ├── services/ — persisted assessment use cases
│   │   ├── __init__.py — services package marker
│   │   └── assessment_service.py — lifecycle, workflow execution, and review persistence
│   └── workflows/ — graph orchestration and per-step states
│       ├── __init__.py — workflows package marker
│       └── assessment_graph.py — parallel runner and optional LangGraph adapter
├── migrations/ — Alembic environment and versions
│   ├── env.py — application settings and metadata wiring
│   ├── script.py.mako — migration revision template
│   └── versions/ — ordered migration scripts
│       └── 0001_initial.py — initial tables and pgvector extension setup
├── scripts/ — local project utilities
│   └── init_db.py — create declared tables for local development
└── tests/ — API, schema, workflow, and calculation checks
    ├── __init__.py — test package marker
    ├── integration/ — API and graph tests
    │   ├── __init__.py — integration test package marker
    │   └── test_api_and_workflow.py — health, lifecycle, parallelism, and dependency order
    └── unit/ — schema and deterministic math tests
        ├── __init__.py — unit test package marker
        ├── test_schemas.py — optional inputs, provenance, and schema validation
        └── test_valuation.py — calculation values and missing-input behavior
```
