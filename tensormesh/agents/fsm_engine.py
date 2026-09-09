from typing import Dict, Any
from tensormesh.governance.hitl_pause import HITLGovernor

class DeterministicFSMEngine:
    def __init__(self, compiled_dag: Dict[str, Any]):
        self.dag = compiled_dag
        self.governor = HITLGovernor()
        self.memory = {}

    def execute_workflow(self, execution_id: str, start_state: str):
        """Runs the state machine step-by-step."""
        current_state = start_state
        print(f"[FSM Engine] Starting execution: {execution_id}")

        while current_state:
            print(f" -> [FSM State]: {current_state}")
            state_logic = self.dag.get(current_state)
            
            if not state_logic:
                print("[FSM Engine] Workflow Complete.")
                break

            action = state_logic["action_type"]
            
            # Simulate hitting a high-risk anomaly that requires human intervention
            if action == "ANOMALY_DETECTION" and "human_override" not in self.memory:
                self.governor.suspend_execution(
                    execution_id, 
                    self.memory, 
                    "Shadow Transshipment Risk Detected (Score: 0.9). Approve Reroute?"
                )
                return # Hard stop

            # Move to next state
            allowed_transitions = state_logic["next_allowed"]
            current_state = allowed_transitions[0] if allowed_transitions else None