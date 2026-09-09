#include "tensormesh_compute/borehole_trajectory.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace tensormesh::compute {
namespace {

constexpr double kPi = 3.14159265358979323846;
double radians(double degrees) { return degrees * kPi / 180.0; }

}

std::vector<TrajectoryPoint3D> compute_minimum_curvature_trajectory(
    const std::vector<SurveyStation>& stations) {
    if (stations.empty()) {
        return {};
    }

    std::vector<TrajectoryPoint3D> trajectory;
    trajectory.reserve(stations.size());
    trajectory.push_back({stations.front().measured_depth_m, 0.0, 0.0, 0.0});

    for (std::size_t index = 1; index < stations.size(); ++index) {
        const auto& previous = stations[index - 1];
        const auto& current = stations[index];
        const double delta_depth = current.measured_depth_m - previous.measured_depth_m;
        if (delta_depth < 0.0) {
            throw std::invalid_argument("survey measured depths must be non-decreasing");
        }

        const double inclination_1 = radians(previous.inclination_deg);
        const double inclination_2 = radians(current.inclination_deg);
        const double azimuth_1 = radians(previous.azimuth_deg);
        const double azimuth_2 = radians(current.azimuth_deg);
        const double dogleg = std::acos(std::clamp(
            std::cos(inclination_1) * std::cos(inclination_2) +
                std::sin(inclination_1) * std::sin(inclination_2) * std::cos(azimuth_2 - azimuth_1),
            -1.0, 1.0));
        const double ratio_factor = dogleg < 1e-12 ? 1.0 : 2.0 / dogleg * std::tan(dogleg / 2.0);
        const double easting_delta = delta_depth / 2.0 *
            (std::sin(inclination_1) * std::sin(azimuth_1) +
             std::sin(inclination_2) * std::sin(azimuth_2)) * ratio_factor;
        const double northing_delta = delta_depth / 2.0 *
            (std::sin(inclination_1) * std::cos(azimuth_1) +
             std::sin(inclination_2) * std::cos(azimuth_2)) * ratio_factor;
        const double tvd_delta = delta_depth / 2.0 *
            (std::cos(inclination_1) + std::cos(inclination_2)) * ratio_factor;
        const auto& previous_point = trajectory.back();
        trajectory.push_back({
            current.measured_depth_m,
            previous_point.easting_m + easting_delta,
            previous_point.northing_m + northing_delta,
            previous_point.true_vertical_depth_m + tvd_delta,
        });
    }
    return trajectory;
}

}