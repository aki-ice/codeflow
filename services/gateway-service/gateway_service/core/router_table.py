"""网关路由表：路径前缀 -> 上游服务。"""

from dataclasses import dataclass

from gateway_service.core.config import settings


@dataclass
class Route:
    prefix: str
    upstream: str
    requires_auth: bool


def build_routes() -> list[Route]:
    return [
        Route(f"{settings.API_V1_PREFIX}/auth", settings.USER_SERVICE_URL, requires_auth=False),
        Route(f"{settings.API_V1_PREFIX}/users", settings.USER_SERVICE_URL, requires_auth=True),
        Route(f"{settings.API_V1_PREFIX}/internal", settings.USER_SERVICE_URL, requires_auth=False),
        Route(
            f"{settings.API_V1_PREFIX}/projects", settings.PROJECT_SERVICE_URL, requires_auth=True
        ),
        Route(f"{settings.API_V1_PREFIX}/issues", settings.PROJECT_SERVICE_URL, requires_auth=True),
        Route(
            f"{settings.API_V1_PREFIX}/webhooks", settings.PROJECT_SERVICE_URL, requires_auth=False
        ),
        Route(
            f"{settings.API_V1_PREFIX}/notifications",
            settings.NOTIFICATION_SERVICE_URL,
            requires_auth=True,
        ),
        Route(f"{settings.API_V1_PREFIX}/pipelines", settings.CI_SERVICE_URL, requires_auth=True),
        Route(f"{settings.API_V1_PREFIX}/ai", settings.AI_SERVICE_URL, requires_auth=True),
    ]


def resolve(path: str) -> Route | None:
    for route in build_routes():
        if path.startswith(route.prefix):
            return route
    return None
