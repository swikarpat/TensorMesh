"""OpenTelemetry metrics and Prometheus exposition for TensorMesh."""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Mapping

try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.metrics import MeterProvider

    _OTEL_PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised in minimal environments
    _OTEL_PROMETHEUS_AVAILABLE = False


class _FallbackInstrument:
    def __init__(self, name: str, kind: str):
        self.name = name
        self.kind = kind
        self._values: defaultdict[tuple[tuple[str, str], ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def _update(self, value: float, attributes: Mapping[str, object] | None) -> None:
        labels = tuple(sorted((str(key), str(item)) for key, item in (attributes or {}).items()))
        with self._lock:
            self._values[labels] += value

    def add(self, amount: float, attributes: Mapping[str, object] | None = None) -> None:
        self._update(float(amount), attributes)

    def record(self, amount: float, attributes: Mapping[str, object] | None = None) -> None:
        self._update(float(amount), attributes)

    def snapshot(self) -> dict[tuple[tuple[str, str], ...], float]:
        with self._lock:
            return dict(self._values)


if _OTEL_PROMETHEUS_AVAILABLE:
    _reader = PrometheusMetricReader()
    _provider = MeterProvider(metric_readers=[_reader])
    otel_metrics.set_meter_provider(_provider)
    meter = otel_metrics.get_meter("tensormesh")
    request_duration_seconds = meter.create_histogram(
        "tensormesh_request_duration_seconds", unit="s", description="TensorMesh API request latency"
    )
    dfars_violations_total = meter.create_counter(
        "tensormesh_dfars_violations_total", unit="{violation}", description="DFARS compliance violations"
    )
    active_agents = meter.create_up_down_counter(
        "tensormesh_active_agents", unit="{agent}", description="Currently active reasoning agents"
    )
    simd_inversion_duration_us = meter.create_histogram(
        "tensormesh_simd_inversion_duration_us", unit="us", description="Native seismic inversion latency"
    )
else:
    request_duration_seconds = _FallbackInstrument("tensormesh_request_duration_seconds", "histogram")
    dfars_violations_total = _FallbackInstrument("tensormesh_dfars_violations_total", "counter")
    active_agents = _FallbackInstrument("tensormesh_active_agents", "up_down_counter")
    simd_inversion_duration_us = _FallbackInstrument("tensormesh_simd_inversion_duration_us", "histogram")


def record_request_duration(duration_seconds: float, method: str, path: str, status: int) -> None:
    request_duration_seconds.record(
        duration_seconds,
        {"method": method, "path": path, "status": str(status)},
    )


def record_dfars_violation(vessel_mmsi: str = "unknown", restricted_port: str = "unknown") -> None:
    dfars_violations_total.add(
        1,
        {"vessel_mmsi": vessel_mmsi or "unknown", "restricted_port": restricted_port or "unknown"},
    )


def change_active_agents(amount: int, agent: str = "unknown") -> None:
    active_agents.add(amount, {"agent": agent})


def record_simd_inversion_duration(duration_microseconds: float, kernel: str = "acoustic_impedance") -> None:
    simd_inversion_duration_us.record(duration_microseconds, {"kernel": kernel})


def get_metrics_payload() -> str:
    """Return Prometheus text exposition suitable for a FastAPI response."""
    if _OTEL_PROMETHEUS_AVAILABLE:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        del CONTENT_TYPE_LATEST
        return generate_latest().decode("utf-8")

    lines: list[str] = []
    for instrument in (
        request_duration_seconds,
        dfars_violations_total,
        active_agents,
        simd_inversion_duration_us,
    ):
        lines.append(f"# HELP {instrument.name} TensorMesh metric")
        metric_type = {
            "counter": "counter",
            "histogram": "histogram",
            "up_down_counter": "gauge",
        }[instrument.kind]
        lines.append(f"# TYPE {instrument.name} {metric_type}")
        for labels, value in instrument.snapshot().items():
            suffix = "" if not labels else "{" + ",".join(f'{key}="{value}"' for key, value in labels) + "}"
            lines.append(f"{instrument.name}{suffix} {value}")
    return "\n".join(lines) + "\n"


__all__ = [
    "active_agents",
    "change_active_agents",
    "dfars_violations_total",
    "get_metrics_payload",
    "record_dfars_violation",
    "record_request_duration",
    "record_simd_inversion_duration",
    "request_duration_seconds",
    "simd_inversion_duration_us",
]
