from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ci_service.db.base import Base

PIPELINE_STATUSES = ("pending", "running", "success", "failed", "canceled")


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    repository_id: Mapped[int | None] = mapped_column(default=None)
    repository: Mapped[str] = mapped_column(String(256), default="")
    commit_sha: Mapped[str] = mapped_column(String(64), default="")
    branch: Mapped[str] = mapped_column(String(256), default="main")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    trigger_type: Mapped[str] = mapped_column(String(16), default="webhook")  # webhook/manual
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    builds: Mapped[list["Build"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan"
    )


class Build(Base):
    __tablename__ = "builds"

    id: Mapped[int] = mapped_column(primary_key=True)
    pipeline_id: Mapped[int] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    logs: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    pipeline: Mapped["Pipeline"] = relationship(back_populates="builds")


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
