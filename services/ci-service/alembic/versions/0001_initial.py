"""ci service initial schema

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
        "pipelines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("repository_id", sa.Integer(), nullable=True),
        sa.Column("repository", sa.String(256), nullable=False, server_default=""),
        sa.Column("commit_sha", sa.String(64), nullable=False, server_default=""),
        sa.Column("branch", sa.String(256), nullable=False, server_default="main"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending", index=True),
        sa.Column("trigger_type", sa.String(16), nullable=False, server_default="webhook"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "builds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "pipeline_id",
            sa.Integer(),
            sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("logs", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
    op.drop_table("builds")
    op.drop_table("pipelines")
