"""project service initial schema

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
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, index=True),
        sa.Column("description", sa.String(2048), nullable=False, server_default=""),
        sa.Column("visibility", sa.String(16), nullable=False, server_default="private"),
        sa.Column("created_by", sa.Integer(), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("role", sa.String(16), nullable=False, server_default="developer"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )
    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("type", sa.String(16), nullable=False, server_default="task"),
        sa.Column("priority", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(16), nullable=False, server_default="open", index=True),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_issues_project_status", "issues", ["project_id", "status"])
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "issue_id", sa.Integer(), sa.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(16), nullable=False, server_default="github"),
        sa.Column("external_id", sa.String(128), nullable=False, index=True),
        sa.Column("url", sa.String(512), nullable=False, server_default=""),
        sa.Column("default_branch", sa.String(128), nullable=False, server_default="main"),
        sa.Column(
            "webhook_secret_configured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "pull_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "repository_id",
            sa.Integer(),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("author_login", sa.String(128), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("source_branch", sa.String(256), nullable=False, server_default=""),
        sa.Column("target_branch", sa.String(256), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("repository_id", "external_id", name="uq_repo_pr"),
    )


def downgrade() -> None:
    op.drop_table("pull_requests")
    op.drop_table("repositories")
    op.drop_table("comments")
    op.drop_index("ix_issues_project_status", table_name="issues")
    op.drop_table("issues")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("outbox_events")
