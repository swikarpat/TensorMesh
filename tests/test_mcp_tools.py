import asyncio
import tempfile
import unittest
from pathlib import Path

from tensormesh.graph.neo4j_schema import SupplyChainGraph
from tensormesh.mcp.server import (
    AssayBenchmark,
    AssayObservation,
    BoreholeStrataRequest,
    MCPToolService,
    MineralAssayRequest,
    SupplyDependencyRequest,
    create_mcp_server,
)
from tensormesh.storage import CF_BOREHOLE_TELEMETRY, RocksDBStore


class FakeGraph:
    def trace_supply_dependency(self, entity_name: str, mineral: str, max_hops: int):
        return {
            "entity_name": entity_name,
            "mineral": mineral,
            "dependencies": [{"source": "Smelter A", "quantity": 80}],
            "bottleneck_entities": ["Smelter A"],
            "smelter_concentration_risk": 0.8,
        }


class MCPToolTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = RocksDBStore(Path(self.directory.name))
        self.service = MCPToolService(self.store, FakeGraph())

    def tearDown(self):
        self.directory.cleanup()

    def test_borehole_strata_depth_filter(self):
        self.store.put_json(CF_BOREHOLE_TELEMETRY, "strata:BH-1:000", {
            "borehole_id": "BH-1", "top_depth_m": 0, "base_depth_m": 10, "lithology": "basalt"
        })
        self.store.put_json(CF_BOREHOLE_TELEMETRY, "strata:BH-1:010", {
            "borehole_id": "BH-1", "top_depth_m": 10, "base_depth_m": 25, "lithology": "pegmatite"
        })
        result = self.service.query_borehole_strata(BoreholeStrataRequest(
            borehole_id="BH-1", start_depth_m=8, end_depth_m=20
        ))
        self.assertEqual([interval.lithology for interval in result.intervals], ["basalt", "pegmatite"])

    def test_assay_thresholds_are_case_insensitive(self):
        result = self.service.evaluate_mineral_assays(MineralAssayRequest(
            deposit_id="DEP-1",
            assays=[
                AssayObservation(sample_id="S1", element="Lithium", concentration_ppm=900),
                AssayObservation(sample_id="S2", element="lithium", concentration_ppm=1200),
                AssayObservation(sample_id="S3", element="Cobalt", concentration_ppm=30),
            ],
            benchmarks=[
                AssayBenchmark(element="LITHIUM", threshold_ppm=1000),
                AssayBenchmark(element="Cobalt", threshold_ppm=100),
            ],
        ))
        self.assertEqual(result.anomalous_elements, ["LITHIUM"])
        self.assertEqual(result.evaluations[0].observed_max_ppm, 1200)
        self.assertFalse(result.evaluations[1].anomaly_detected)

    def test_supply_dependency_tool(self):
        result = self.service.trace_supply_dependency(SupplyDependencyRequest(
            entity_name="Defense OEM", mineral="Lithium"
        ))
        self.assertEqual(result.bottleneck_entities, ["Smelter A"])
        self.assertEqual(result.smelter_concentration_risk, 0.8)

    def test_fastmcp_registers_typed_tools(self):
        server = create_mcp_server(self.service)
        tools = asyncio.run(server.list_tools())
        self.assertEqual(
            {tool.name for tool in tools},
            {"query_borehole_strata", "evaluate_mineral_assays", "trace_supply_dependency"},
        )


if __name__ == "__main__":
    unittest.main()