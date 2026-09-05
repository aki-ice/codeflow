"""Prometheus 指标：每个服务暴露 /metrics。

http_requests_total / http_request_duration_seconds（P50/P95/P99 直方图）等。
"""

import logging

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger("codeflow.metrics")


def instrument_app(app: FastAPI, service_name: str) -> None:
    try:
        instrumentator = Instrumentator(excluded_handlers=["/metrics", "/health"])
        instrumentator.instrument(
            app, metric_namespace="codeflow", metric_subsystem=service_name.replace("-", "_")
        )
        instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)
        logger.info("metrics instrumented: %s", service_name)
    except Exception as exc:  # pragma: no cover
        logger.warning("metrics instrumentation failed: %s", exc)
