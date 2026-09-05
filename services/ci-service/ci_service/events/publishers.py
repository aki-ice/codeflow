"""pipeline.finished 事件发布（执行完成后由 main 调用）。"""

import logging

from codeflow_common.outbox import emit
from sqlalchemy.ext.asyncio import AsyncSession

from ci_service.models.pipeline import OutboxEvent, Pipeline

logger = logging.getLogger("ci-service.events")


async def publish_finished(db: AsyncSession, pipeline: Pipeline, build_logs_tail: str = "") -> None:
    await emit(
        db,
        OutboxEvent,
        "pipeline.finished",
        pipeline_id=pipeline.id,
        project_id=pipeline.project_id,
        repository=pipeline.repository,
        branch=pipeline.branch,
        commit_sha=pipeline.commit_sha,
        status=pipeline.status,
        logs_tail=build_logs_tail[-500:],
    )
