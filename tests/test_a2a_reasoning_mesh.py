import tempfile
import unittest
from pathlib import Path

from tensormesh.agents.reasoning_mesh import GeologicalReasoningMesh
from tensormesh.storage import CF_A2A_CHECKPOINTS, RocksDBStore


class A2AReasoningMeshTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = RocksDBStore(Path(self.directory.name))

    def tearDown(self):
        self.directory.cleanup()

    def _evaluate(self, minimum_confidence=0.6):
        return GeologicalReasoningMesh(self.store, minimum_confidence).evaluate_deposit(
            task_id="TASK-1",
            assays=[
                {"element": "Lithium", "concentration_ppm": 1500},
                {"element": "Cobalt", "concentration_ppm": 400},
            ],
            thresholds={"lithium": 1000, "cobalt": 300},
            strata_intervals=[
                {"top_depth_m": 0, "base_depth_m": 100},
                {"top_depth_m": 100, "base_depth_m": 200},
            ],
            faults=[],
            voxel_volume_m3=2_000_000,
            extraction_yield=0.8,
            supply_risk=0.25,
        )

    def test_pipeline_gates_handoffs_and_persists_evidence(self):
        result = self._evaluate()
        self.assertEqual(result.task_id, "TASK-1")
        self.assertEqual(len(result.hypotheses), 3)
        self.assertEqual(len(result.handoffs), 2)
        self.assertEqual(result.verdict, "commercially_viable")
        checkpoints = list(self.store.scan_json(CF_A2A_CHECKPOINTS, "TASK-1:"))
        self.assertEqual(len(checkpoints), 6)
        self.assertTrue(any(key.startswith("TASK-1:handoff:") for key, _ in checkpoints))
        self.assertTrue(all(record.get("task_id") == "TASK-1" for _, record in checkpoints if "agent_id" in record))

    def test_low_confidence_handoff_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "handoff blocked"):
            self._evaluate(minimum_confidence=0.95)


if __name__ == "__main__":
    unittest.main()