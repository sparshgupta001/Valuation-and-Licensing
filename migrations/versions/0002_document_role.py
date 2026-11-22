"""Add role classification to stored documents."""

import sqlalchemy as sa
from alembic import op

revision = "0002_document_role"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a role without rebuilding tables or changing existing document data."""

    # The initial migration creates tables from live metadata. On a fresh
    # install that may already include this column, while upgraded databases
    # still need the additive change.
    if "role" in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("documents")}:
        return
    op.add_column(
        "documents",
        sa.Column(
            "role",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'target_patent'"),
        ),
    )


def downgrade() -> None:
    """Remove only the role column; preserve all existing document records."""

    if "role" in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("documents")}:
        op.drop_column("documents", "role")
