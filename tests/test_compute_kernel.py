import tempfile
import unittest
from pathlib import Path

import numpy as np

import tensormesh.compute.inversion as inversion
from tensormesh.compute import (
    compute_spectral_decomposition,
    invert_acoustic_impedance,
    retrieve_inverted_voxel_trace,
    store_inverted_voxel_trace,
)
from tensormesh.storage import RocksDBStore


class ComputeKernelTests(unittest.TestCase):
    def test_acoustic_impedance_recursive_accuracy(self):
        trace = np.array([0.1, -0.05, 0.0], dtype=np.float32)
        result = invert_acoustic_impedance(trace, 2000.0)
        expected = np.array([2444.4443, 2211.6401, 2211.6401], dtype=np.float32)
        np.testing.assert_allclose(result, expected, rtol=1e-4, atol=0.1)

    def test_kernel_boundaries_and_validation(self):
        self.assertEqual(invert_acoustic_impedance([], 1000.0).size, 0)
        np.testing.assert_allclose(invert_acoustic_impedance([1.5], 1000.0), np.array([1_999_000.0], dtype=np.float32), rtol=2e-5)
        self.assertEqual(compute_spectral_decomposition([], [10.0], 0.001).shape, (1, 0))
        with self.assertRaises(ValueError):
            compute_spectral_decomposition([1.0], [10.0], 0.0)
        with self.assertRaises(ValueError):
            compute_spectral_decomposition([1.0], [0.0], 0.001)

    def test_spectral_decomposition_shape_and_finiteness(self):
        result = compute_spectral_decomposition([0.0, 1.0, 0.0, -1.0, 0.0], [10.0, 40.0, 90.0], 0.001)
        self.assertEqual(result.shape, (3, 5))
        self.assertTrue(np.isfinite(result).all())
        self.assertGreater(float(np.abs(result).sum()), 0.0)

    def test_numpy_fallback_matches_native_impedance(self):
        native = invert_acoustic_impedance([0.1, -0.05, 0.02], 2000.0)
        original = inversion._native_invert_acoustic_impedance
        inversion._native_invert_acoustic_impedance = None
        try:
            fallback = inversion.invert_acoustic_impedance([0.1, -0.05, 0.02], 2000.0)
        finally:
            inversion._native_invert_acoustic_impedance = original
        np.testing.assert_allclose(fallback, native, rtol=1e-6, atol=0.1)

    def test_inverted_voxel_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RocksDBStore(Path(directory))
            trace = invert_acoustic_impedance([0.05, -0.02, 0.01], 1800.0)
            store_inverted_voxel_trace(store, "x10-y20-z30", trace)
            restored = retrieve_inverted_voxel_trace(store, "x10-y20-z30")
            np.testing.assert_array_equal(restored, trace)
            self.assertIsNone(retrieve_inverted_voxel_trace(store, "missing"))


if __name__ == "__main__":
    unittest.main()
