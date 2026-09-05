from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SERVICE_NAME: str = "ci-service"
    ENV: str = "dev"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    SECRET_KEY: str = "change-me-to-a-random-secret-at-least-32-bytes-long"

    DATABASE_URL: str = "postgresql+asyncpg://codeflow:codeflow@localhost:5432/codeflow_ci"
    DB_ECHO: bool = False

    REDIS_URL: str = "redis://localhost:6379/0"

    KAFKA_ENABLED: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    OTEL_ENABLED: bool = False
    OTEL_ENDPOINT: str = "http://localhost:4318/v1/traces"
    OUTBOX_POLL_INTERVAL_SECONDS: float = 1.0

    CONSUMER_GROUP_ID: str = "codeflow-ci"
    # 同时执行的 Pipeline 上限
    CI_MAX_CONCURRENCY: int = 2
    # true=模拟执行器（无需真实仓库/docker）；false=调用本地 git/docker
    CI_SIMULATE: bool = True
    # 仓库本地缓存目录
    CI_WORKSPACE_DIR: str = "./.ci-workspace"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
