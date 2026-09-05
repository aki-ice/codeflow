"""Gateway：统一入口。

- JWT 校验（无需每个下游服务重复验签，这里验一次，下游可自行再验）
- Rate Limit（Redis INCR）
- 反向代理（httpx 转发，保留 path/query/body/headers）
"""

import logging
from contextlib import asynccontextmanager

import httpx
import jwt as pyjwt
from codeflow_common.metrics import instrument_app
from codeflow_common.redis import RateLimiter, create_redis
from codeflow_common.security import decode_token
from codeflow_common.tracing import setup_tracing
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from gateway_service.core.config import settings
from gateway_service.core.router_table import resolve

logger = logging.getLogger("gateway-service")

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

_client: httpx.AsyncClient | None = None
_limiter: RateLimiter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client, _limiter
    _client = httpx.AsyncClient(timeout=30)
    redis = await create_redis(settings.REDIS_URL)
    _limiter = RateLimiter(redis)

    yield
    await _client.aclose()
    if redis is not None:
        await redis.aclose()


async def proxy(request: Request) -> Response:
    assert _client is not None and _limiter is not None
    path = request.url.path
    route = resolve(path)
    if route is None:
        return JSONResponse({"detail": "route not found"}, status_code=404)

    # 限流
    identity = "anonymous"
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        identity = auth_header[7:32]
    client_ip = request.client.host if request.client else "unknown"
    if not await _limiter.check(
        f"gw:{path}:{identity or client_ip}", settings.RATE_LIMIT_PER_MINUTE
    ):
        return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)

    # JWT 校验
    if route.requires_auth:
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Not authenticated"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            decode_token(auth_header[7:], settings.SECRET_KEY, expected_type="access")
        except pyjwt.ExpiredSignatureError:
            return JSONResponse({"detail": "token expired"}, status_code=401)
        except pyjwt.InvalidTokenError:
            return JSONResponse({"detail": "Could not validate credentials"}, status_code=401)

    # 转发
    url = f"{route.upstream}{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
    body = await request.body()
    try:
        resp = await _client.request(
            request.method,
            url,
            headers=headers,
            content=body,
            params=request.query_params,
        )
    except httpx.ConnectError:
        return JSONResponse({"detail": f"upstream unavailable: {route.upstream}"}, status_code=502)

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={
            k: v
            for k, v in resp.headers.items()
            if k.lower() not in HOP_BY_HOP and k.lower() != "content-encoding"
        },
    )


async def catch_all(request: Request) -> Response:
    return await proxy(request)


def create_app() -> FastAPI:
    app = FastAPI(title="CodeFlow Gateway", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "service": "gateway-service"}

    # 先注册 /metrics，再注册兜底路由（否则 catch-all 会抢先匹配）
    instrument_app(app, "gateway-service")
    if settings.OTEL_ENABLED:
        setup_tracing(app, "gateway-service", settings.OTEL_ENDPOINT)

    app.add_api_route("/{path:path}", catch_all, methods=["GET", "POST", "PATCH", "PUT", "DELETE"])

    return app


app = create_app()
