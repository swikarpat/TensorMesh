#include "tensormesh_compute/acoustic_impedance.hpp"
#include "tensormesh_compute/spectral_decomposition.hpp"
#include "tensormesh_compute/spatial_morton.hpp"
#include "tensormesh_compute/borehole_trajectory.hpp"

#include <cassert>
#include <cmath>
#include <vector>

int main() {
    const std::vector<float> trace{0.1f, -0.05f, 0.0f, 0.2f};
    const auto impedance = tensormesh::compute::invert_acoustic_impedance(trace, 2000.0f);
    assert(impedance.size() == trace.size());
    assert(std::abs(impedance[0] - 2444.4443f) < 0.1f);
    assert(std::isfinite(impedance.back()));

    const auto spectrum = tensormesh::compute::compute_spectral_decomposition(
        std::vector<float>{0.0f, 1.0f, 0.0f, -1.0f, 0.0f},
        std::vector<float>{10.0f, 40.0f, 90.0f},
        0.001f);
    assert(spectrum.size() == 3);
    assert(spectrum[0].size() == 5);
    for (const auto& band : spectrum) {
        for (float value : band) {
            assert(std::isfinite(value));
        }
    }
    const auto morton = tensormesh::compute::encode_morton_3d(17, 23, 31);
    std::uint32_t x;
    std::uint32_t y;
    std::uint32_t z;
    tensormesh::compute::decode_morton_3d(morton, x, y, z);
    assert(x == 17 && y == 23 && z == 31);
    const auto trajectory = tensormesh::compute::compute_minimum_curvature_trajectory({
        {0.0, 0.0, 0.0}, {100.0, 0.0, 0.0}, {200.0, 90.0, 0.0}});
    assert(trajectory.size() == 3);
    assert(std::abs(trajectory[1].true_vertical_depth_m - 100.0) < 1e-6);
    assert(trajectory[2].northing_m > 0.0);
    return 0;
}