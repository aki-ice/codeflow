from codeflow_common.outbox import emit
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from project_service.models.project import OutboxEvent, Project, ProjectMember
from project_service.repositories.project import ProjectRepository
from project_service.services.audit import write_audit


class ProjectError(Exception):
    pass


ROLE_ORDER = {"viewer": 0, "developer": 1, "admin": 2, "owner": 3}


class ProjectService:
    def __init__(self, db: AsyncSession, user_client=None) -> None:
        self.projects = ProjectRepository(db)
        self.db = db
        self.user_client = user_client

    async def create(self, user_id: int, name: str, description: str, visibility: str) -> Project:
        project = Project(
            name=name, description=description, visibility=visibility, created_by=user_id
        )
        project = await self.projects.create(project)
        await self.projects.add_member(
            ProjectMember(project_id=project.id, user_id=user_id, role="owner")
        )
        await emit(
            self.db,
            OutboxEvent,
            "project.created",
            project_id=project.id,
            name=name,
            creator_id=user_id,
        )

        await write_audit(
            self.db, user_id, "project.created", "project", project.id, project.id, {"name": name}
        )
        return project

    async def get(self, project_id: int) -> Project:
        project = await self.projects.get(project_id)
        if not project:
            raise ProjectError("project not found")
        return project

    async def list_for_user(self, user_id: int, offset: int, limit: int):
        return await self.projects.list_for_user(user_id, offset=offset, limit=limit)

    async def update(self, project_id: int, data: dict, user_id: int | None = None) -> Project:
        project = await self.get(project_id)
        for key, value in data.items():
            if value is not None:
                setattr(project, key, value)
        await emit(
            self.db,
            OutboxEvent,
            "project.updated",
            project_id=project_id,
            changes={k: v for k, v in data.items() if v is not None},
        )
        await write_audit(
            self.db,
            user_id,
            "project.updated",
            "project",
            project_id,
            project_id,
            {k: v for k, v in data.items() if v is not None},
        )
        return project

    async def delete(self, project_id: int, user_id: int | None = None) -> None:
        project = await self.get(project_id)
        await self.db.delete(project)
        await emit(self.db, OutboxEvent, "project.deleted", project_id=project_id)
        await write_audit(
            self.db,
            user_id,
            "project.deleted",
            "project",
            project_id,
            project_id,
            {"name": project.name},
        )

    async def require_role(self, project_id: int, user_id: int, min_role: str) -> ProjectMember:
        member = await self.projects.get_member(project_id, user_id)
        if not member:
            raise ProjectError("you are not a member of this project")
        if ROLE_ORDER[member.role] < ROLE_ORDER[min_role]:
            raise ProjectError(f"requires {min_role} role or higher")
        return member

    async def add_member(
        self, project_id: int, username: str, role: str, operator_id: int | None = None
    ) -> ProjectMember:
        if self.user_client is None:
            raise ProjectError("user service unavailable")
        user_id = await self.user_client.get_user_id(username)
        if user_id is None:
            raise ProjectError("user not found")
        existing = await self.projects.get_member(project_id, user_id)
        if existing:
            raise ProjectError("user is already a member")
        member = await self.projects.add_member(
            ProjectMember(project_id=project_id, user_id=user_id, role=role)
        )
        await emit(
            self.db,
            OutboxEvent,
            "project.member_added",
            project_id=project_id,
            user_id=user_id,
            role=role,
        )
        await write_audit(
            self.db,
            operator_id,
            "project.member_added",
            "member",
            user_id,
            project_id,
            {"username": username, "role": role},
        )
        return member

    async def update_member_role(self, project_id: int, user_id: int, role: str) -> ProjectMember:
        member = await self.projects.get_member(project_id, user_id)
        if not member:
            raise ProjectError("member not found")
        if member.role == "owner":
            raise ProjectError("cannot change owner role")
        member.role = role
        return member

    async def remove_member(self, project_id: int, user_id: int) -> None:
        member = await self.projects.get_member(project_id, user_id)
        if not member:
            raise ProjectError("member not found")
        if member.role == "owner":
            raise ProjectError("cannot remove owner")
        await self.db.delete(member)

    async def list_members(self, project_id: int) -> list[tuple[ProjectMember, str | None]]:
        members = await self.projects.list_members(project_id)
        usernames = await self.user_client.get_usernames([m.user_id for m in members])
        return [(m, usernames.get(m.user_id)) for m in members]

    async def member_count(self, project_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == project_id)
        )
        return int(result.scalar_one())
