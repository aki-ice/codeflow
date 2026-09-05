from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_service.db.base import Base


class Document(Base):
    """RAG 知识库文档（分块后入库）。

    embedding 用 JSON 列存储（所有数据库通用）；
    Postgres + pgvector 可用时额外维护 embedding_vec 向量列加速检索。
    """

    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_project", "project_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column()
    doc_name: Mapped[str] = mapped_column(String(256))
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiReview(Base):
    """AI Code Review 结果（对应文档第 30 节）。"""

    __tablename__ = "ai_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(default=None)
    pull_request_id: Mapped[int | None] = mapped_column(default=None)
    summary: Mapped[str] = mapped_column(String(2048), default="")
    severity: Mapped[str] = mapped_column(String(16), default="info")  # info/low/medium/high
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
