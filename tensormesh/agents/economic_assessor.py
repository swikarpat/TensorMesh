from typing import Any

from tensormesh.agents.reasoning_models import AgentHypothesis
from tensormesh.mcp.server import audit_shipping_corridor


class EconomicAssessorAgent:
    agent_id = "economic_assessor"

    def analyze(
        self,
        task_id: str,
        geochem: AgentHypothesis,
        structure: AgentHypothesis,
        extraction_yield: float,
        supply_risk: float,
        origin_port: str | None = None,
        destination_port: str | None = None,
        vessel_waypoints: list[tuple[float, float]] | None = None,
    ) -> AgentHypothesis:
        anomaly_count = len(geochem.evidence.get("anomalies", {}))
        volume = float(structure.evidence.get("voxel_volume_m3", 0.0))
        recovery = max(0.0, min(1.0, extraction_yield))
        viability_score = min(1.0, anomaly_count * 0.25 + min(0.4, volume / 1_000_000) + recovery * 0.4)
        viability_score *= max(0.0, 1.0 - max(0.0, min(1.0, supply_risk)) * 0.25)
        verdict = "commercially_viable" if viability_score >= 0.5 else "requires_further_evaluation"
        shipping_audit = None
        if origin_port and destination_port and vessel_waypoints:
            shipping_audit = audit_shipping_corridor(origin_port, destination_port, vessel_waypoints)
        return AgentHypothesis(
            agent_id=self.agent_id,
            task_id=task_id,
            conclusion=verdict,
            confidence_score=min(1.0, 0.5 + abs(viability_score - 0.5)),
            evidence={
                "viability_score": round(viability_score, 4),
                "extraction_yield": recovery,
                "supply_risk": supply_risk,
                "geochemical_conclusion": geochem.conclusion,
                "structural_conclusion": structure.conclusion,
                "dfars_252_225_7052_compliance_certificate": (
                    shipping_audit.model_dump() if shipping_audit else {"status": "not_requested"}
                ),
            },
            assumptions=["Economic viability is a screening verdict, not a feasibility study."],
        )