from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from ci_service.api.deps import CurrentUser, DBSession
from ci_service.events.publishers import publish_finished
from ci_service.models.pipeline import Build, Pipeline
from ci_service.schemas.pipeline import PipelineDetail, PipelineOut, PipelinePage, PipelineTrigger
from ci_service.services import runner

router = APIRouter(tags=["pipelines"])


def _out(p: Pipeline) -> PipelineOut:
    return PipelineOut(
        id=p.id,
        project_id=p.project_id,
        repository=p.repository,
        repository_id=p.repository_id,
        commit_sha=p.commit_sha,
        branch=p.branch,
        status=p.status,
        trigger_type=p.trigger_type,
        started_at=p.started_at,
        finished_at=p.finished_at,
        created_at=p.created_at,
    )


@router.post("/pipelines", response_model=PipelineOut, status_code=status.HTTP_201_CREATED)
async def trigger_pipeline(body: PipelineTrigger, user: CurrentUser, db: DBSession) -> PipelineOut:
    """手动触发 Pipeline（通过网关携带 JWT）。"""
    pipeline = Pipeline(
        project_id=body.project_id,
        repository_id=body.repository_id,
        repository=body.repository,
        commit_sha=body.commit_sha,
        branch=body.branch,
        status="pending",
        trigger_type="manual",
    )
    db.add(pipeline)
    await db.flush()
    build = Build(pipeline_id=pipeline.id, status="pending", logs="")
    db.add(build)
    await db.flush()
    await db.commit()
    runner.enqueue(pipeline.id)
    return _out(pipeline)


@router.get("/pipelines", response_model=PipelinePage)
async def list_pipelines(
    user: CurrentUser,
    db: DBSession,
    project_id: int | None = None,
    offset: int = 0,
    limit: int = 20,
) -> PipelinePage:
    base = select(Pipeline)
    if project_id is not None:
        base = base.where(Pipeline.project_id == project_id)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    result = await db.execute(base.order_by(Pipeline.id.desc()).offset(offset).limit(limit))
    items = result.scalars().all()
    return PipelinePage(total=total, items=[_out(p) for p in items])


@router.get("/pipelines/{pipeline_id}", response_model=PipelineDetail)
async def get_pipeline(pipeline_id: int, user: CurrentUser, db: DBSession) -> PipelineDetail:
    pipeline = await db.get(Pipeline, pipeline_id)
    if pipeline is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "pipeline not found")
    result = await db.execute(
        select(Build).where(Build.pipeline_id == pipeline_id).order_by(Build.id.desc()).limit(1)
    )
    build = result.scalar_one_or_none()
    return PipelineDetail(
        **_out(pipeline).model_dump(),
        build_id=build.id if build else None,
        build_status=build.status if build else None,
        logs=build.logs if build else "",
    )


@router.get("/pipelines/{pipeline_id}/logs")
async def get_logs(pipeline_id: int, user: CurrentUser, db: DBSession) -> dict:
    result = await db.execute(
        select(Build).where(Build.pipeline_id == pipeline_id).order_by(Build.id.desc()).limit(1)
    )
    build = result.scalar_one_or_none()
    if build is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "build not found")
    return {"pipeline_id": pipeline_id, "build_id": build.id, "logs": build.logs}


@router.post("/pipelines/{pipeline_id}/cancel")
async def cancel_pipeline(pipeline_id: int, user: CurrentUser, db: DBSession) -> dict:
    pipeline = await db.get(Pipeline, pipeline_id)
    if pipeline is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "pipeline not found")
    if pipeline.status in ("success", "failed", "canceled"):
        return {"id": pipeline.id, "status": pipeline.status, "canceled": False}
    pipeline.status = "canceled"
    pipeline.finished_at = datetime.now(UTC)
    result = await db.execute(
        select(Build).where(Build.pipeline_id == pipeline_id).order_by(Build.id.desc()).limit(1)
    )
    build = result.scalar_one_or_none()
    if build is not None and build.status in ("pending", "running"):
        build.status = "canceled"
        build.finished_at = pipeline.finished_at
    await publish_finished(db, pipeline)
    await db.commit()
    return {"id": pipeline.id, "status": pipeline.status, "canceled": True}
