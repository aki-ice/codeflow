"""审计写入：写操作同事务落库 + outbox 事件。"""

from typing import Any

from codeflow_common.audit import build_audit_record
from codeflow_common.outbox import emit
from sqlalchemy.ext.asyncio import AsyncSession

from project_service.models.audit import AuditLog
from project_service.models.project import OutboxEvent


async def write_audit(
    db: AsyncSession,
    user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | str | None = None,
    project_id: int | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    db.add(
        build_audit_record(
            AuditLog,
            user_id,
            action,
            resource_type,
            resource_id,
            detail,
            project_id,
        )
    )
    await emit(
        db,
        OutboxEvent,
        f"audit.{action.replace('.', '_')}",
        user_id=user_id,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
    )
