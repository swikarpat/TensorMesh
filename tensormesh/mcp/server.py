from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from tensormesh.graph.neo4j_schema import SupplyChainGraph
from tensormesh.storage import CF_BOREHOLE_TELEMETRY, RocksDBStore


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


def create_mcp_server(service: MCPToolService) -> FastMCP:
    server = FastMCP(
        name="TensorMesh Geological MCP",
        instructions="Geological exploration and critical-mineral supply-chain tools.",
        stateless_http=True,
    )

    @server.tool(name="query_borehole_strata", structured_output=True)
    def query_borehole_strata(request: BoreholeStrataRequest) -> BoreholeStrataResponse:
        """Inspect stratigraphic depth intervals and lithology logs."""
        return service.query_borehole_strata(request)

    @server.tool(name="evaluate_mineral_assays", structured_output=True)
    def evaluate_mineral_assays(request: MineralAssayRequest) -> MineralAssayResponse:
        """Evaluate elemental ppm concentrations against deposit benchmarks."""
        return service.evaluate_mineral_assays(request)

    @server.tool(name="trace_supply_dependency", structured_output=True)
    def trace_supply_dependency(request: SupplyDependencyRequest) -> SupplyDependencyResponse:
        """Trace mineral dependencies and identify supply bottlenecks."""
        return service.trace_supply_dependency(request)

    return server
