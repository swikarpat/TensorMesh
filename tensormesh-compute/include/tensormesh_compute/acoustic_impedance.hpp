#pragma once

#include <vector>

namespace tensormesh::compute {

std::vector<float> invert_acoustic_impedance(const std::vector<float>& trace, float z0);

}