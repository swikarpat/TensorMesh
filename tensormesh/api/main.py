import json
from statistics import mean
from typing import Any

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import our Core Modules
from tensormesh.security.token_vault import TokenVault
from tensormesh.config.settings import settings
from tensormesh.agents.reasoning_mesh import GeologicalReasoningMesh
from tensormesh.compute import (
    compute_spectral_decomposition,
    invert_acoustic_impedance,
    store_inverted_voxel_trace,
)
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
from tensormesh.simulation.replay_engine import DeterministicReplaySimulator
from tensormesh.storage import RocksDBStore
from tensormesh.telemetry.tracer import CryptographicTracer

app = FastAPI(title="TensorMesh API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize singletons
vault = TokenVault()
tool_service = MCPToolService(RocksDBStore(settings.ROCKSDB_PATH), SupplyChainGraph())
mcp = create_mcp_server(tool_service)
simulator = DeterministicReplaySimulator()
tracer = CryptographicTracer()
reasoning_mesh = GeologicalReasoningMesh(RocksDBStore(settings.ROCKSDB_PATH))

class PromptRequest(BaseModel):
    text: str

class SimulationRequest(BaseModel):
    scenario: str


class DepositEvaluationRequest(BaseModel):
    deposit_id: str = Field(min_length=1)
    borehole_id: str = Field(min_length=1)
    raw_seismic_trace: list[float] = Field(min_length=1)
    elemental_assays: dict[str, float]
    depth_range: list[float] = Field(min_length=2, max_length=2)


DEFAULT_ASSAY_THRESHOLDS = {
    "lithium": 1000.0,
    "cobalt": 300.0,
    "neodymium": 500.0,
    "rare earth elements": 500.0,
}
ELEMENT_ALIASES = {
    "li": "lithium",
    "co": "cobalt",
    "nd": "neodymium",
    "ree": "rare earth elements",
}


app.mount("/mcp", mcp.streamable_http_app())

@app.get("/")
def read_root():
    return {"status": "TensorMesh Backend is Active"}

@app.post("/api/clean-room/redact")
def redact_prompt(req: PromptRequest):
    redacted_text, token_map = vault.redact_and_tokenize(req.text)
    tracer.log_span("TXN-UI", "SecurityAgent", "REDACT_PROMPT", {"tokens_generated": len(token_map)})
    return {"original": req.text, "redacted": redacted_text, "token_map": token_map}

@app.get("/api/graph/trace/{entity_name}")
def trace_supply_chain(entity_name: str):
    response = tool_service.trace_supply_dependency({
        "entity_name": entity_name,
        "mineral": "rare earth",
    })
    tracer.log_span("TXN-UI", "GraphAgent", "QUERY_NEO4J", {"entity": entity_name})
    return {"trace": json.dumps(response.model_dump())}

@app.post("/api/simulate")
def run_simulation(req: SimulationRequest):
    """Runs the XGBoost Ranking Engine against a Policy Shock."""
    historical_data = [
        {"name": "Shadow Port A", "origin": "Vietnam", "china_ownership": 49.0, "geo_risk": 0.8, "itar_compliant": 0.0, "purity": 99.5, "lead_time": 7, "energy": "coal", "recycling": 0.0},
        {"name": "IREL India", "origin": "India", "china_ownership": 0.0, "geo_risk": 0.2, "itar_compliant": 1.0, "purity": 99.9, "lead_time": 14, "energy": "solar_hydro", "recycling": 15.0},
        {"name": "Lynas Rare Earths", "origin": "Australia", "china_ownership": 0.0, "geo_risk": 0.1, "itar_compliant": 1.0, "purity": 99.9, "lead_time": 21, "energy": "grid_mixed", "recycling": 5.0}
    ]
    
    result = simulator.run_policy_shock_simulation(historical_data, shock_scenario=req.scenario)
    tracer.log_span("SIM-UI", "SimulatorAgent", "POLICY_SHOCK", {"scenario": req.scenario})
    
    return {
        "result": result,
        "latest_trace": tracer.trace_log[-1]
    }


@app.post("/api/deposits/evaluate")
def evaluate_deposit(req: DepositEvaluationRequest) -> dict[str, Any]:
    """Run seismic, geological, agentic, and supply-impact evaluation as one transaction."""
    start_depth, end_depth = req.depth_range
    if end_depth <= start_depth:
        raise ValueError("depth_range end must be greater than start")

    dt = 0.001
    z0 = 2000.0
    frequencies = [float(frequency) for frequency in range(10, 100, 10)]
    impedance = invert_acoustic_impedance(req.raw_seismic_trace, z0)
    spectral = compute_spectral_decomposition(req.raw_seismic_trace, frequencies, dt)
    store_inverted_voxel_trace(
        tool_service.store,
        f"{req.deposit_id}:{req.borehole_id}:impedance",
        impedance,
    )

    strata = tool_service.query_borehole_strata(BoreholeStrataRequest(
        borehole_id=req.borehole_id,
        start_depth_m=start_depth,
        end_depth_m=end_depth,
    ))
    if strata.intervals:
        strata_records = [interval.model_dump() for interval in strata.intervals]
    else:
        strata_records = [{
            "borehole_id": req.borehole_id,
            "top_depth_m": start_depth,
            "base_depth_m": end_depth,
            "lithology": "unclassified",
            "observations": {"source": "inferred_from_evaluation_range"},
        }]

    assays = []
    thresholds: dict[str, float] = {}
    for index, (element, concentration) in enumerate(req.elemental_assays.items()):
        canonical_element = ELEMENT_ALIASES.get(element.casefold(), element.casefold())
        thresholds[canonical_element] = DEFAULT_ASSAY_THRESHOLDS.get(canonical_element, 500.0)
        assays.append({
            "sample_id": f"{req.deposit_id}-sample-{index}",
            "element": canonical_element,
            "concentration_ppm": concentration,
            "depth_m": start_depth,
        })
    assay_report = tool_service.evaluate_mineral_assays(MineralAssayRequest(
        deposit_id=req.deposit_id,
        assays=[AssayObservation.model_validate(assay) for assay in assays],
        benchmarks=[AssayBenchmark(element=element, threshold_ppm=threshold) for element, threshold in thresholds.items()],
    ))

    supply_impact = []
    for element in thresholds:
        try:
            impact = tool_service.trace_supply_dependency(SupplyDependencyRequest(
                entity_name=req.deposit_id,
                mineral=element,
            ))
            supply_impact.append(impact.model_dump())
        except Exception as error:
            supply_impact.append({
                "entity_name": req.deposit_id,
                "mineral": element,
                "dependencies": [],
                "bottleneck_entities": [],
                "smelter_concentration_risk": 0.0,
                "status": "graph_unavailable",
                "error": str(error),
            })

    supply_risk = max((impact["smelter_concentration_risk"] for impact in supply_impact), default=0.0)
    agent_result = reasoning_mesh.evaluate_deposit(
        task_id=f"deposit:{req.deposit_id}",
        assays=assays,
        thresholds=thresholds,
        strata_intervals=strata_records,
        faults=[],
        voxel_volume_m3=max(1.0, (end_depth - start_depth) * max(1, len(req.raw_seismic_trace))),
        extraction_yield=0.8,
        supply_risk=supply_risk,
    )
    checkpoint_keys = [
        key for key, _ in tool_service.store.scan_json("cf_a2a_checkpoints", f"{agent_result.task_id}:")
    ]
    impedance_stats = {
        "sample_count": len(impedance),
        "min": float(np.min(impedance)),
        "max": float(np.max(impedance)),
        "mean": float(mean(impedance.tolist())),
        "frequency_count": len(frequencies),
        "spectral_anomaly_flags": [
            bool(float(np.max(np.abs(band))) >= 0.5) for band in spectral
        ],
    }
    tracer.log_span("DEPOSIT-EVAL", "OrchestrationAgent", "DEPOSIT_EVALUATION", {
        "deposit_id": req.deposit_id,
        "checkpoint_count": len(checkpoint_keys),
        "verdict": agent_result.verdict,
    })
    return {
        "deposit_id": req.deposit_id,
        "borehole_id": req.borehole_id,
        "impedance_statistics": impedance_stats,
        "assay_grade_status": assay_report.model_dump(),
        "stratigraphy": strata.model_dump(),
        "a2a_reasoning": agent_result.model_dump(),
        "supply_impact": supply_impact,
        "checkpoint_keys": checkpoint_keys,
        "commercial_viability_verdict": agent_result.verdict,
    }