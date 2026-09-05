from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from project_service.models.project import Project, ProjectMember


class ProjectRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, project_id: int) -> Project | None:
        return await self.db.get(Project, project_id)

    async def create(self, project: Project) -> Project:
        self.db.add(project)
        await self.db.flush()
        return project

    async def list_for_user(
        self, user_id: int, offset: int = 0, limit: int = 20
    ) -> tuple[list[Project], int]:
        base = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user_id)
        )
        count_result = await self.db.execute(select(func.count()).select_from(base.subquery()))
        total = int(count_result.scalar_one())
        result = await self.db.execute(base.order_by(Project.id.desc()).offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def add_member(self, member: ProjectMember) -> ProjectMember:
        self.db.add(member)
        await self.db.flush()
        return member

    async def get_member(self, project_id: int, user_id: int) -> ProjectMember | None:
        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_members(self, project_id: int) -> list[ProjectMember]:
        result = await self.db.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.id)
        )
        return list(result.scalars().all())

    async def list_member_ids(self, project_id: int) -> list[int]:
        result = await self.db.execute(
            select(ProjectMember.user_id).where(ProjectMember.project_id == project_id)
        )
        return [int(uid) for uid in result.scalars().all()]
