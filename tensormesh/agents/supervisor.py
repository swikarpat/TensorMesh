from tensormesh.agents.a2a_protocol import A2AMessageEnvelope

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
            print(f"[Supervisor] BLOCKED: Handoff from {envelope.sender_agent_id} rejected. Confidence {envelope.confidence_score} < {self.min_confidence}")
            return False