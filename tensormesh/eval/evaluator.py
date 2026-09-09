from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

from tensormesh.agents.reasoning_mesh import GeologicalReasoningMesh
from tensormesh.security.guardrails import enforce_dfars_output_invariant
from tensormesh.storage import CF_A2A_CHECKPOINTS, RocksDBStore
from tensormesh.eval.golden_dataset import GOLDEN_BENCHMARKS


def _classify(result: Any) -> str:
    structural = next(
        hypothesis for hypothesis in result.hypotheses if hypothesis.agent_id == "structural_geologist"
    )
    economic = next(
        hypothesis for hypothesis in result.hypotheses if hypothesis.agent_id == "economic_assessor"
    )
    if structural.conclusion == "structural_risk_requires_review":
        return "STRUCTURAL_REJECT"
    if economic.conclusion == "commercially_viable":
        return "VIABLE"
    return "NON_VIABLE"


def _render_report(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# TensorMesh Agent Evaluation Scorecard",
        "",
        f"- Grounding Fidelity Score: **{metrics['grounding_fidelity_score']:.3f}**",
        f"- Hallucination Rate: **{metrics['hallucination_rate']:.3f}**",
        f"- DFARS Sanctions Precision: **{metrics['dfars_sanctions_precision']:.3f}**",
        f"- DFARS Sanctions Recall: **{metrics['dfars_sanctions_recall']:.3f}**",
        f"- Mean Decision Latency: **{metrics['mean_decision_latency_ms']:.2f} ms**",
        "",
        "| Case | Expected | Predicted | DFARS | Grounded |",
        "|---|---|---|---|---|",
    ]
    for case in report["cases"]:
        lines.append(
            f"| {case['case_id']} | {case['expected']} | {case['predicted']} | "
            f"{case['dfars_compliant']} | {case['grounded_claims']}/{case['claims']} |"
        )
    lines.append("")
    return "\n".join(lines)


def evaluate_golden_dataset(
    benchmarks: tuple[dict[str, Any], ...] = GOLDEN_BENCHMARKS,
    report_path: Path | str = Path("reports/agent_evaluation_scorecard.md"),
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    true_positive = false_positive = false_negative = 0
    total_claims = grounded_claims = hallucinated_claims = 0
    latencies: list[float] = []

    for benchmark in benchmarks:
        case_id = str(benchmark["case_id"])
        task_id = f"golden:{case_id}"
        start = time.perf_counter()
        with tempfile.TemporaryDirectory() as directory:
            store = RocksDBStore(Path(directory))
            mesh = GeologicalReasoningMesh(store, minimum_confidence=benchmark["minimum_confidence"])
            arguments = {key: value for key, value in benchmark.items() if key not in {
                "case_id", "expected", "expected_dfars_compliant", "minimum_confidence"
            }}
            arguments["task_id"] = task_id
            try:
                result = mesh.evaluate_deposit(**arguments)
                predicted = _classify(result)
                economic = next(h for h in result.hypotheses if h.agent_id == "economic_assessor")
                certificate = economic.evidence.get("dfars_252_225_7052_compliance_certificate", {})
                dfars_compliant = certificate.get("dfars_compliant")
                if predicted == "VIABLE":
                    enforce_dfars_output_invariant(economic)
                claims = len(result.hypotheses)
            except ValueError as error:
                predicted = "SUPERVISOR_REVIEW"
                dfars_compliant = None
                claims = 1
                result = None
                if "handoff blocked" not in str(error):
                    raise
            persisted = list(store.scan(CF_A2A_CHECKPOINTS, f"{task_id}:hypothesis:"))
            grounded = min(claims, len(persisted))
            total_claims += claims
            grounded_claims += grounded
            hallucinated_claims += claims - grounded
            expected_violation = benchmark["expected_dfars_compliant"] is False
            predicted_violation = dfars_compliant is False or predicted == "dfars_violation"
            if expected_violation and predicted_violation:
                true_positive += 1
            elif not expected_violation and predicted_violation:
                false_positive += 1
            elif expected_violation and not predicted_violation:
                false_negative += 1
            cases.append({
                "case_id": case_id,
                "expected": benchmark["expected"],
                "predicted": predicted,
                "dfars_compliant": dfars_compliant,
                "claims": claims,
                "grounded_claims": grounded,
            })
        latencies.append((time.perf_counter() - start) * 1000.0)

    report = {
        "metrics": {
            "grounding_fidelity_score": grounded_claims / total_claims if total_claims else 0.0,
            "hallucination_rate": hallucinated_claims / total_claims if total_claims else 0.0,
            "dfars_sanctions_precision": true_positive / (true_positive + false_positive) if true_positive + false_positive else 1.0,
            "dfars_sanctions_recall": true_positive / (true_positive + false_negative) if true_positive + false_negative else 1.0,
            "mean_decision_latency_ms": sum(latencies) / len(latencies) if latencies else 0.0,
        },
        "cases": cases,
    }
    destination = Path(report_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(_render_report(report), encoding="utf-8")
    return report