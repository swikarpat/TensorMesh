#include "tensormesh_compute/spectral_decomposition.hpp"

#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace tensormesh::compute {

namespace {
constexpr float kPi = 3.14159265358979323846f;
constexpr float kMorletCycles = 6.0f;
}

std::vector<std::vector<float>> compute_spectral_decomposition(
    const std::vector<float>& trace,
    const std::vector<float>& freqs,
    float dt) {
    if (dt <= 0.0f) {
        throw std::invalid_argument("dt must be positive");
    }

    std::vector<std::vector<float>> result(freqs.size(), std::vector<float>(trace.size(), 0.0f));
    for (std::size_t frequency_index = 0; frequency_index < freqs.size(); ++frequency_index) {
        const float frequency = freqs[frequency_index];
        if (frequency <= 0.0f) {
            throw std::invalid_argument("target frequencies must be positive");
        }
        const float sigma = kMorletCycles / (2.0f * kPi * frequency);
        const int radius = static_cast<int>(std::ceil(3.0f * sigma / dt));
        const float normalization = 1.0f / std::sqrt(2.0f * kPi * sigma * sigma);

        for (std::size_t sample_index = 0; sample_index < trace.size(); ++sample_index) {
            float sum = 0.0f;
            float weight_sum = 0.0f;
            const int center = static_cast<int>(sample_index);
            for (int offset = -radius; offset <= radius; ++offset) {
                const int source_index = center + offset;
                if (source_index < 0 || source_index >= static_cast<int>(trace.size())) {
                    continue;
                }
                const float time = static_cast<float>(offset) * dt;
                const float envelope = std::exp(-0.5f * (time / sigma) * (time / sigma));
                const float wavelet = normalization * envelope * std::cos(2.0f * kPi * frequency * time);
                sum += trace[static_cast<std::size_t>(source_index)] * wavelet;
                weight_sum += envelope;
            }
            result[frequency_index][sample_index] = weight_sum > 0.0f ? sum / weight_sum : 0.0f;
        }
    }
    return result;
}

}