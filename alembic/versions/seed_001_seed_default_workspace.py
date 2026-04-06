"""Seed default workspace

Revision ID: seed_001
Revises: 8bb6cac3dfc3
Create Date: 2026-04-06 21:34:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "seed_001"
down_revision: str | Sequence[str] | None = "8bb6cac3dfc3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create default workspace."""
    workspaces_table = sa.table(
        "workspaces",
        sa.column("id", sa.Uuid),
        sa.column("name", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )

    op.execute(
        workspaces_table.insert().values(
            id=uuid.uuid4(),
            name="Default Workspace",
        )
    )


def downgrade() -> None:
    """Remove default workspace."""
    op.execute("DELETE FROM workspaces WHERE name = 'Default Workspace'")
