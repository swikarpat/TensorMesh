from __future__ import annotations

from typing import Iterable

import numpy as np

from tensormesh.storage import CF_SPATIAL_VOXELS, RocksDBStore

try:
    from tensormesh.compute._tensormesh_compute import (
        compute_spectral_decomposition as _native_spectral_decomposition,
        invert_acoustic_impedance as _native_invert_acoustic_impedance,
    )
except ImportError:  # pragma: no cover - exercised before the native build
    _native_spectral_decomposition = None
    _native_invert_acoustic_impedance = None


def _as_trace(trace: Iterable[float]) -> np.ndarray:
    values = np.asarray(list(trace), dtype=np.float32)
    if values.ndim != 1:
        raise ValueError("trace must be one-dimensional")
    return values


def invert_acoustic_impedance(trace: Iterable[float], z0: float) -> np.ndarray:
    """Estimate post-stack acoustic impedance from reflection coefficients."""
    trace_array = _as_trace(trace)
    if _native_invert_acoustic_impedance is not None:
        return np.asarray(_native_invert_acoustic_impedance(trace_array.tolist(), float(z0)), dtype=np.float32)

    impedance = np.empty_like(trace_array)
    previous = max(float(z0), 0.0)
    for index, sample in enumerate(trace_array):
        reflection = float(np.clip(sample, -0.999, 0.999))
        previous *= (1.0 + reflection) / (1.0 - reflection)
        impedance[index] = previous
    return impedance


def compute_spectral_decomposition(
    trace: Iterable[float],
    freqs: Iterable[float],
    dt: float,
) -> np.ndarray:
    """Convolve a trace with a Morlet wavelet bank and return frequency x time."""
    trace_array = _as_trace(trace)
    frequency_array = np.asarray(list(freqs), dtype=np.float32)
    if frequency_array.ndim != 1:
        raise ValueError("freqs must be one-dimensional")
    if dt <= 0.0:
        raise ValueError("dt must be positive")
    if np.any(frequency_array <= 0.0):
        raise ValueError("target frequencies must be positive")

    if _native_spectral_decomposition is not None:
        native = _native_spectral_decomposition(
            trace_array.tolist(), frequency_array.tolist(), float(dt)
        )
        return np.asarray(native, dtype=np.float32)

    result = np.zeros((len(frequency_array), len(trace_array)), dtype=np.float32)
    for frequency_index, frequency in enumerate(frequency_array):
        sigma = 6.0 / (2.0 * np.pi * float(frequency))
        radius = int(np.ceil(3.0 * sigma / dt))
        normalization = 1.0 / np.sqrt(2.0 * np.pi * sigma * sigma)
        for sample_index in range(len(trace_array)):
            offsets = np.arange(-radius, radius + 1)
            source_indices = sample_index + offsets
            valid = (source_indices >= 0) & (source_indices < len(trace_array))
            times = offsets[valid] * dt
            envelope = np.exp(-0.5 * (times / sigma) ** 2)
            wavelet = normalization * envelope * np.cos(2.0 * np.pi * frequency * times)
            result[frequency_index, sample_index] = np.dot(trace_array[source_indices[valid]], wavelet) / envelope.sum()
    return result


def store_inverted_voxel_trace(store: RocksDBStore, voxel_id: str, trace: Iterable[float]) -> None:
    """Store an inverted float32 voxel trace in the spatial voxel column family."""
    if not voxel_id:
        raise ValueError("voxel_id must not be empty")
    inverted = _as_trace(trace)
    store.put(CF_SPATIAL_VOXELS, f"voxel:{voxel_id}", inverted.tobytes())


def retrieve_inverted_voxel_trace(store: RocksDBStore, voxel_id: str) -> np.ndarray | None:
    """Retrieve a stored float32 voxel trace, or None when it is absent."""
    value = store.get(CF_SPATIAL_VOXELS, f"voxel:{voxel_id}")
    if value is None:
        return None
    if len(value) % np.dtype(np.float32).itemsize != 0:
        raise ValueError("stored voxel trace has invalid float32 alignment")
    return np.frombuffer(value, dtype=np.float32).copy()
