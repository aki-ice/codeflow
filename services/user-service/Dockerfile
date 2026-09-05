FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /build
COPY pyproject.toml uv.lock ./
COPY libs ./libs
COPY services/user-service ./services/user-service
RUN uv sync --frozen --no-dev --project services/user-service

FROM python:3.12-slim AS runtime
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY --from=builder /build/services/user-service/.venv /app/.venv
COPY services/user-service/user_service ./user_service
COPY services/user-service/alembic ./alembic
COPY services/user-service/alembic.ini ./
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["sh", "-c", "alembic upgrade head && uvicorn user_service.main:app --host 0.0.0.0 --port 8000"]
