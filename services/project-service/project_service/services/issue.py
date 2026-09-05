import logging

from codeflow_common.outbox import emit
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from project_service.models.project import Comment, Issue, OutboxEvent
from project_service.repositories.issue import CommentRepository, IssueRepository
from project_service.services.project import ProjectError, ProjectService

logger = logging.getLogger("project-service.issue")


async def allocate_issue_number(db: AsyncSession, project_id: int) -> int:
    """项目内自增编号。Redis 不可用时退化为 max(number)+1。"""
    from project_service.api.deps import get_redis_client

    client = await get_redis_client()
    if client is not None:
        try:
            return int(await client.incr(f"project:{project_id}:issue_seq"))
        except Exception as exc:
            logger.warning("issue seq incr failed, fallback to db: %s", exc)
    result = await db.execute(select(func.max(Issue.number)).where(Issue.project_id == project_id))
    current = result.scalar_one_or_none()
    return int(current or 0) + 1


class IssueError(Exception):
    pass


class IssueService:
    def __init__(self, db: AsyncSession, user_client=None) -> None:
        self.issues = IssueRepository(db)
        self.comments = CommentRepository(db)
        self.projects = ProjectService(db, user_client)
        self.user_client = user_client
        self.db = db

    async def create(
        self,
        user_id: int,
        project_id: int,
        title: str,
        description: str,
        type: str,
        priority: str,
        assignee_id: int | None,
    ) -> Issue:
        await self.projects.require_role(project_id, user_id, "developer")
        if assignee_id is not None:
            username = await self.user_client.get_username(assignee_id)
            if username is None:
                raise IssueError("assignee does not exist")
        number = await allocate_issue_number(self.db, project_id)
        issue = Issue(
            project_id=project_id,
            number=number,
            title=title,
            description=description,
            type=type,
            priority=priority,
            assignee_id=assignee_id,
            creator_id=user_id,
        )
        issue = await self.issues.create(issue)
        # Event Contract：事件内携带 watchers（除创建者外的成员），消费端无需反查
        watcher_ids = await self.projects.projects.list_member_ids(project_id)
        await emit(
            self.db,
            OutboxEvent,
            "issue.created",
            issue_id=issue.id,
            number=number,
            title=title,
            project_id=project_id,
            creator_id=user_id,
            watchers=[uid for uid in watcher_ids if uid != user_id],
        )
        return issue

    async def get_for_user(self, issue_id: int, user_id: int) -> Issue:
        issue = await self.issues.get(issue_id)
        if not issue:
            raise IssueError("issue not found")
        try:
            await self.projects.require_role(issue.project_id, user_id, "viewer")
        except ProjectError as exc:
            raise IssueError(str(exc)) from exc
        return issue

    async def update(self, issue_id: int, user_id: int, data: dict) -> Issue:
        issue = await self.get_for_user(issue_id, user_id)
        await self.projects.require_role(issue.project_id, user_id, "developer")
        for key, value in data.items():
            if value is not None:
                setattr(issue, key, value)
        await emit(
            self.db, OutboxEvent, "issue.updated", issue_id=issue.id, project_id=issue.project_id
        )
        return issue

    async def delete(self, issue_id: int, user_id: int) -> None:
        issue = await self.get_for_user(issue_id, user_id)
        await self.projects.require_role(issue.project_id, user_id, "admin")
        await self.db.delete(issue)

    async def list_for_project(
        self,
        user_id: int,
        project_id: int,
        status: str | None,
        assignee_id: int | None,
        offset: int,
        limit: int,
    ):
        await self.projects.require_role(project_id, user_id, "viewer")
        return await self.issues.list_for_project(
            project_id, status=status, assignee_id=assignee_id, offset=offset, limit=limit
        )

    async def add_comment(self, issue_id: int, user_id: int, content: str) -> Comment:
        issue = await self.get_for_user(issue_id, user_id)
        await self.projects.require_role(issue.project_id, user_id, "developer")
        comment = Comment(issue_id=issue_id, user_id=user_id, content=content)
        return await self.comments.create(comment)

    async def list_comments(self, issue_id: int, user_id: int, offset: int, limit: int):
        issue = await self.get_for_user(issue_id, user_id)
        comments, total = await self.comments.list_for_issue(issue.id, offset=offset, limit=limit)
        usernames = await self.user_client.get_usernames([c.user_id for c in comments])
        return comments, usernames, total
