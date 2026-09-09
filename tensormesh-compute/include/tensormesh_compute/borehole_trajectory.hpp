#pragma once

#include <vector>

namespace tensormesh::compute {

struct SurveyStation {
    double measured_depth_m{};
    double inclination_deg{};
    double azimuth_deg{};
};

struct TrajectoryPoint3D {
    double measured_depth_m{};
    double easting_m{};
    double northing_m{};
    double true_vertical_depth_m{};
};

std::vector<TrajectoryPoint3D> compute_minimum_curvature_trajectory(
    const std::vector<SurveyStation>& stations);

}