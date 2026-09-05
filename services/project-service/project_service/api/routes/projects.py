from typing import Annotated

from codeflow_common.idempotency import with_idempotency
from fastapi import APIRouter, Header, HTTPException, Query, Response, status

from project_service.api.deps import (
    CacheDep,
    CurrentUser,
    DBSession,
    UserClientDep,
    get_user_client,
)
from project_service.schemas.project import (
    Page,
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberOut,
    ProjectMemberUpdate,
    ProjectOut,
    ProjectUpdate,
)
from project_service.services.project import ProjectError, ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def _error(exc: ProjectError, code: int = status.HTTP_404_NOT_FOUND) -> HTTPException:
    return HTTPException(code, str(exc))


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    response: Response,
    user: CurrentUser,
    db: DBSession,
    cache: CacheDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ProjectOut:
    service = ProjectService(db, get_user_client())

    async def execute() -> ProjectOut:
        project = await service.create(user, body.name, body.description, body.visibility)
        return ProjectOut.model_validate(project)

    key = f"create-project:{user}:{idempotency_key}" if idempotency_key else None
    result = await with_idempotency(cache, key, execute)
    if result is None:
        return await execute()

    # 首次执行或幂等重放都返回缓存的响应快照
    data = result.response
    if result.replayed:
        response.status_code = status.HTTP_200_OK
    return data if isinstance(data, ProjectOut) else ProjectOut(**data)


@router.get("", response_model=Page)
async def list_projects(
    user: CurrentUser,
    db: DBSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page:
    items, total = await ProjectService(db, get_user_client()).list_for_user(
        user, offset=offset, limit=limit
    )
    return Page(total=total, items=[ProjectOut.model_validate(p) for p in items])


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: int, user: CurrentUser, db: DBSession, cache: CacheDep
) -> ProjectOut:
    service = ProjectService(db, get_user_client())
    try:
        await service.require_role(project_id, user, "viewer")
    except ProjectError as exc:
        raise _error(exc) from exc

    async def builder() -> ProjectOut:
        project = await service.get(project_id)
        return ProjectOut.model_validate(project)

    result: ProjectOut = await cache.get_or_set(f"project:{project_id}", builder)
    return result


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: int, body: ProjectUpdate, user: CurrentUser, db: DBSession, cache: CacheDep
) -> ProjectOut:
    service = ProjectService(db, get_user_client())
    try:
        await service.require_role(project_id, user, "admin")
        project = await service.update(project_id, body.model_dump(exclude_unset=True), user)
    except ProjectError as exc:
        raise _error(exc) from exc
    await cache.delete(f"project:{project_id}")
    return ProjectOut.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int, user: CurrentUser, db: DBSession, cache: CacheDep
) -> None:
    service = ProjectService(db, get_user_client())
    try:
        await service.require_role(project_id, user, "owner")
        await service.delete(project_id, user)
    except ProjectError as exc:
        raise _error(exc) from exc
    await cache.delete(f"project:{project_id}")


@router.get("/{project_id}/members", response_model=list[ProjectMemberOut])
async def list_members(
    project_id: int, user: CurrentUser, db: DBSession, client: UserClientDep
) -> list[ProjectMemberOut]:
    service = ProjectService(db, client)
    try:
        await service.require_role(project_id, user, "viewer")
        members = await service.list_members(project_id)
    except ProjectError as exc:
        raise _error(exc) from exc
    return [
        ProjectMemberOut(
            id=m.id,
            user_id=m.user_id,
            username=username or "",
            role=m.role,
            created_at=m.created_at,
        )
        for m, username in members
    ]


@router.post(
    "/{project_id}/members", response_model=ProjectMemberOut, status_code=status.HTTP_201_CREATED
)
async def add_member(
    project_id: int, body: ProjectMemberAdd, user: CurrentUser, db: DBSession
) -> ProjectMemberOut:
    service = ProjectService(db, get_user_client())
    try:
        await service.require_role(project_id, user, "admin")
        member = await service.add_member(project_id, body.username, body.role, user)
    except ProjectError as exc:
        raise _error(exc, status.HTTP_400_BAD_REQUEST) from exc
    username = await get_user_client().get_username(member.user_id)
    return ProjectMemberOut(
        id=member.id,
        user_id=member.user_id,
        username=username or "",
        role=member.role,
        created_at=member.created_at,
    )


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberOut)
async def update_member(
    project_id: int, user_id: int, body: ProjectMemberUpdate, user: CurrentUser, db: DBSession
) -> ProjectMemberOut:
    service = ProjectService(db, get_user_client())
    try:
        await service.require_role(project_id, user, "admin")
        member = await service.update_member_role(project_id, user_id, body.role)
    except ProjectError as exc:
        raise _error(exc, status.HTTP_400_BAD_REQUEST) from exc
    username = await get_user_client().get_username(member.user_id)
    return ProjectMemberOut(
        id=member.id,
        user_id=member.user_id,
        username=username or "",
        role=member.role,
        created_at=member.created_at,
    )


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(project_id: int, user_id: int, user: CurrentUser, db: DBSession) -> None:
    service = ProjectService(db, get_user_client())
    try:
        await service.require_role(project_id, user, "admin")
        await service.remove_member(project_id, user_id)
    except ProjectError as exc:
        raise _error(exc, status.HTTP_400_BAD_REQUEST) from exc
