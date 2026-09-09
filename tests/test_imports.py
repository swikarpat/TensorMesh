import importlib
import unittest


MODULES = (
    "tensormesh.api.main",
    "tensormesh.agents.a2a_protocol",
    "tensormesh.agents.fsm_engine",
    "tensormesh.compiler.agentscript",
    "tensormesh.data.ingestion",
    "tensormesh.data.gsi_copilot",
    "tensormesh.graph.neo4j_schema",
    "tensormesh.hardware.vram_router",
    "tensormesh.mcp.server",
    "tensormesh.ml.ranking_engine",
    "tensormesh.security.semantic_cache",
    "tensormesh.security.token_vault",
    "tensormesh.simulation.replay_engine",
    "tensormesh.telemetry.tracer",
)


class PackageImportTests(unittest.TestCase):
    def test_migrated_modules_import(self):
        for module in MODULES:
            with self.subTest(module=module):
                importlib.import_module(module)


if __name__ == "__main__":
    unittest.main()
