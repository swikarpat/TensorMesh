import asyncio
import sys
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
from tensormesh.telemetry.otel_tracer import OpenTelemetryTracer, get_otel_tracer


class GeologicalReasoningMesh:
    def __init__(
        self,
        store: RocksDBStore,
        minimum_confidence: float = 0.6,
        telemetry: OpenTelemetryTracer | None = None,
    ):
        self.store = store
        self.supervisor = MultiAgentSupervisor(minimum_confidence=minimum_confidence)
        self.geochemist = GeochemistAgent()
        self.structural_geologist = StructuralGeologistAgent()
        self.economic_assessor = EconomicAssessorAgent()
        self.telemetry = telemetry or get_otel_tracer()

    def evaluate_deposit(
        self,
        **kwargs: Any,
    ) -> ReasoningMeshResult:
        """Synchronously evaluate a deposit for existing API callers."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.evaluate_deposit_async(**kwargs))
        raise RuntimeError("evaluate_deposit cannot be called synchronously from an active event loop; use evaluate_deposit_async")

    async def evaluate_deposit_async(
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
        parent_context = self.telemetry.span(
            "a2a.reasoning_mesh",
            {"task_id": task_id, "agent_role": "reasoning_mesh"},
        )
        parent_span = parent_context.__enter__()

        async def run_geochemist() -> AgentHypothesis:
            with self.telemetry.span(
                "agent.geochemist", {"task_id": task_id, "agent_role": "geochemist"}
            ) as span:
                hypothesis = await asyncio.to_thread(
                    self.geochemist.analyze, task_id, assays, thresholds
                )
                span.set_attribute("confidence_score", hypothesis.confidence_score)
                span.set_attribute("dfars_compliant", False)
                return hypothesis

        async def run_structural_geologist() -> AgentHypothesis:
            with self.telemetry.span(
                "agent.structural_geologist",
                {"task_id": task_id, "agent_role": "structural_geologist"},
            ) as span:
                hypothesis = await asyncio.to_thread(
                    self.structural_geologist.analyze,
                    task_id,
                    strata_intervals,
                    faults,
                    voxel_volume_m3,
                    trajectory_stations,
                )
                span.set_attribute("confidence_score", hypothesis.confidence_score)
                span.set_attribute("dfars_compliant", False)
                return hypothesis

        try:
            geochem, structural = await asyncio.gather(
                run_geochemist(), run_structural_geologist()
            )
            hypotheses.append(geochem)
            self._checkpoint(task_id, "hypothesis", geochem)

            self._store_spatial_voxels(task_id, spatial_voxels or [])
            self._handoff(task_id, geochem, structural, handoffs)
            hypotheses.append(structural)
            self._checkpoint(task_id, "hypothesis", structural)

            async def run_economic_assessor() -> AgentHypothesis:
                with self.telemetry.span(
                    "agent.economic_assessor",
                    {"task_id": task_id, "agent_role": "economic_assessor"},
                ) as span:
                    hypothesis = await asyncio.to_thread(
                        self.economic_assessor.analyze,
                        task_id,
                        geochem,
                        structural,
                        extraction_yield,
                        supply_risk,
                        origin_port,
                        destination_port,
                        vessel_waypoints,
                    )
                    certificate = hypothesis.evidence.get(
                        "dfars_252_225_7052_compliance_certificate", {}
                    )
                    span.set_attribute("confidence_score", hypothesis.confidence_score)
                    span.set_attribute("dfars_compliant", certificate.get("dfars_compliant", False))
                    return hypothesis

            economic = await run_economic_assessor()
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
            parent_span.set_attribute("confidence_score", result.confidence_score)
            parent_span.set_attribute(
                "dfars_compliant",
                economic.evidence.get("dfars_252_225_7052_compliance_certificate", {}).get(
                    "dfars_compliant", False
                ),
            )
            return result
        finally:
            parent_context.__exit__(*sys.exc_info())

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