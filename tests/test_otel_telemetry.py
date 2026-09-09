import unittest

from opentelemetry import context

from tensormesh.telemetry.otel_tracer import OpenTelemetryTracer


class OpenTelemetryTests(unittest.TestCase):
    def test_w3c_trace_context_and_child_attributes(self):
        tracer = OpenTelemetryTracer()
        extracted = tracer.extract_context({
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        })
        token = context.attach(extracted)
        try:
            with tracer.span("agent.geochemist", {"task_id": "TASK-1", "agent_role": "geochemist"}) as span:
                span.set_attribute("confidence_score", 0.91)
                span.set_attribute("dfars_compliant", True)
                self.assertEqual(span.get_span_context().trace_id, int("4bf92f3577b34da6a3ce929d0e0e4736", 16))
                self.assertEqual(span.attributes["task_id"], "TASK-1")
                self.assertEqual(span.attributes["agent_role"], "geochemist")
                self.assertEqual(span.attributes["dfars_compliant"], True)
        finally:
            context.detach(token)

    def test_injects_traceparent_header(self):
        tracer = OpenTelemetryTracer()
        carrier = {}
        with tracer.span("mesh"):
            tracer.inject_context(carrier)
        self.assertTrue(carrier["traceparent"].startswith("00-"))


if __name__ == "__main__":
    unittest.main()