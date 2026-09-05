from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SERVICE_NAME: str = "ai-service"
    ENV: str = "dev"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    SECRET_KEY: str = "change-me-to-a-random-secret-at-least-32-bytes-long"
    DATABASE_URL: str = "postgresql+asyncpg://codeflow:codeflow@localhost:5432/codeflow_ai"
    DB_ECHO: bool = False

    REDIS_URL: str = "redis://localhost:6379/0"

    OTEL_ENABLED: bool = False
    OTEL_ENDPOINT: str = "http://localhost:4318/v1/traces"

    # ===== LLM（手动配置；留空则使用 Mock 降级） =====
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    # Mock Embedding 维度（pgvector 列宽）
    EMBEDDING_DIM: int = 256
    # RAG 检索条数 / 分块大小
    RAG_TOP_K: int = 3
    RAG_CHUNK_SIZE: int = 500


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
