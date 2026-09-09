import tempfile
import unittest
from pathlib import Path

from tensormesh.storage import (
    CF_A2A_CHECKPOINTS,
    CF_BOREHOLE_TELEMETRY,
    CF_SECURE_STATE,
    CF_SPATIAL_VOXELS,
    COLUMN_FAMILIES,
    RocksDBStore,
)


class RocksDBStoreTests(unittest.TestCase):
    def test_column_families_and_json_crud(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RocksDBStore(Path(directory))
            self.assertEqual(
                COLUMN_FAMILIES,
                (
                    CF_SPATIAL_VOXELS,
                    CF_BOREHOLE_TELEMETRY,
                    CF_A2A_CHECKPOINTS,
                    CF_SECURE_STATE,
                ),
            )
            store.put_json(CF_SPATIAL_VOXELS, "voxel:1", {"x": 1, "y": 2, "z": 3})
            store.put_json(CF_BOREHOLE_TELEMETRY, "borehole:1", {"depth": 120.5})
            store.put_json(CF_A2A_CHECKPOINTS, "checkpoint:1", {"agent": "geochemist"})
            store.put_json(CF_SECURE_STATE, "token:1", {"encrypted_value": "value"})

            self.assertEqual(store.get_json(CF_SPATIAL_VOXELS, "voxel:1"), {"x": 1, "y": 2, "z": 3})
            self.assertEqual(list(store.scan_json(CF_BOREHOLE_TELEMETRY, "borehole:"))[0][1], {"depth": 120.5})
            self.assertEqual(store.get_json(CF_A2A_CHECKPOINTS, "checkpoint:1"), {"agent": "geochemist"})
            self.assertEqual(store.get_json(CF_SECURE_STATE, "token:1"), {"encrypted_value": "value"})

            store.delete(CF_SPATIAL_VOXELS, "voxel:1")
            self.assertIsNone(store.get(CF_SPATIAL_VOXELS, "voxel:1"))


if __name__ == "__main__":
    unittest.main()
