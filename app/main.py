"""FastAPI application factory and health check."""

from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import assessments, claim_charts, competitors, negotiation, patents, valuation
from app.core.config import Settings, get_settings
from app.database.base import Base
from app.database.session import make_engine, make_session_factory


def create_app(settings: Settings | None = None, *, database_url: str | None = None) -> FastAPI:
    """Create an isolated API instance and database session factory."""

    active_settings = settings or get_settings()
    active_database_url = database_url or active_settings.database_url
    engine = make_engine(active_database_url)
    if active_database_url.startswith(("postgresql", "postgres")):
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    application = FastAPI(title=active_settings.app_name, version="0.1.0", debug=active_settings.debug)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
    )
    application.state.settings = active_settings
    application.state.engine = engine
    application.state.session_factory = make_session_factory(engine)
    application.include_router(assessments.router, prefix=active_settings.api_v1_prefix)
    for route in (patents.router, competitors.router, claim_charts.router, valuation.router, negotiation.router):
        application.include_router(route, prefix=active_settings.api_v1_prefix)

    @application.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """Return a lightweight liveness response."""

        return {"status": "ok"}

    return application


app = create_app()
