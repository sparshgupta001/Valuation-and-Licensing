"""Create the initial assessment and pgvector-ready tables."""

from alembic import op

from app.database.base import Base
from app.database import models  # noqa: F401 - register all models

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all scaffold tables from SQLAlchemy metadata."""

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drop all scaffold tables."""

    Base.metadata.drop_all(bind=op.get_bind())
