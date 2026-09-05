from fastapi import APIRouter
from sqlalchemy import select

from user_service.api.deps import CurrentUser, DBSession
from user_service.models.audit import AuditLog

router = APIRouter(prefix="/users", tags=["audit"])


@router.get("/me/audit")
async def my_audit(user: CurrentUser, db: DBSession) -> list[dict]:
    result = await db.execute(
        select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.id.desc()).limit(50)
    )
    rows = result.scalars().all()
    return [
        {
            "id": a.id,
            "action": a.action,
            "resource_type": a.resource_type,
            "resource_id": a.resource_id,
            "created_at": a.created_at.isoformat(),
        }
        for a in rows
    ]
