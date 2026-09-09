#include "tensormesh_compute/spatial_morton.hpp"

namespace tensormesh::compute {
namespace {

constexpr std::uint32_t kCoordinateMask = (1u << 21u) - 1u;

std::uint64_t spread(std::uint32_t value) {
    std::uint64_t result = 0;
    for (std::uint32_t bit = 0; bit < 21; ++bit) {
        result |= static_cast<std::uint64_t>((value >> bit) & 1u) << (bit * 3u);
    }
    return result;
}

std::uint32_t compact(std::uint64_t value) {
    std::uint32_t result = 0;
    for (std::uint32_t bit = 0; bit < 21; ++bit) {
        result |= static_cast<std::uint32_t>((value >> (bit * 3u)) & 1ull) << bit;
    }
    return result;
}

}

std::uint64_t encode_morton_3d(std::uint32_t x, std::uint32_t y, std::uint32_t z) {
    return spread(x & kCoordinateMask) | (spread(y & kCoordinateMask) << 1u) |
           (spread(z & kCoordinateMask) << 2u);
}

void decode_morton_3d(std::uint64_t code, std::uint32_t& x, std::uint32_t& y, std::uint32_t& z) {
    x = compact(code);
    y = compact(code >> 1u);
    z = compact(code >> 2u);
}

}