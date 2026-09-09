from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from tensormesh.compute._tensormesh_compute import (
    SurveyStation,
    compute_minimum_curvature_trajectory as _native_trajectory,
    decode_morton_3d,
    encode_morton_3d,
)


def compute_minimum_curvature_trajectory(
    stations: Iterable[SurveyStation | dict[str, Any]],
) -> list[Any]:
    """Convert measured-depth directional surveys into true 3D points."""
    normalized = [
        station
        if isinstance(station, SurveyStation)
        else SurveyStation(
            float(station["measured_depth_m"]),
            float(station["inclination_deg"]),
            float(station["azimuth_deg"]),
        )
        for station in stations
    ]
    return list(_native_trajectory(normalized))