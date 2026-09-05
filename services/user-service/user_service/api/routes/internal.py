from fastapi import APIRouter, Depends, HTTPException, status

from user_service.api.deps import DBSession, require_internal_token
from user_service.repositories.user import UserRepository
from user_service.schemas.user import LookupByIdRequest, LookupRequest, UserBrief

router = APIRouter(prefix="/internal/users", tags=["internal"])


@router.get("/{user_id}", response_model=UserBrief, dependencies=[Depends(require_internal_token)])
async def get_user(user_id: int, db: DBSession) -> UserBrief:
    user = await UserRepository(db).get(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    return UserBrief(id=user.id, username=user.username)


@router.post(
    "/lookup", response_model=list[UserBrief], dependencies=[Depends(require_internal_token)]
)
async def lookup_by_usernames(body: LookupRequest, db: DBSession) -> list[UserBrief]:
    users = await UserRepository(db).get_many_by_usernames(body.usernames)
    return [UserBrief(id=u.id, username=u.username) for u in users]


@router.post(
    "/lookup-ids", response_model=list[UserBrief], dependencies=[Depends(require_internal_token)]
)
async def lookup_by_ids(body: LookupByIdRequest, db: DBSession) -> list[UserBrief]:
    users = await UserRepository(db).get_many_by_ids(body.ids)
    return [UserBrief(id=u.id, username=u.username) for u in users]
