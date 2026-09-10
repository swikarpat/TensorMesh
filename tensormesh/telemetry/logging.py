"""Structured logging to Loki with a JSON stdout fallback."""

from __future__ import annotations

import json
import logging as std_logging
import os
import sys
import threading
import time
from typing import Any

import requests
from opentelemetry import trace


class LokiJSONLogHandler(std_logging.Handler):
    """Buffer structured records and push them to Loki when available."""

    def __init__(
        self,
        endpoint: str | None = None,
        flush_interval: float = 1.0,
        max_buffer_size: int = 20,
    ) -> None:
        super().__init__()
        self.endpoint = endpoint or os.getenv(
            "TENSORMESH_LOKI_URL", "http://localhost:3100/loki/api/v1/push"
        )
        self.flush_interval = flush_interval
        self.max_buffer_size = max_buffer_size
        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._last_flush = time.monotonic()

    def emit(self, record: std_logging.LogRecord) -> None:
        try:
            payload = self._record_payload(record)
            should_flush = False
            with self._lock:
                self._buffer.append(payload)
                should_flush = (
                    len(self._buffer) >= self.max_buffer_size
                    or time.monotonic() - self._last_flush >= self.flush_interval
                )
            if should_flush:
                self.flush()
        except Exception:
            self.handleError(record)

    def _record_payload(self, record: std_logging.LogRecord) -> dict[str, Any]:
        span_context = trace.get_current_span().get_span_context()
        trace_id = f"{span_context.trace_id:032x}" if span_context.is_valid else "0" * 32
        span_id = f"{span_context.span_id:016x}" if span_context.is_valid else "0" * 16
        payload: dict[str, Any] = {
            "timestamp": record.created,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": trace_id,
            "span_id": span_id,
        }
        for key in ("event", "agent", "task_id", "vessel_mmsi", "restricted_port"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return payload

    def _build_push_payload(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        values = [
            [str(int(record["timestamp"] * 1_000_000_000)), json.dumps(record, sort_keys=True)]
            for record in records
        ]
        return {
            "streams": [
                {
                    "stream": {"service_name": "tensormesh", "level": "info"},
                    "values": values,
                }
            ]
        }

    def flush(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            records = self._buffer
            self._buffer = []
            self._last_flush = time.monotonic()
        payload = self._build_push_payload(records)
        try:
            response = requests.post(self.endpoint, json=payload, timeout=0.5)
            response.raise_for_status()
        except Exception:
            for record in records:
                print(json.dumps(record, sort_keys=True), file=sys.stdout, flush=True)

    def close(self) -> None:
        try:
            self.flush()
        finally:
            super().close()


def configure_logging() -> std_logging.Logger:
    logger = std_logging.getLogger("tensormesh")
    logger.setLevel(std_logging.INFO)
    if not any(isinstance(handler, LokiJSONLogHandler) for handler in logger.handlers):
        logger.addHandler(LokiJSONLogHandler())
    return logger


logger = configure_logging()

__all__ = ["LokiJSONLogHandler", "configure_logging", "logger"]
