from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from project_service.api.deps import CurrentUser, DBSession
from project_service.models.audit import AuditLog
from project_service.services.project import ProjectError, ProjectService

router = APIRouter(tags=["audit"])


@router.get("/audit")
async def list_audit(
    user: CurrentUser,
    db: DBSession,
    project_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[dict]:
    """审计记录查询：按项目过滤时要求成员身份；无 project_id 只看自己触发的。"""
    service = ProjectService(db)
    if project_id is not None:
        try:
            await service.require_role(project_id, user, "viewer")
        except ProjectError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
        base = select(AuditLog).where(AuditLog.project_id == project_id)
    else:
        base = select(AuditLog).where(AuditLog.user_id == user)
    result = await db.execute(base.order_by(AuditLog.id.desc()).limit(limit))
    rows = result.scalars().all()
    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "project_id": a.project_id,
            "action": a.action,
            "resource_type": a.resource_type,
            "resource_id": a.resource_id,
            "detail": a.detail,
            "created_at": a.created_at.isoformat(),
        }
        for a in rows
    ]
