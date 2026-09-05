from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from user_service.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(default=None)
    project_id: Mapped[int | None] = mapped_column(default=None)
    action: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str] = mapped_column(String(32), default="")
    resource_id: Mapped[str | None] = mapped_column(String(64), default=None)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
