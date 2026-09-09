import tempfile
import unittest
from pathlib import Path

import grpc

from tensormesh.grpc.generated import maritime_telemetry_pb2 as telemetry_pb2
from tensormesh.grpc.generated import maritime_telemetry_pb2_grpc as telemetry_pb2_grpc
from tensormesh.grpc.service import create_grpc_server
from tensormesh.storage import CF_A2A_CHECKPOINTS, RocksDBStore


class GrpcCorridorBridgeTests(unittest.TestCase):
    def test_live_corridor_audit_returns_response_and_persists_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RocksDBStore(Path(directory))
            server = create_grpc_server(store, port=0)
            server.start()
            try:
                with grpc.insecure_channel(f"localhost:{server._tensormesh_port}") as channel:
                    stub = telemetry_pb2_grpc.MaritimeComplianceServiceStub(channel)
                    response = stub.AuditLiveCorridor(telemetry_pb2.CorridorAuditRequest(
                        mmsi="123456789",
                        vessel_name="Rare Earth Carrier",
                        origin_port="Singapore",
                        destination_port="Yokohama",
                        cargo_manifest="monazite concentrate",
                        waypoints=[telemetry_pb2.LatLng(latitude=29.87, longitude=121.55)],
                    ))
                self.assertFalse(response.dfars_compliant)
                self.assertEqual(response.status, "DFARS_VIOLATION")
                self.assertEqual(response.nearest_restricted_port, "Ningbo coastal smelter")
                self.assertTrue(response.audit_hash)
                records = list(store.scan_json(CF_A2A_CHECKPOINTS, "live_ais:123456789:"))
                self.assertEqual(len(records), 1)
                self.assertEqual(records[0][1]["response"]["audit_hash"], response.audit_hash)
            finally:
                server.stop(0).wait()


if __name__ == "__main__":
    unittest.main()