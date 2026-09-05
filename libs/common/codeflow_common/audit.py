"""审计日志通用构建器（各服务在自身库维护 audit_logs 表）。"""

from datetime import UTC, datetime
from typing import Any

from codeflow_common.envelope import Event


def build_audit_record(
    audit_model: type,
    user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str | int | None = None,
    detail: dict[str, Any] | None = None,
    project_id: int | None = None,
) -> Any:
    kwargs: dict[str, Any] = {}
    if project_id is not None:
        kwargs["project_id"] = project_id
    return audit_model(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        detail=detail or {},
        **kwargs,
    )


def audit_event(action: str, resource_type: str, resource_id: Any, user_id: int | None) -> Event:
    return Event(
        event_type=f"audit.{action}",
        payload={
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id is not None else None,
            "action": action,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
