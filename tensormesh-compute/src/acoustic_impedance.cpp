#include "tensormesh_compute/acoustic_impedance.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>

#if defined(__ARM_NEON) || defined(__aarch64__)
#include <arm_neon.h>
#define TENSORMESH_NEON 1
#endif

namespace tensormesh::compute {

namespace {

float safe_reflection(float sample) {
    return std::clamp(sample, -0.999f, 0.999f);
}

}  // namespace

std::vector<float> invert_acoustic_impedance(const std::vector<float>& trace, float z0) {
    std::vector<float> impedance(trace.size());
    if (trace.empty()) {
        return impedance;
    }

    float previous = std::max(z0, 0.0f);
    std::size_t index = 0;

#if defined(TENSORMESH_NEON)
    // NEON vectorizes the reflection-to-impedance factors; the recursive state
    // is carried lane-by-lane because each sample depends on the previous one.
    const float32x4_t one = vdupq_n_f32(1.0f);
    for (; index + 4 <= trace.size(); index += 4) {
        const float32x4_t samples = vld1q_f32(trace.data() + index);
        const float32x4_t clipped = vmaxq_f32(vminq_f32(samples, vdupq_n_f32(0.999f)), vdupq_n_f32(-0.999f));
        const float32x4_t numerator = vaddq_f32(one, clipped);
        const float32x4_t denominator = vsubq_f32(one, clipped);
    #if defined(__aarch64__)
        const float32x4_t refined = vdivq_f32(numerator, denominator);
        const float32x4_t factors = refined;
    #else
        const float32x4_t reciprocal = vrecpeq_f32(denominator);
        const float32x4_t refined_once = vmulq_f32(reciprocal, vrecpsq_f32(denominator, reciprocal));
        const float32x4_t refined = vmulq_f32(refined_once, vrecpsq_f32(denominator, refined_once));
        const float32x4_t factors = vmulq_f32(numerator, refined);
    #endif
        alignas(16) float factor_values[4];
        vst1q_f32(factor_values, factors);
        for (float factor : factor_values) {
            previous *= factor;
            impedance[index++] = previous;
        }
        index -= 4;
    }
#endif

    for (; index < trace.size(); ++index) {
        const float reflection = safe_reflection(trace[index]);
        previous *= (1.0f + reflection) / (1.0f - reflection);
        impedance[index] = previous;
    }
    return impedance;
}

}