from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from project_service.db.base import Base


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    topic: Mapped[str] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(1024), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(String(2048), default="")
    visibility: Mapped[str] = mapped_column(String(16), default="private")
    created_by: Mapped[int] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(index=True)
    role: Mapped[str] = mapped_column(String(16), default="developer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="members")


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (Index("ix_issues_project_status", "project_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    number: Mapped[int | None] = mapped_column(default=None)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(String(16), default="task")
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    assignee_id: Mapped[int | None] = mapped_column(default=None)
    creator_id: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


ISSUE_TYPES = ("issue", "bug", "task")
ISSUE_PRIORITIES = ("low", "medium", "high", "critical")
ISSUE_STATUSES = ("open", "in_progress", "done", "closed")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column()
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Repository(Base):
    """Git repository integration (Phase 6). external_id is GitHub full_name."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(16), default="github")
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    url: Mapped[str] = mapped_column(String(512), default="")
    default_branch: Mapped[str] = mapped_column(String(128), default="main")
    webhook_secret_configured: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repository_id", "external_id", name="uq_repo_pr"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    external_id: Mapped[int] = mapped_column()
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="")
    author_login: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="open")
    source_branch: Mapped[str] = mapped_column(String(256), default="")
    target_branch: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
