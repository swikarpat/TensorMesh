import hashlib
import time
import json
from typing import Dict, Any
from tensormesh.config.settings import settings
from tensormesh.storage import CF_SECURE_STATE, RocksDBStore

class CryptographicTracer:
    def __init__(self):
        self.store = RocksDBStore(settings.ROCKSDB_PATH)
        self.previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        existing_spans = self.trace_log
        if existing_spans:
            self.previous_hash = existing_spans[-1]["hash"]

    @property
    def trace_log(self):
        return [span for _, span in self.store.scan_json(CF_SECURE_STATE, "trace:")]

    def _hash_payload(self, payload: str, prev_hash: str) -> str:
        """Creates a SHA-256 hash linking the current action to the previous one."""
        block = f"{payload}|{prev_hash}".encode('utf-8')
        return hashlib.sha256(block).hexdigest()

    def log_span(self, execution_id: str, agent_name: str, action: str, data: Dict[str, Any]):
        """Logs an event into the immutable trace chain."""
        timestamp = time.time()
        payload = json.dumps({"exec_id": execution_id, "agent": agent_name, "action": action, "data": data}, sort_keys=True)
        
        current_hash = self._hash_payload(payload, self.previous_hash)
        
        span = {
            "timestamp": timestamp,
            "execution_id": execution_id,
            "agent_name": agent_name,
            "action": action,
            "payload": data,
            "hash": current_hash,
            "parent_hash": self.previous_hash
        }
        
        self.store.put_json(
            CF_SECURE_STATE,
            f"trace:{time.time_ns():020d}:{current_hash}",
            span,
        )
        self.previous_hash = current_hash
        print(f"[Tracer] Logged {action} | Hash: {current_hash[:8]}...")

    def verify_trace_integrity(self) -> bool:
        """Audits the log to ensure no data was tampered with."""
        temp_prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        for span in self.trace_log:
            payload = json.dumps({"exec_id": span["execution_id"], "agent": span["agent_name"], "action": span["action"], "data": span["payload"]}, sort_keys=True)
            expected_hash = self._hash_payload(payload, temp_prev_hash)
            
            if expected_hash != span["hash"]:
                print(f"[Tracer] 🚨 INTEGRITY COMPROMISED at span {span['action']}")
                return False
            temp_prev_hash = span["hash"]
            
        return True