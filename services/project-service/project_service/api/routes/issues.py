from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from project_service.api.deps import CurrentUser, DBSession, get_user_client
from project_service.schemas.issue import (
    CommentCreate,
    CommentOut,
    IssueCreate,
    IssueOut,
    IssuePage,
    IssueUpdate,
)
from project_service.services.issue import IssueError, IssueService
from project_service.services.project import ProjectError

router = APIRouter(tags=["issues"])


def _error(exc: Exception, code: int = status.HTTP_404_NOT_FOUND) -> HTTPException:
    return HTTPException(code, str(exc))


@router.post(
    "/projects/{project_id}/issues", response_model=IssueOut, status_code=status.HTTP_201_CREATED
)
async def create_issue(
    project_id: int, body: IssueCreate, user: CurrentUser, db: DBSession
) -> IssueOut:
    service = IssueService(db, get_user_client())
    try:
        issue = await service.create(
            user,
            project_id,
            body.title,
            body.description,
            body.type,
            body.priority,
            body.assignee_id,
        )
    except ProjectError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except IssueError as exc:
        raise _error(exc, status.HTTP_400_BAD_REQUEST) from exc
    return IssueOut.model_validate(issue)


@router.get("/projects/{project_id}/issues", response_model=IssuePage)
async def list_issues(
    project_id: int,
    user: CurrentUser,
    db: DBSession,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    assignee_id: int | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> IssuePage:
    service = IssueService(db, get_user_client())
    try:
        items, total = await service.list_for_project(
            user, project_id, status_filter, assignee_id, offset, limit
        )
    except IssueError as exc:
        raise _error(exc) from exc
    return IssuePage(total=total, items=[IssueOut.model_validate(i) for i in items])


@router.get("/issues/{issue_id}", response_model=IssueOut)
async def get_issue(issue_id: int, user: CurrentUser, db: DBSession) -> IssueOut:
    try:
        issue = await IssueService(db, get_user_client()).get_for_user(issue_id, user)
    except IssueError as exc:
        raise _error(exc) from exc
    return IssueOut.model_validate(issue)


@router.patch("/issues/{issue_id}", response_model=IssueOut)
async def update_issue(
    issue_id: int, body: IssueUpdate, user: CurrentUser, db: DBSession
) -> IssueOut:
    service = IssueService(db, get_user_client())
    try:
        issue = await service.update(issue_id, user, body.model_dump(exclude_unset=True))
    except IssueError as exc:
        raise _error(exc) from exc
    return IssueOut.model_validate(issue)


@router.delete("/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(issue_id: int, user: CurrentUser, db: DBSession) -> None:
    try:
        await IssueService(db, get_user_client()).delete(issue_id, user)
    except IssueError as exc:
        raise _error(exc) from exc


@router.post(
    "/issues/{issue_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED
)
async def create_comment(
    issue_id: int, body: CommentCreate, user: CurrentUser, db: DBSession
) -> CommentOut:
    service = IssueService(db, get_user_client())
    try:
        comment = await service.add_comment(issue_id, user, body.content)
    except IssueError as exc:
        raise _error(exc, status.HTTP_400_BAD_REQUEST) from exc
    username = await get_user_client().get_username(comment.user_id)
    return CommentOut(
        id=comment.id,
        issue_id=comment.issue_id,
        user_id=comment.user_id,
        username=username,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.get("/issues/{issue_id}/comments", response_model=list[CommentOut])
async def list_comments(
    issue_id: int,
    user: CurrentUser,
    db: DBSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[CommentOut]:
    service = IssueService(db, get_user_client())
    try:
        comments, usernames, _total = await service.list_comments(issue_id, user, offset, limit)
    except IssueError as exc:
        raise _error(exc) from exc
    return [
        CommentOut(
            id=c.id,
            issue_id=c.issue_id,
            user_id=c.user_id,
            username=usernames.get(c.user_id),
            content=c.content,
            created_at=c.created_at,
        )
        for c in comments
    ]
