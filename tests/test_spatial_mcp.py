import tempfile
import unittest
from pathlib import Path

from tensormesh.mcp.server import (
    MCPToolService,
    ShippingCorridorRequest,
    SpatialConcessionRequest,
)
from tensormesh.storage import CF_A2A_CHECKPOINTS, CF_SPATIAL_VOXELS, RocksDBStore


class SpatialMCPTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = RocksDBStore(Path(self.directory.name))
        self.service = MCPToolService(self.store, object())

    def tearDown(self):
        self.directory.cleanup()

    def test_concession_validation_persists_verified_lease(self):
        result = self.service.query_spatial_concession(SpatialConcessionRequest(
            concession_id="OD-NEO-001",
            latitude=20.3,
            longitude=85.8,
            mineral_type="Neodymium",
        ))
        self.assertTrue(result.verified)
        self.assertEqual(result.state, "Odisha")
        self.assertEqual(result.lease_status, "verified_state_lease")
        self.assertTrue(list(self.store.scan_json(CF_SPATIAL_VOXELS, "concession:OD-NEO-001:")))

    def test_chinese_port_geofence_is_non_compliant(self):
        result = self.service.audit_shipping_corridor(ShippingCorridorRequest(
            origin_port="Singapore",
            destination_port="Yokohama",
            vessel_waypoints=[(29.87, 121.55)],
        ))
        self.assertFalse(result.dfars_compliant)
        self.assertFalse(result.section_848_compliant)
        self.assertEqual(result.chinese_eez_proximity_risk, "high")
        self.assertTrue(result.violations)
        self.assertTrue(list(self.store.scan_json(CF_A2A_CHECKPOINTS, "shipping_audit:")))


if __name__ == "__main__":
    unittest.main()