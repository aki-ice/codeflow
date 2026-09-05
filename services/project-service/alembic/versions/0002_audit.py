"""audit_logs 表

Revision ID: 0002_audit
Revises: 0001_initial
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_audit"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False, server_default=""),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_logs_project", "audit_logs", ["project_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
