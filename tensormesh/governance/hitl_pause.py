from typing import Dict, Any
from tensormesh.config.settings import settings
from tensormesh.storage import CF_SECURE_STATE, RocksDBStore

class HITLGovernor:
    def __init__(self):
        self.store = RocksDBStore(settings.ROCKSDB_PATH)

    def suspend_execution(self, execution_id: str, current_memory: Dict[str, Any], alert_message: str):
        """Hard-pauses the FSM and saves state to disk."""
        self.store.put_json(
            CF_SECURE_STATE,
            f"hitl:{execution_id}",
            {"state_memory": current_memory, "status": "PAUSED_PENDING_HUMAN"},
        )
        
        # Simulate sending a Slack/Teams webhook to the Defense Procurement Officer
        print(f"\n🚨 [SLACK WEBHOOK FIRED] To: Procurement Manager")
        print(f"🚨 ALERT: {alert_message}")
        print(f"🚨 Execution {execution_id} suspended. Awaiting human approval...\n")

    def hydrate_and_resume(self, execution_id: str, human_decision: str) -> Dict[str, Any]:
        """Loads state back into memory after human clicks 'Approve' or 'Reject'."""
        record = self.store.get_json(CF_SECURE_STATE, f"hitl:{execution_id}")
        if record is None:
            raise ValueError("Execution ID not found.")
        memory = record["state_memory"]
        memory["human_override"] = human_decision
        self.store.put_json(
            CF_SECURE_STATE,
            f"hitl:{execution_id}",
            {"state_memory": memory, "status": "RESUMED"},
        )
        return memory