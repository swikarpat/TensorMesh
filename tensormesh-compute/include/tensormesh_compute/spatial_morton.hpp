#pragma once

#include <cstdint>

namespace tensormesh::compute {

std::uint64_t encode_morton_3d(std::uint32_t x, std::uint32_t y, std::uint32_t z);
void decode_morton_3d(std::uint64_t code, std::uint32_t& x, std::uint32_t& y, std::uint32_t& z);

}