"""OpenTelemetry 分布式追踪。

- FastAPI 入站请求自动建 span
- httpx 出站调用（网关代理/服务间调用）自动注入 traceparent
- OTLP/HTTP 导出到 Jaeger / OTel Collector

OTEL_ENABLED=false 时完全零开销。
"""

import logging

from fastapi import FastAPI

logger = logging.getLogger("codeflow.tracing")


def setup_tracing(app: FastAPI, service_name: str, otlp_endpoint: str) -> bool:
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        HTTPXClientInstrumentor().instrument(tracer_provider=provider)
        logger.info("tracing enabled: %s -> %s", service_name, otlp_endpoint)
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("tracing setup failed: %s", exc)
        return False
