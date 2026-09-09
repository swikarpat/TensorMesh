import hashlib
import json
import math
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from tensormesh.graph.neo4j_schema import SupplyChainGraph
from tensormesh.storage import CF_A2A_CHECKPOINTS, CF_BOREHOLE_TELEMETRY, CF_SPATIAL_VOXELS, RocksDBStore
from tensormesh.telemetry.otel_tracer import get_otel_tracer


class BoreholeStrataRequest(BaseModel):
    borehole_id: str = Field(min_length=1)
    start_depth_m: float = Field(default=0.0, ge=0.0)
    end_depth_m: float | None = Field(default=None, gt=0.0)


class StrataInterval(BaseModel):
    borehole_id: str
    top_depth_m: float
    base_depth_m: float
    lithology: str
    observations: dict[str, Any] = Field(default_factory=dict)


class BoreholeStrataResponse(BaseModel):
    borehole_id: str
    intervals: list[StrataInterval]


class AssayObservation(BaseModel):
    sample_id: str
    element: str
    concentration_ppm: float = Field(ge=0.0)
    depth_m: float | None = Field(default=None, ge=0.0)


class AssayBenchmark(BaseModel):
    element: str
    threshold_ppm: float = Field(ge=0.0)


class MineralAssayRequest(BaseModel):
    deposit_id: str = Field(min_length=1)
    assays: list[AssayObservation]
    benchmarks: list[AssayBenchmark]


class AssayEvaluation(BaseModel):
    element: str
    observed_max_ppm: float
    threshold_ppm: float
    anomaly_detected: bool
    sample_count: int


class MineralAssayResponse(BaseModel):
    deposit_id: str
    evaluations: list[AssayEvaluation]
    anomalous_elements: list[str]


class SupplyDependencyRequest(BaseModel):
    entity_name: str = Field(min_length=1)
    mineral: str = Field(min_length=1)
    max_hops: int = Field(default=4, ge=1, le=8)


class SupplyDependencyResponse(BaseModel):
    entity_name: str
    mineral: str
    dependencies: list[dict[str, Any]]
    bottleneck_entities: list[str]
    smelter_concentration_risk: float = Field(ge=0.0, le=1.0)


class SpatialConcessionRequest(BaseModel):
    concession_id: str = Field(min_length=1)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    mineral_type: str = Field(min_length=1)


class SpatialConcessionResponse(BaseModel):
    concession_id: str
    verified: bool
    state: str | None
    lease_status: str
    mineral_type: str
    findings: list[str]
    audit_hash: str


class ShippingCorridorRequest(BaseModel):
    origin_port: str = Field(min_length=1)
    destination_port: str = Field(min_length=1)
    vessel_waypoints: list[tuple[float, float]] = Field(min_length=1)


class ShippingCorridorResponse(BaseModel):
    origin_port: str
    destination_port: str
    dfars_compliant: bool
    section_848_compliant: bool
    chinese_eez_proximity_risk: str
    violations: list[str]
    audit_hash: str


class MCPToolService:
    def __init__(self, store: RocksDBStore, graph_db: SupplyChainGraph):
        self.store = store
        self.graph_db = graph_db

    def query_borehole_strata(self, request: BoreholeStrataRequest) -> BoreholeStrataResponse:
        intervals = []
        for _, record in self.store.scan_json(CF_BOREHOLE_TELEMETRY, f"strata:{request.borehole_id}:"):
            interval = StrataInterval.model_validate(record)
            if interval.base_depth_m < request.start_depth_m:
                continue
            if request.end_depth_m is not None and interval.top_depth_m > request.end_depth_m:
                continue
            intervals.append(interval)
        intervals.sort(key=lambda interval: interval.top_depth_m)
        return BoreholeStrataResponse(borehole_id=request.borehole_id, intervals=intervals)

    def evaluate_mineral_assays(self, request: MineralAssayRequest) -> MineralAssayResponse:
        evaluations = []
        assays_by_element: dict[str, list[AssayObservation]] = {}
        for assay in request.assays:
            assays_by_element.setdefault(assay.element.casefold(), []).append(assay)

        for benchmark in request.benchmarks:
            observations = assays_by_element.get(benchmark.element.casefold(), [])
            observed_max = max((assay.concentration_ppm for assay in observations), default=0.0)
            evaluations.append(
                AssayEvaluation(
                    element=benchmark.element,
                    observed_max_ppm=observed_max,
                    threshold_ppm=benchmark.threshold_ppm,
                    anomaly_detected=observed_max >= benchmark.threshold_ppm,
                    sample_count=len(observations),
                )
            )

        return MineralAssayResponse(
            deposit_id=request.deposit_id,
            evaluations=evaluations,
            anomalous_elements=[
                evaluation.element for evaluation in evaluations if evaluation.anomaly_detected
            ],
        )

    def trace_supply_dependency(self, request: SupplyDependencyRequest) -> SupplyDependencyResponse:
        result = self.graph_db.trace_supply_dependency(
            entity_name=request.entity_name,
            mineral=request.mineral,
            max_hops=request.max_hops,
        )
        return SupplyDependencyResponse.model_validate(result)

    def query_geological_knowledge_graph(
        self, deposit_name: str, min_confidence: float = 0.7
    ) -> dict[str, Any]:
        if not deposit_name.strip():
            raise ValueError("deposit_name must not be empty")
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        result = self.graph_db.query_hybrid_knowledge_graph(deposit_name)
        for field in ("host_rocks", "minerals", "refinery_paths"):
            result[field] = [
                item for item in result.get(field, [])
                if float(item.get("confidence", 1.0)) >= min_confidence
            ]
        result["min_confidence"] = min_confidence
        return result

    def query_spatial_concession(self, request: SpatialConcessionRequest) -> SpatialConcessionResponse:
        regions = {
            "Odisha": (18.0, 22.5, 81.3, 87.5),
            "Gujarat": (20.0, 24.7, 68.0, 74.5),
            "Kerala": (8.2, 12.8, 74.8, 77.4),
            "Rajasthan": (24.5, 30.2, 69.5, 78.3),
        }
        critical_minerals = {"neodymium", "monazite"}
        state = next(
            (name for name, (south, north, west, east) in regions.items()
             if south <= request.latitude <= north and west <= request.longitude <= east),
            None,
        )
        mineral_supported = request.mineral_type.casefold() in critical_minerals
        verified = state is not None and mineral_supported
        findings = []
        if state is None:
            findings.append("Coordinate is outside the configured Indian critical-mineral blocks")
        else:
            findings.append(f"Coordinate intersects the {state} critical-mineral block")
        if not mineral_supported:
            findings.append("Mineral type is not in the supported critical-mineral registry")
        response_data = {
            "concession_id": request.concession_id,
            "verified": verified,
            "state": state,
            "lease_status": "verified_state_lease" if verified else "unverified",
            "mineral_type": request.mineral_type,
            "findings": findings,
        }
        audit_hash = _audit_hash(response_data)
        response = SpatialConcessionResponse(**response_data, audit_hash=audit_hash)
        self.store.put_json(CF_SPATIAL_VOXELS, f"concession:{request.concession_id}:{audit_hash}", response.model_dump())
        return response

    def audit_shipping_corridor(self, request: ShippingCorridorRequest) -> ShippingCorridorResponse:
        response = audit_shipping_corridor(
            request.origin_port, request.destination_port, request.vessel_waypoints
        )
        self.store.put_json(
            CF_A2A_CHECKPOINTS,
            f"shipping_audit:{response.audit_hash}",
            response.model_dump(),
        )
        return response


def _audit_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _distance_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    latitude_1, longitude_1 = map(math.radians, first)
    latitude_2, longitude_2 = map(math.radians, second)
    delta_latitude = latitude_2 - latitude_1
    delta_longitude = longitude_2 - longitude_1
    value = math.sin(delta_latitude / 2) ** 2 + math.cos(latitude_1) * math.cos(latitude_2) * math.sin(delta_longitude / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(value))


def _evaluate_shipping_corridor(request: ShippingCorridorRequest) -> dict[str, Any]:
    geofences = {
        "Ningbo coastal smelter": ((29.87, 121.55), 90.0),
        "Hainan processing hub": ((19.2, 109.7), 150.0),
        "South China Sea transshipment hub": ((16.0, 114.0), 180.0),
    }
    violations = []
    nearest_eez_distance = float("inf")
    for waypoint in request.vessel_waypoints:
        for name, (center, radius_km) in geofences.items():
            distance = _distance_km(waypoint, center)
            nearest_eez_distance = min(nearest_eez_distance, distance)
            if distance <= radius_km:
                violations.append(f"Waypoint {waypoint} intersects {name} geofence")
    violations = sorted(set(violations))
    risk = "high" if violations else "elevated" if nearest_eez_distance <= 370.0 else "low"
    return {
        "origin_port": request.origin_port,
        "destination_port": request.destination_port,
        "dfars_compliant": not violations,
        "section_848_compliant": not violations,
        "chinese_eez_proximity_risk": risk,
        "violations": violations,
    }


def audit_shipping_corridor(
    origin_port: str, destination_port: str, vessel_waypoints: list[tuple[float, float]]
) -> ShippingCorridorResponse:
    request = ShippingCorridorRequest(
        origin_port=origin_port,
        destination_port=destination_port,
        vessel_waypoints=vessel_waypoints,
    )
    response_data = _evaluate_shipping_corridor(request)
    return ShippingCorridorResponse(**response_data, audit_hash=_audit_hash(response_data))


def create_mcp_server(service: MCPToolService) -> FastMCP:
    server = FastMCP(
        name="TensorMesh Geological MCP",
        instructions="Geological exploration and critical-mineral supply-chain tools.",
        stateless_http=True,
    )
    telemetry = get_otel_tracer()

    @server.tool(name="query_borehole_strata", structured_output=True)
    def query_borehole_strata(request: BoreholeStrataRequest) -> BoreholeStrataResponse:
        """Inspect stratigraphic depth intervals and lithology logs."""
        with telemetry.span("mcp.query_borehole_strata", {"agent_role": "mcp"}):
            return service.query_borehole_strata(request)

    @server.tool(name="evaluate_mineral_assays", structured_output=True)
    def evaluate_mineral_assays(request: MineralAssayRequest) -> MineralAssayResponse:
        """Evaluate elemental ppm concentrations against deposit benchmarks."""
        with telemetry.span("mcp.evaluate_mineral_assays", {"agent_role": "mcp"}):
            return service.evaluate_mineral_assays(request)

    @server.tool(name="trace_supply_dependency", structured_output=True)
    def trace_supply_dependency(request: SupplyDependencyRequest) -> SupplyDependencyResponse:
        """Trace mineral dependencies and identify supply bottlenecks."""
        with telemetry.span("mcp.trace_supply_dependency", {"agent_role": "mcp"}):
            return service.trace_supply_dependency(request)

    @server.tool(name="query_geological_knowledge_graph", structured_output=True)
    def query_geological_knowledge_graph(
        deposit_name: str, min_confidence: float = 0.7
    ) -> dict[str, Any]:
        """Retrieve geological context, mineral purity, and refinery paths."""
        with telemetry.span(
            "mcp.query_geological_knowledge_graph",
            {"agent_role": "mcp", "deposit_name": deposit_name, "min_confidence": min_confidence},
        ):
            return service.query_geological_knowledge_graph(deposit_name, min_confidence)

    @server.tool(name="query_spatial_concession", structured_output=True)
    def query_spatial_concession(request: SpatialConcessionRequest) -> SpatialConcessionResponse:
        """Verify an Indian critical-mineral concession coordinate and lease status."""
        with telemetry.span("mcp.query_spatial_concession", {"agent_role": "mcp"}):
            return service.query_spatial_concession(request)

    @server.tool(name="audit_shipping_corridor", structured_output=True)
    def audit_shipping_corridor(request: ShippingCorridorRequest) -> ShippingCorridorResponse:
        """Audit vessel waypoints against maritime supply-chain geofences."""
        with telemetry.span("mcp.audit_shipping_corridor", {"agent_role": "mcp"}):
            return service.audit_shipping_corridor(request)

    return server
