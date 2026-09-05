from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from project_service.models.project import Comment, Issue, PullRequest, Repository


class IssueRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, issue_id: int) -> Issue | None:
        return await self.db.get(Issue, issue_id)

    async def create(self, issue: Issue) -> Issue:
        self.db.add(issue)
        await self.db.flush()
        return issue

    async def list_for_project(
        self,
        project_id: int,
        status: str | None = None,
        assignee_id: int | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Issue], int]:
        conditions = [Issue.project_id == project_id]
        if status:
            conditions.append(Issue.status == status)
        if assignee_id is not None:
            conditions.append(Issue.assignee_id == assignee_id)
        base = select(Issue).where(*conditions)
        count_result = await self.db.execute(select(func.count()).select_from(base.subquery()))
        total = int(count_result.scalar_one())
        result = await self.db.execute(base.order_by(Issue.id.desc()).offset(offset).limit(limit))
        return list(result.scalars().all()), total


class CommentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, comment: Comment) -> Comment:
        self.db.add(comment)
        await self.db.flush()
        return comment

    async def list_for_issue(
        self, issue_id: int, offset: int = 0, limit: int = 50
    ) -> tuple[list[Comment], int]:
        base = select(Comment).where(Comment.issue_id == issue_id)
        count_result = await self.db.execute(select(func.count()).select_from(base.subquery()))
        total = int(count_result.scalar_one())
        result = await self.db.execute(base.order_by(Comment.id).offset(offset).limit(limit))
        return list(result.scalars().all()), total


class GitRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, repo_id: int) -> Repository | None:
        return await self.db.get(Repository, repo_id)

    async def get_by_external_id(self, provider: str, external_id: str) -> Repository | None:
        result = await self.db.execute(
            select(Repository).where(
                Repository.provider == provider, Repository.external_id == external_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, repo: Repository) -> Repository:
        self.db.add(repo)
        await self.db.flush()
        return repo

    async def list_for_project(self, project_id: int) -> list[Repository]:
        result = await self.db.execute(
            select(Repository).where(Repository.project_id == project_id).order_by(Repository.id)
        )
        return list(result.scalars().all())

    async def upsert_prs(self, repository_id: int, prs: list[dict]) -> int:
        """Upsert PR list by external_id. Returns count."""
        count = 0
        existing_result = await self.db.execute(
            select(PullRequest).where(PullRequest.repository_id == repository_id)
        )
        existing = {pr.external_id: pr for pr in existing_result.scalars().all()}
        for item in prs:
            pr = existing.get(item["external_id"])
            if pr:
                pr.title = item["title"]
                pr.status = item["status"]
                pr.author_login = item.get("author_login", "")
                pr.source_branch = item.get("source_branch", "")
                pr.target_branch = item.get("target_branch", "")
            else:
                self.db.add(PullRequest(repository_id=repository_id, **item))
            count += 1
        await self.db.flush()
        return count

    async def list_prs(self, repository_id: int) -> list[PullRequest]:
        result = await self.db.execute(
            select(PullRequest)
            .where(PullRequest.repository_id == repository_id)
            .order_by(PullRequest.external_id.desc())
        )
        return list(result.scalars().all())
