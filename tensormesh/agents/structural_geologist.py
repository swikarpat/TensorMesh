from typing import Any

from tensormesh.agents.reasoning_models import AgentHypothesis


class StructuralGeologistAgent:
    agent_id = "structural_geologist"

    def analyze(
        self,
        task_id: str,
        strata_intervals: list[dict[str, Any]],
        faults: list[dict[str, Any]],
        voxel_volume_m3: float,
    ) -> AgentHypothesis:
        ordered = sorted(strata_intervals, key=lambda interval: float(interval["top_depth_m"]))
        continuity_gaps = sum(
            1
            for previous, current in zip(ordered, ordered[1:])
            if float(current["top_depth_m"]) > float(previous["base_depth_m"])
        )
        structural_risk = min(1.0, len(faults) * 0.15 + continuity_gaps * 0.2)
        confidence = 0.6 if ordered else 0.25
        return AgentHypothesis(
            agent_id=self.agent_id,
            task_id=task_id,
            conclusion="structurally_continuous" if structural_risk < 0.5 else "structural_risk_requires_review",
            confidence_score=confidence,
            evidence={
                "interval_count": len(ordered),
                "fault_count": len(faults),
                "continuity_gaps": continuity_gaps,
                "structural_risk": round(structural_risk, 3),
                "voxel_volume_m3": voxel_volume_m3,
            },
            assumptions=["Voxel volume is an interpreted mineralized volume."],
        )