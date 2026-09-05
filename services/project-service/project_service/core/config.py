from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SERVICE_NAME: str = "project-service"
    ENV: str = "dev"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    SECRET_KEY: str = "change-me-to-a-random-secret-at-least-32-bytes-long"

    DATABASE_URL: str = "postgresql+asyncpg://codeflow:codeflow@localhost:5432/codeflow_projects"
    DB_ECHO: bool = False

    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_PER_MINUTE: int = 120
    CACHE_TTL_SECONDS: int = 60

    USER_SERVICE_URL: str = "http://localhost:8001"
    INTERNAL_TOKEN: str = "dev-internal-token"

    KAFKA_ENABLED: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    OTEL_ENABLED: bool = False
    OTEL_ENDPOINT: str = "http://localhost:4318/v1/traces"
    OUTBOX_POLL_INTERVAL_SECONDS: float = 1.0

    # GitHub 集成（手动配置）
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_TOKEN: str = ""
    GITHUB_API_URL: str = "https://api.github.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
