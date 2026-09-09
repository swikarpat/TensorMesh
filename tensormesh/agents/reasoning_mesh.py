from typing import Any
from uuid import uuid4

from tensormesh.agents.a2a_protocol import A2AMessageEnvelope, A2ARouter
from tensormesh.agents.economic_assessor import EconomicAssessorAgent
from tensormesh.agents.geochemist import GeochemistAgent
from tensormesh.agents.reasoning_models import AgentHypothesis, ReasoningMeshResult
from tensormesh.agents.structural_geologist import StructuralGeologistAgent
from tensormesh.agents.supervisor import MultiAgentSupervisor
from tensormesh.compute import encode_morton_3d
from tensormesh.storage import CF_A2A_CHECKPOINTS, CF_SPATIAL_VOXELS, RocksDBStore


class GeologicalReasoningMesh:
    def __init__(self, store: RocksDBStore, minimum_confidence: float = 0.6):
        self.store = store
        self.supervisor = MultiAgentSupervisor(minimum_confidence=minimum_confidence)
        self.geochemist = GeochemistAgent()
        self.structural_geologist = StructuralGeologistAgent()
        self.economic_assessor = EconomicAssessorAgent()

    def evaluate_deposit(
        self,
        *,
        task_id: str | None = None,
        assays: list[dict[str, Any]],
        thresholds: dict[str, float],
        strata_intervals: list[dict[str, Any]],
        faults: list[dict[str, Any]],
        voxel_volume_m3: float,
        extraction_yield: float,
        supply_risk: float,
        trajectory_stations: list[dict[str, Any]] | None = None,
        spatial_voxels: list[tuple[int, int, int]] | None = None,
        origin_port: str | None = None,
        destination_port: str | None = None,
        vessel_waypoints: list[tuple[float, float]] | None = None,
    ) -> ReasoningMeshResult:
        task_id = task_id or str(uuid4())
        hypotheses: list[AgentHypothesis] = []
        handoffs: list[dict[str, Any]] = []

        geochem = self.geochemist.analyze(task_id, assays, thresholds)
        hypotheses.append(geochem)
        self._checkpoint(task_id, "hypothesis", geochem)

        structural = self.structural_geologist.analyze(
            task_id, strata_intervals, faults, voxel_volume_m3, trajectory_stations
        )
        self._store_spatial_voxels(task_id, spatial_voxels or [])
        self._handoff(task_id, geochem, structural, handoffs)
        hypotheses.append(structural)
        self._checkpoint(task_id, "hypothesis", structural)

        economic = self.economic_assessor.analyze(
            task_id,
            geochem,
            structural,
            extraction_yield,
            supply_risk,
            origin_port,
            destination_port,
            vessel_waypoints,
        )
        certificate = economic.evidence.get("dfars_252_225_7052_compliance_certificate", {})
        audit_hash = certificate.get("audit_hash")
        if audit_hash:
            self.store.put_json(
                CF_A2A_CHECKPOINTS,
                f"{task_id}:shipping_audit:{audit_hash}",
                {"task_id": task_id, **certificate},
            )
        self._handoff(task_id, structural, economic, handoffs)
        hypotheses.append(economic)
        self._checkpoint(task_id, "hypothesis", economic)

        result = ReasoningMeshResult(
            task_id=task_id,
            verdict=economic.conclusion,
            confidence_score=economic.confidence_score,
            hypotheses=hypotheses,
            handoffs=handoffs,
        )
        self.store.put_json(
            CF_A2A_CHECKPOINTS,
            f"{task_id}:verdict",
            result.model_dump(),
        )
        return result

    def _store_spatial_voxels(self, task_id: str, spatial_voxels: list[tuple[int, int, int]]) -> None:
        for x, y, z in spatial_voxels:
            code = encode_morton_3d(int(x), int(y), int(z))
            self.store.put_json(
                CF_SPATIAL_VOXELS,
                f"morton:{code:016x}",
                {"task_id": task_id, "x": int(x), "y": int(y), "z": int(z), "morton_code": code},
            )

    def _checkpoint(self, task_id: str, record_type: str, payload: AgentHypothesis) -> None:
        self.store.put_json(
            CF_A2A_CHECKPOINTS,
            f"{task_id}:{record_type}:{payload.agent_id}",
            payload.model_dump(),
        )

    def _handoff(
        self,
        task_id: str,
        source: AgentHypothesis,
        target: AgentHypothesis,
        handoffs: list[dict[str, Any]],
    ) -> None:
        envelope = A2AMessageEnvelope(
            sender_agent_id=source.agent_id,
            recipient_agent_id=target.agent_id,
            intent_capability="GEOLOGICAL_REASONING_HANDOFF",
            payload_data={"hypothesis": source.model_dump()},
            confidence_score=source.confidence_score,
            evidence_refs=[f"{task_id}:hypothesis:{source.agent_id}"],
            task_id=task_id,
        )
        if not self.supervisor.evaluate_handoff(envelope):
            raise ValueError(f"A2A handoff blocked for {source.agent_id}: confidence below threshold")
        delivery = A2ARouter.dispatch(envelope)
        record = {"envelope": envelope.model_dump(), "delivery": delivery}
        handoffs.append(record)
        self.store.put_json(
            CF_A2A_CHECKPOINTS,
            f"{task_id}:handoff:{envelope.message_id}",
            record,
        )