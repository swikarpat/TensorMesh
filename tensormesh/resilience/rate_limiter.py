from collections import defaultdict, deque
import threading
import time

try:
    import redis
except ImportError:
    redis = None

from tensormesh.config.settings import settings


class DistributedRateLimiter:
    """Redis-backed sliding-window limiter with a process-local fallback."""

    _SCRIPT = """
local cutoff = tonumber(ARGV[1]) - tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, cutoff)
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[2])
return redis.call('ZCARD', KEYS[1])
"""

    def __init__(self, limit: int = 20, window_seconds: int = 60, redis_url: str | None = None):
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._windows = defaultdict(deque)
        self.redis = self._connect(redis_url or settings.REDIS_URL)

    @staticmethod
    def _connect(redis_url: str):
        if redis is None:
            return None
        try:
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception:
            return None

    def allow(self, identifier: str) -> bool:
        now = time.time()
        if self.redis is not None:
            try:
                count = self.redis.eval(
                    self._SCRIPT,
                    1,
                    f"tensormesh:rate:{identifier}",
                    str(now),
                    str(self.window_seconds),
                    f"{now}:{id(self)}",
                )
                return int(count) <= self.limit
            except Exception:
                self.redis = None

        with self._lock:
            window = self._windows[identifier]
            cutoff = now - self.window_seconds
            while window and window[0] <= cutoff:
                window.popleft()
            if len(window) >= self.limit:
                return False
            window.append(now)
            return True

    is_allowed = allow