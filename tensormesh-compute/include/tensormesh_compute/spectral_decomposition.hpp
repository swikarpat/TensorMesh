#pragma once

#include <vector>

namespace tensormesh::compute {

std::vector<std::vector<float>> compute_spectral_decomposition(
    const std::vector<float>& trace,
    const std::vector<float>& freqs,
    float dt);

}