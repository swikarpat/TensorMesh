import tempfile
import unittest
from pathlib import Path

from tensormesh.graph.neo4j_schema import SupplyChainGraph
from tensormesh.mcp.server import MCPToolService
from tensormesh.storage import RocksDBStore


class FakeRecord:
    def __init__(self, data):
        self._data = data

    def data(self):
        return self._data


class FakeSession:
    def __init__(self, record):
        self.record = record
        self.query = None
        self.parameters = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def run(self, query, **parameters):
        self.query = query
        self.parameters = parameters
        return iter([self.record])


class FakeDriver:
    def __init__(self, record):
        self.session_instance = FakeSession(record)

    def session(self):
        return self.session_instance


class GraphRAGMCPTests(unittest.TestCase):
    def test_hybrid_query_combines_graph_entities_and_survey_excerpt(self):
        record = FakeRecord({
            "deposit_name": "Kalahari North",
            "geological_context": "Carbonatite-hosted system",
            "host_rocks": [{"name": "Carbonatite", "lithology": "igneous", "confidence": 0.95}],
            "minerals": [{"name": "Neodymium", "purity_ppm": 1400, "confidence": 0.9}],
            "refinery_paths": [{"name": "Refinery A", "route": "rail", "confidence": 0.8}],
            "survey_excerpts": [{"text": "Core logging confirms fenitized carbonatite."}],
        })
        graph = object.__new__(SupplyChainGraph)
        graph.driver = FakeDriver(record)
        result = graph.query_hybrid_knowledge_graph("Kalahari North")

        self.assertEqual(result["host_rocks"][0]["name"], "Carbonatite")
        self.assertEqual(result["minerals"][0]["purity_ppm"], 1400)
        self.assertIn("fenitized carbonatite", result["survey_synthesis"])
        self.assertEqual(graph.driver.session_instance.parameters, {"deposit_name": "Kalahari North"})

    def test_mcp_filters_low_confidence_graph_facts(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RocksDBStore(Path(directory))
            graph = type("Graph", (), {
                "query_hybrid_knowledge_graph": lambda self, name: {
                    "deposit_name": name,
                    "host_rocks": [{"name": "A", "confidence": 0.9}, {"name": "B", "confidence": 0.4}],
                    "minerals": [], "refinery_paths": [], "survey_excerpts": [],
                }
            })()
            result = MCPToolService(store, graph).query_geological_knowledge_graph("DEP-1", 0.7)
        self.assertEqual([item["name"] for item in result["host_rocks"]], ["A"])


if __name__ == "__main__":
    unittest.main()