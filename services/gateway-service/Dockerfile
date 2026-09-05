FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /build
COPY pyproject.toml uv.lock ./
COPY libs ./libs
COPY services/gateway-service ./services/gateway-service
RUN uv sync --frozen --no-dev --project services/gateway-service

FROM python:3.12-slim AS runtime
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY --from=builder /build/services/gateway-service/.venv /app/.venv
COPY services/gateway-service/gateway_service ./gateway_service
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "gateway_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
