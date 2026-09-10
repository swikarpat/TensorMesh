import json
import logging
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, TraceState

from tensormesh.api.main import app
from tensormesh.telemetry.logging import LokiJSONLogHandler
from tensormesh.telemetry.metrics import (
    active_agents,
    dfars_violations_total,
    record_request_duration,
    request_duration_seconds,
    simd_inversion_duration_us,
)


class TelemetryLGTMTests(unittest.TestCase):
    def test_metrics_endpoint_exposes_tensor_mesh_instruments(self):
        record_request_duration(0.012, "GET", "/metrics-test", 200)
        active_agents.add(1, {"agent": "test"})
        dfars_violations_total.add(1, {"vessel_mmsi": "123", "restricted_port": "Ningbo"})
        simd_inversion_duration_us.record(42.0, {"kernel": "test"})

        response = TestClient(app).get("/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertIn("tensormesh_request_duration_seconds", response.text)
        self.assertIn("tensormesh_dfars_violations_total", response.text)
        self.assertIn("tensormesh_active_agents", response.text)
        self.assertIn("tensormesh_simd_inversion_duration_us", response.text)
        self.assertIn("# TYPE", response.text)

    @patch("tensormesh.telemetry.logging.requests.post")
    def test_loki_handler_injects_trace_context_and_builds_push_payload(self, post):
        post.return_value = Mock(raise_for_status=Mock())
        handler = LokiJSONLogHandler(max_buffer_size=1)
        logger = logging.getLogger("telemetry-lgtm-test")
        logger.handlers = [handler]
        logger.propagate = False

        span_context = SpanContext(
            trace_id=int("4bf92f3577b34da6a3ce929d0e0e4736", 16),
            span_id=int("00f067aa0ba902b7", 16),
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state=TraceState(),
        )
        with trace.use_span(NonRecordingSpan(span_context), end_on_exit=False):
            logger.info("audit message", extra={"event": "TEST_EVENT"})
        handler.close()

        payload = post.call_args.kwargs["json"]
        record = json.loads(payload["streams"][0]["values"][0][1])
        self.assertEqual(record["trace_id"], "4bf92f3577b34da6a3ce929d0e0e4736")
        self.assertEqual(record["span_id"], "00f067aa0ba902b7")
        self.assertEqual(record["event"], "TEST_EVENT")
        self.assertEqual(payload["streams"][0]["values"][0][0], str(int(record["timestamp"] * 1_000_000_000)))


if __name__ == "__main__":
    unittest.main()
