"""ai service initial schema

Revision ID: 0001_initial
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("doc_name", sa.String(256), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "ai_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("pull_request_id", sa.Integer(), nullable=True),
        sa.Column("summary", sa.String(2048), nullable=False, server_default=""),
        sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("topic", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_events_event_id", "outbox_events", ["event_id"], unique=True)
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"])
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])


def downgrade() -> None:
    op.drop_table("outbox_events")
    op.drop_table("ai_reviews")
    op.drop_table("documents")
