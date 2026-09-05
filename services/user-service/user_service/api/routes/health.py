from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "user-service"}


@router.get("/ready")
async def ready() -> dict:
    """就绪探针：检查 DB 连通性。"""
    from sqlalchemy import text

    from user_service.db.session import engine

    checks: dict[str, str] = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"fail: {exc}"
    ready = all(v == "ok" for v in checks.values())
    return {"ready": ready, "checks": checks}
