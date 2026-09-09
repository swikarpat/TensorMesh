import tempfile
import unittest
from pathlib import Path

from tensormesh.eval.evaluator import evaluate_golden_dataset


class AgentEvaluationTests(unittest.TestCase):
    def test_golden_dataset_meets_quality_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            report = evaluate_golden_dataset(
                report_path=Path(directory) / "agent_evaluation_scorecard.md"
            )
        metrics = report["metrics"]
        self.assertGreaterEqual(metrics["grounding_fidelity_score"], 0.95)
        self.assertEqual(metrics["dfars_sanctions_recall"], 1.0)
        self.assertEqual(metrics["dfars_sanctions_precision"], 1.0)
        self.assertEqual(len(report["cases"]), 5)


if __name__ == "__main__":
    unittest.main()