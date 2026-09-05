from fastapi import APIRouter

from user_service.api.deps import CurrentUser
from user_service.schemas.user import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser) -> UserOut:
    return UserOut.model_validate(current_user)
