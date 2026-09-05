from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from notification_service.api.deps import CurrentUser, DBSession
from notification_service.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(user: CurrentUser, db: DBSession) -> list[dict]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user)
        .order_by(Notification.id.desc())
        .limit(50)
    )
    items = result.scalars().all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "read": n.read,
            "created_at": n.created_at.isoformat(),
        }
        for n in items
    ]


@router.post("/{notification_id}/read")
async def mark_read(notification_id: int, user: CurrentUser, db: DBSession) -> dict:
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user)
    )
    n = result.scalar_one_or_none()
    if n is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "notification not found")
    n.read = True
    return {"id": n.id, "read": n.read}
