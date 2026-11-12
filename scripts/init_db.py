"""Create application tables for local development without running Alembic."""

from app.core.config import get_settings
from app.database.base import Base
from app.database.session import make_engine


def main() -> None:
    """Create all currently declared tables."""

    engine = make_engine(get_settings().database_url)
    Base.metadata.create_all(engine)
    print("Database tables are ready.")


if __name__ == "__main__":
    main()
