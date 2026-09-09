from __future__ import annotations

import os
import secrets
import socket
from contextlib import contextmanager
from typing import Any, Iterator
from urllib.parse import urlparse

from opentelemetry import propagate, trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, TraceState

try:  # Optional runtime dependency: the API remains usable without a collector SDK.
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    _SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised in minimal installations
    _SDK_AVAILABLE = False


class _FallbackSpan(NonRecordingSpan):
    def __init__(self, context: SpanContext, parent: SpanContext | None, name: str):
        super().__init__(context)
        self.name = name
        self.parent = parent
        self.attributes: dict[str, Any] = {}
        self.ended = False

    def set_attribute(self, key: str, value: Any) -> "_FallbackSpan":
        self.attributes[key] = value
        return self

    def end(self, *args: Any, **kwargs: Any) -> None:
        self.ended = True


def _collector_is_reachable(endpoint: str) -> bool:
    parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
    host = parsed.hostname or "localhost"
    port = parsed.port or 4317
    try:
        with socket.create_connection((host, port), timeout=0.05):
            return True
    except OSError:
        return False


class OpenTelemetryTracer:
    """Small TensorMesh tracing adapter with W3C propagation and OTLP export."""

    def __init__(self, service_name: str = "tensormesh", endpoint: str | None = None):
        self.service_name = service_name
        self.endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        self._fallback_spans: list[_FallbackSpan] = []
        self._provider = None
        if _SDK_AVAILABLE:
            resource = Resource.create({"service.name": service_name})
            self._provider = TracerProvider(resource=resource)
            exporter_mode = os.getenv("TENSORMESH_OTEL_EXPORTER", "otlp").casefold()
            if exporter_mode == "console":
                self._provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
            elif exporter_mode == "none":
                pass
            elif _collector_is_reachable(self.endpoint):
                try:
                    exporter = OTLPSpanExporter(endpoint=self.endpoint, insecure=True)
                    self._provider.add_span_processor(BatchSpanProcessor(exporter))
                except Exception:
                    self._provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
            self._tracer = self._provider.get_tracer(service_name)
        else:
            self._tracer = None

    def extract_context(self, carrier: dict[str, str]):
        """Extract a W3C traceparent context from HTTP or MCP metadata."""
        return propagate.extract(carrier)

    def inject_context(self, carrier: dict[str, str]) -> dict[str, str]:
        """Inject the current W3C trace context into a mutable carrier."""
        propagate.inject(carrier)
        return carrier

    @contextmanager
    def span(self, name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
        if self._tracer is not None:
            with self._tracer.start_as_current_span(name) as current_span:
                for key, value in (attributes or {}).items():
                    if value is not None:
                        current_span.set_attribute(key, value)
                yield current_span
            return

        parent = trace.get_current_span().get_span_context()
        parent_context = parent if parent.is_valid else None
        context = SpanContext(
            trace_id=parent.trace_id if parent_context else secrets.randbits(128),
            span_id=secrets.randbits(64),
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state=TraceState(),
        )
        current_span = _FallbackSpan(context, parent_context, name)
        for key, value in (attributes or {}).items():
            if value is not None:
                current_span.set_attribute(key, value)
        token = trace.context_api.attach(trace.set_span_in_context(current_span))
        self._fallback_spans.append(current_span)
        try:
            yield current_span
        finally:
            current_span.end()
            trace.context_api.detach(token)

    @property
    def finished_spans(self) -> list[Any]:
        return list(self._fallback_spans)


_default_tracer = OpenTelemetryTracer()


def get_otel_tracer() -> OpenTelemetryTracer:
    return _default_tracer