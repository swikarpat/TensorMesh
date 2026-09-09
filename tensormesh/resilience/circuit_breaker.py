import time
from typing import Callable, Any

class APICircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 10):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED = Healthy, OPEN = Broken, HALF_OPEN = Testing recovery

    def execute(self, api_call: Callable, backup_call: Callable, *args, **kwargs) -> Any:
        """Executes an API call with automatic fallback to a backup function."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                print("[Circuit Breaker] OPEN: Routing directly to backup API.")
                return backup_call(*args, **kwargs)

        try:
            result = api_call(*args, **kwargs)
            self._reset()
            return result
        except Exception as e:
            self._record_failure()
            print(f"[Circuit Breaker] Primary API failed ({e}). Routing to backup API.")
            return backup_call(*args, **kwargs)

    def _record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"

    def _reset(self):
        self.failures = 0
        self.state = "CLOSED"