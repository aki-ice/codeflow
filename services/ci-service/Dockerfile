FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /build
COPY pyproject.toml uv.lock ./
COPY libs ./libs
COPY services/ci-service ./services/ci-service
RUN uv sync --frozen --no-dev --project services/ci-service

FROM python:3.12-slim AS runtime
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY --from=builder /build/services/ci-service/.venv /app/.venv
COPY services/ci-service/ci_service ./ci_service
COPY services/ci-service/alembic ./alembic
COPY services/ci-service/alembic.ini ./
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["sh", "-c", "alembic upgrade head && uvicorn ci_service.main:app --host 0.0.0.0 --port 8000"]
