"""Pipeline 异步执行器（CI Worker）。

流程：git.push 事件 → Pipeline(pending) → 队列执行 → running → 步骤
（checkout/install/test/lint）→ success/failed → pipeline.finished 事件。

- CI_SIMULATE=true：模拟执行器，不依赖真实仓库与 Docker（演示/开发）
- CI_SIMULATE=false：真实执行（git clone + 命令），需要本机工具链
- 每步开始前检查 DB 中的最新状态，被 cancel 的 pipeline 立即终止
- 日志实时追加到 builds.logs
"""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from ci_service.core.config import settings
from ci_service.db.session import async_session_factory
from ci_service.models.pipeline import Build, Pipeline

logger = logging.getLogger("ci-service.runner")

_queue: asyncio.Queue[int] = asyncio.Queue()
_worker_tasks: list[asyncio.Task] = []


def enqueue(pipeline_id: int) -> None:
    _queue.put_nowait(pipeline_id)


async def _now():
    return datetime.now(UTC)


async def _load(pipeline_id: int) -> tuple[Pipeline, Build] | None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Pipeline, Build)
            .join(Build, Build.pipeline_id == Pipeline.id)
            .where(Pipeline.id == pipeline_id)
            .order_by(Build.id.desc())
            .limit(1)
        )
        row = result.first()
        return (row[0], row[1]) if row else None


async def _update(
    pipeline_id: int, build_id: int, *, pipeline_fields: dict, build_fields: dict
) -> str:
    """更新状态并返回最新 pipeline status（用于取消检测）。"""
    async with async_session_factory() as session:
        pipeline = await session.get(Pipeline, pipeline_id)
        build = await session.get(Build, build_id)
        assert pipeline and build
        for k, v in pipeline_fields.items():
            setattr(pipeline, k, v)
        for k, v in build_fields.items():
            setattr(build, k, v)
        await session.commit()
        return pipeline.status


async def _append_log(build_id: int, line: str) -> None:
    async with async_session_factory() as session:
        build = await session.get(Build, build_id)
        if build is not None:
            build.logs = (build.logs or "") + line + "\n"
            await session.commit()


async def _run_step(name: str, detail: str) -> tuple[bool, str]:
    """执行单个步骤，返回 (成功?, 日志行)。模拟模式直接成功。"""
    if settings.CI_SIMULATE:
        await asyncio.sleep(0.3)  # 模拟耗时
        return True, f"[{name}] ok (simulated): {detail}"
    # 真实模式示例：checkout 阶段执行 git clone
    if name == "checkout" and detail.startswith("http"):
        process = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--depth",
            "1",
            detail,
            "repo",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await process.communicate()
        return process.returncode == 0, f"[{name}] exit={process.returncode}\n{out.decode()[:2000]}"
    return True, f"[{name}] ok: {detail}"


STEPS = [
    ("checkout", lambda p: p.repository or f"project-{p.project_id}@{p.branch}"),
    ("install", lambda p: f"install dependencies for {p.branch}"),
    ("test", lambda p: f"run tests @ {p.commit_sha[:8] or 'HEAD'}"),
    ("lint", lambda p: "ruff + mypy"),
    ("build", lambda p: f"build artifact for {p.branch}"),
]


async def execute_pipeline(pipeline_id: int) -> None:
    loaded = await _load(pipeline_id)
    if loaded is None:
        logger.error("pipeline %s not found", pipeline_id)
        return
    pipeline, build = loaded

    status = await _update(
        pipeline_id,
        build.id,
        pipeline_fields={"status": "running", "started_at": await _now()},
        build_fields={"status": "running", "started_at": await _now()},
    )
    if status == "canceled":
        return

    ok = True
    try:
        for name, detail_fn in STEPS:
            # 取消检测
            async with async_session_factory() as session:
                p = await session.get(Pipeline, pipeline_id)
                if p is None or p.status == "canceled":
                    logger.info("pipeline %s canceled, stop", pipeline_id)
                    return
                await session.close()

            success, log_line = await _run_step(name, detail_fn(pipeline))
            await _append_log(build.id, log_line)
            if not success:
                ok = False
                await _append_log(build.id, f"[{name}] FAILED")
                break
    except Exception as exc:
        ok = False
        await _append_log(build.id, f"[error] {exc}")
        logger.exception("pipeline %s crashed", pipeline_id)

    final_status = "success" if ok else "failed"
    await _update(
        pipeline_id,
        build.id,
        pipeline_fields={"status": final_status, "finished_at": await _now()},
        build_fields={"status": final_status, "finished_at": await _now()},
    )
    logger.info("pipeline %s finished: %s", pipeline_id, final_status)


async def _worker(n: int, stop: asyncio.Event, on_finished) -> None:
    logger.info("ci worker #%s started", n)
    while not stop.is_set():
        try:
            pipeline_id = await asyncio.wait_for(_queue.get(), timeout=1.0)
        except TimeoutError:
            continue
        await execute_pipeline(pipeline_id)
        await on_finished(pipeline_id)
    logger.info("ci worker #%s stopped", n)


def start_workers(stop: asyncio.Event, on_finished, concurrency: int | None = None) -> None:
    count = concurrency or settings.CI_MAX_CONCURRENCY
    for i in range(count):
        _worker_tasks.append(asyncio.create_task(_worker(i, stop, on_finished)))


async def stop_workers() -> None:
    for task in _worker_tasks:
        task.cancel()
    await asyncio.gather(*_worker_tasks, return_exceptions=True)
    _worker_tasks.clear()
