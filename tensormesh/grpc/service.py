from __future__ import annotations

import time
from concurrent import futures

import grpc

from tensormesh.grpc.generated import maritime_telemetry_pb2 as telemetry_pb2
from tensormesh.grpc.generated import maritime_telemetry_pb2_grpc as telemetry_pb2_grpc
from tensormesh.mcp.server import audit_shipping_corridor, _distance_km
from tensormesh.storage import CF_A2A_CHECKPOINTS, RocksDBStore


_RESTRICTED_PORTS = {
    "Ningbo coastal smelter": (29.87, 121.55),
    "Hainan processing hub": (19.2, 109.7),
    "South China Sea transshipment hub": (16.0, 114.0),
}


class MaritimeComplianceServer(telemetry_pb2_grpc.MaritimeComplianceServiceServicer):
    def __init__(self, store: RocksDBStore):
        self.store = store

    def AuditLiveCorridor(self, request, context):
        waypoints = [(point.latitude, point.longitude) for point in request.waypoints]
        audit = audit_shipping_corridor(
            request.origin_port,
            request.destination_port,
            waypoints,
        )
        distances = {
            name: min((_distance_km(point, center) for point in waypoints), default=float("inf"))
            for name, center in _RESTRICTED_PORTS.items()
        }
        nearest_name, nearest_distance = min(
            distances.items(), key=lambda item: item[1], default=("", float("inf"))
        )
        status = "DFARS_COMPLIANT" if audit.dfars_compliant else "DFARS_VIOLATION"
        timestamp = int(time.time() * 1000)
        response = telemetry_pb2.CorridorAuditResponse(
            dfars_compliant=audit.dfars_compliant,
            status=status,
            nearest_restricted_port=nearest_name if nearest_distance != float("inf") else "",
            distance_km=nearest_distance if nearest_distance != float("inf") else 0.0,
            audit_hash=audit.audit_hash,
        )
        self.store.put_json(
            CF_A2A_CHECKPOINTS,
            f"live_ais:{request.mmsi}:{timestamp}",
            {
                "mmsi": request.mmsi,
                "vessel_name": request.vessel_name,
                "origin_port": request.origin_port,
                "destination_port": request.destination_port,
                "cargo_manifest": request.cargo_manifest,
                "waypoints": [point for point in waypoints],
                "response": {
                    "dfars_compliant": response.dfars_compliant,
                    "status": response.status,
                    "nearest_restricted_port": response.nearest_restricted_port,
                    "distance_km": response.distance_km,
                    "audit_hash": response.audit_hash,
                },
            },
        )
        return response


def create_grpc_server(store: RocksDBStore, port: int = 50051) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    telemetry_pb2_grpc.add_MaritimeComplianceServiceServicer_to_server(
        MaritimeComplianceServer(store), server
    )
    server._tensormesh_port = server.add_insecure_port(f"[::]:{port}")
    return server


def serve(store: RocksDBStore, port: int = 50051) -> None:
    server = create_grpc_server(store, port)
    server.start()
    server.wait_for_termination()