from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from notification_service.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 各服务独立数据库，不设跨库外键，只保留逻辑关联
    user_id: Mapped[int] = mapped_column(index=True)
    # 用于消费幂等：同一事件只产生一条通知
    event_id: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[str] = mapped_column(Text, default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
