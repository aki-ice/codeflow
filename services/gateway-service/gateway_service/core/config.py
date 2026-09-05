from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SERVICE_NAME: str = "gateway-service"
    ENV: str = "dev"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    SECRET_KEY: str = "change-me-to-a-random-secret-at-least-32-bytes-long"

    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_PER_MINUTE: int = 120

    OTEL_ENABLED: bool = False
    OTEL_ENDPOINT: str = "http://localhost:4318/v1/traces"

    USER_SERVICE_URL: str = "http://localhost:8001"
    PROJECT_SERVICE_URL: str = "http://localhost:8002"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8003"
    CI_SERVICE_URL: str = "http://localhost:8004"
    AI_SERVICE_URL: str = "http://localhost:8005"

    # 无需 JWT 即可访问的路径前缀
    PUBLIC_PATHS: list[str] = [
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/webhooks/github",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
