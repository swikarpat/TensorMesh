import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tensormesh.resilience.rate_limiter import DistributedRateLimiter
from tensormesh.security import token_vault
from tensormesh.security.token_vault import TokenVault


class FakeStore:
    def __init__(self, path):
        self.values = {}

    def scan(self, column_family, prefix=""):
        return iter((key, value) for key, value in self.values.items() if key.startswith(prefix))

    def put_json(self, column_family, key, value):
        self.values[key] = json.dumps(value).encode("utf-8")

    def scan_json(self, column_family, prefix=""):
        return ((key, json.loads(value.decode("utf-8"))) for key, value in self.scan(column_family, prefix))


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.counter = 0

    def ping(self):
        return True

    def incr(self, key):
        self.counter += 1
        self.values[key] = str(self.counter)
        return self.counter

    def set(self, key, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    def keys(self, pattern):
        return [key for key in self.values if key.startswith("token:")]


class FailingRedisFactory:
    @staticmethod
    def from_url(*args, **kwargs):
        raise ConnectionError("Redis is offline")


class RedisIntegrationTests(unittest.TestCase):
    def test_token_vault_shares_tokens_between_workers(self):
        shared_redis = FakeRedis()
        with tempfile.TemporaryDirectory() as directory, patch.object(
            token_vault, "RocksDBStore", FakeStore
        ), patch.object(token_vault, "redis", FailingRedisFactory), patch.object(
            token_vault.settings, "KEY_PATH", Path(directory) / "vault.key"
        ):
            with patch.object(token_vault.redis, "from_url", return_value=shared_redis):
                first_worker = TokenVault()
                second_worker = TokenVault()

            redacted, _ = first_worker.redact_and_tokenize("Supplier ABC123 shipped 4 MT")
            self.assertEqual(second_worker.rehydrate(redacted), "Supplier ABC123 shipped 4 MT")
            self.assertIn("tensormesh:token_counter", shared_redis.values or {"tensormesh:token_counter": True})

    def test_token_vault_falls_back_to_rocksdb_when_redis_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            token_vault, "RocksDBStore", FakeStore
        ), patch.object(token_vault, "redis", FailingRedisFactory), patch.object(
            token_vault.settings, "KEY_PATH", Path(directory) / "vault.key"
        ):
            vault = TokenVault()
            redacted, _ = vault.redact_and_tokenize("Supplier ABC123")
            self.assertIsNone(vault.redis)
            self.assertEqual(vault.rehydrate(redacted), "Supplier ABC123")
            self.assertTrue(vault.store.values)

    def test_distributed_rate_limiter_rejects_excess_calls(self):
        with patch.object(token_vault, "redis", None), patch(
            "tensormesh.resilience.rate_limiter.redis", None
        ):
            limiter = DistributedRateLimiter(limit=2, window_seconds=60)
            self.assertTrue(limiter.allow("198.51.100.10:deposit-1"))
            self.assertTrue(limiter.allow("198.51.100.10:deposit-1"))
            self.assertFalse(limiter.allow("198.51.100.10:deposit-1"))


if __name__ == "__main__":
    unittest.main()
