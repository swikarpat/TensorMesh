from tensormesh.agents.a2a_protocol import A2AMessageEnvelope
from tensormesh.telemetry.logging import logger
from tensormesh.telemetry.metrics import record_dfars_violation

class MultiAgentSupervisor:
    def __init__(self, minimum_confidence: float = 0.85):
        self.min_confidence = minimum_confidence

    def evaluate_handoff(self, envelope: A2AMessageEnvelope) -> bool:
        """
        Anti-Amplification Engine: Blocks agent handoffs if the 
        sender's confidence score is too low.
        """
        if envelope.confidence_score >= self.min_confidence:
            return True
        else:
            record_dfars_violation(
                getattr(envelope, "vessel_mmsi", "unknown"),
                getattr(envelope, "restricted_port", "unknown"),
            )
            logger.warning(
                "Agent handoff blocked by compliance confidence policy",
                extra={
                    "event": "DFARS_VIOLATION_DETECTED",
                    "task_id": envelope.task_id,
                    "vessel_mmsi": getattr(envelope, "vessel_mmsi", "unknown"),
                    "restricted_port": getattr(envelope, "restricted_port", "unknown"),
                },
            )
            print(f"[Supervisor] BLOCKED: Handoff from {envelope.sender_agent_id} rejected. Confidence {envelope.confidence_score} < {self.min_confidence}")
            return False