#include "tensormesh_compute/acoustic_impedance.hpp"
#include "tensormesh_compute/spectral_decomposition.hpp"

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
    return 0;
}