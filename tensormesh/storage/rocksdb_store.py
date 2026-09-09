import json
from pathlib import Path
from typing import Any, Iterator

try:
    from tensormesh.storage._rocksdb_bridge import RocksDBStore as _NativeRocksDBStore
except ImportError as error:  # pragma: no cover - exercised when the native build is absent
    _NativeRocksDBStore = None
    _NATIVE_IMPORT_ERROR = error

CF_SPATIAL_VOXELS = "cf_spatial_voxels"
CF_BOREHOLE_TELEMETRY = "cf_borehole_telemetry"
CF_A2A_CHECKPOINTS = "cf_a2a_checkpoints"
CF_SECURE_STATE = "cf_secure_state"
COLUMN_FAMILIES = (
    CF_SPATIAL_VOXELS,
    CF_BOREHOLE_TELEMETRY,
    CF_A2A_CHECKPOINTS,
    CF_SECURE_STATE,
)


class RocksDBStore:
    """Typed Python facade over the native RocksDB 11.x adapter."""

    _instances: dict[str, "RocksDBStore"] = {}

    def __new__(cls, path: Path | str):
        normalized_path = str(Path(path).expanduser().resolve())
        if normalized_path not in cls._instances:
            instance = super().__new__(cls)
            instance._normalized_path = normalized_path
            cls._instances[normalized_path] = instance
        return cls._instances[normalized_path]

    def __init__(self, path: Path | str):
        if hasattr(self, "_db"):
            return
        if _NativeRocksDBStore is None:
            raise RuntimeError(
                "The native RocksDB bridge is unavailable. Build tensormesh-compute "
                "with CMake before starting TensorMesh."
            ) from _NATIVE_IMPORT_ERROR
        self._db = _NativeRocksDBStore(self._normalized_path, list(COLUMN_FAMILIES))

    def put(self, column_family: str, key: str, value: bytes) -> None:
        self._validate_column_family(column_family)
        self._db.put(column_family, key, value)

    def get(self, column_family: str, key: str) -> bytes | None:
        self._validate_column_family(column_family)
        return self._db.get(column_family, key)

    def delete(self, column_family: str, key: str) -> None:
        self._validate_column_family(column_family)
        self._db.delete(column_family, key)

    def scan(self, column_family: str, prefix: str = "") -> Iterator[tuple[str, bytes]]:
        self._validate_column_family(column_family)
        yield from self._db.scan(column_family, prefix)

    def put_json(self, column_family: str, key: str, value: Any) -> None:
        self.put(
            column_family,
            key,
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )

    def get_json(self, column_family: str, key: str) -> Any | None:
        value = self.get(column_family, key)
        return None if value is None else json.loads(value.decode("utf-8"))

    def scan_json(self, column_family: str, prefix: str = "") -> Iterator[tuple[str, Any]]:
        for key, value in self.scan(column_family, prefix):
            yield key, json.loads(value.decode("utf-8"))

    @staticmethod
    def _validate_column_family(column_family: str) -> None:
        if column_family not in COLUMN_FAMILIES:
            raise ValueError(f"Unknown TensorMesh column family: {column_family}")
