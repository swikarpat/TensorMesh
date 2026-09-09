from statistics import mean
from typing import Any

from tensormesh.agents.reasoning_models import AgentHypothesis


class GeochemistAgent:
    agent_id = "geochemist"

    def analyze(self, task_id: str, assays: list[dict[str, Any]], thresholds: dict[str, float]) -> AgentHypothesis:
        by_element: dict[str, list[float]] = {}
        for assay in assays:
            by_element.setdefault(str(assay["element"]).casefold(), []).append(float(assay["concentration_ppm"]))

        anomalies = {
            element: max(values)
            for element, values in by_element.items()
            if max(values) >= thresholds.get(element, float("inf"))
        }
        confidence = min(1.0, 0.55 + (0.1 if assays else 0.0) + min(0.25, len(by_element) * 0.05))
        return AgentHypothesis(
            agent_id=self.agent_id,
            task_id=task_id,
            conclusion="geochemical_anomaly_detected" if anomalies else "no_benchmark_anomaly",
            confidence_score=confidence,
            evidence={
                "sample_count": len(assays),
                "elements": sorted(by_element),
                "mean_concentration_ppm": {
                    element: round(mean(values), 3) for element, values in by_element.items()
                },
                "anomalies": anomalies,
            },
            assumptions=["Benchmarks are supplied in parts per million."],
        )