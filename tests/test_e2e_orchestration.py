import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tensormesh.agents.reasoning_mesh import GeologicalReasoningMesh
from tensormesh.api import main
from tensormesh.mcp.server import MCPToolService
from tensormesh.storage import CF_BOREHOLE_TELEMETRY, RocksDBStore


class FakeGraph:
    def trace_supply_dependency(self, entity_name: str, mineral: str, max_hops: int):
        return {
            "entity_name": entity_name,
            "mineral": mineral,
            "dependencies": [{"source": "Smelter North", "quantity": 100}],
            "bottleneck_entities": ["Smelter North"],
            "smelter_concentration_risk": 1.0,
        }


class EndToEndOrchestrationTests(unittest.TestCase):
    def test_synthetic_deposit_evaluation_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RocksDBStore(Path(directory))
            store.put_json(CF_BOREHOLE_TELEMETRY, "strata:BH-E2E:000", {
                "borehole_id": "BH-E2E",
                "top_depth_m": 0.0,
                "base_depth_m": 120.0,
                "lithology": "pegmatite",
                "observations": {"continuity": "high"},
            })
            service = MCPToolService(store, FakeGraph())
            mesh = GeologicalReasoningMesh(store)
            with patch.object(main, "tool_service", service), patch.object(main, "reasoning_mesh", mesh):
                response = TestClient(main.app).post("/api/deposits/evaluate", json={
                    "deposit_id": "DEP-E2E",
                    "borehole_id": "BH-E2E",
                    "raw_seismic_trace": [0.05, 0.1, -0.03, 0.02, 0.0],
                    "elemental_assays": {"Li": 1400.0, "Co": 450.0, "Nd": 700.0},
                    "depth_range": [0.0, 120.0],
                })

            self.assertEqual(response.status_code, 200, response.text)
            report = response.json()
            self.assertEqual(report["deposit_id"], "DEP-E2E")
            self.assertEqual(report["impedance_statistics"]["sample_count"], 5)
            self.assertEqual(report["assay_grade_status"]["anomalous_elements"], [
                "lithium", "cobalt", "neodymium"
            ])
            self.assertEqual(len(report["a2a_reasoning"]["hypotheses"]), 3)
            self.assertEqual(len(report["a2a_reasoning"]["handoffs"]), 2)
            self.assertEqual(report["commercial_viability_verdict"], "commercially_viable")
            self.assertEqual(len(report["checkpoint_keys"]), 6)
            self.assertEqual(report["supply_impact"][0]["bottleneck_entities"], ["Smelter North"])


if __name__ == "__main__":
    unittest.main()
