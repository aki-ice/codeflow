from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SERVICE_NAME: str = "notification-service"
    ENV: str = "dev"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    SECRET_KEY: str = "change-me-to-a-random-secret-at-least-32-bytes-long"

    DATABASE_URL: str = (
        "postgresql+asyncpg://codeflow:codeflow@localhost:5432/codeflow_notifications"
    )
    DB_ECHO: bool = False

    REDIS_URL: str = "redis://localhost:6379/0"

    KAFKA_ENABLED: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    OTEL_ENABLED: bool = False
    OTEL_ENDPOINT: str = "http://localhost:4318/v1/traces"

    CONSUMER_GROUP_ID: str = "codeflow-notification"
    PROCESS_MAX_RETRIES: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
