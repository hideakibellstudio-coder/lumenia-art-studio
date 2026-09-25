#ifndef ALADYN_ENGINE_SIMD_SPAN_BLENDER_HPP
#define ALADYN_ENGINE_SIMD_SPAN_BLENDER_HPP

#include "../../utils/ColorRGBA.hpp"
#include "../color/LinearColorSpace.hpp"
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <algorithm>

#if defined(__AVX2__)
#include <immintrin.h>
#endif

namespace aladyn::engine::raster {

class SimdSpanBlender {
public:
    // Escrita vetorial ultrarrápida para miolo sólido opaco (AVX2: 8 pixels por instrução)
    static inline void blendSpanSolidOpaque(
        utils::ColorRGBA* dst,
        size_t count,
        utils::ColorRGBA srcColor
    ) noexcept {
        if (count == 0 || dst == nullptr) return;

        size_t i = 0;

#if defined(__AVX2__)
        const uint32_t c32 = (static_cast<uint32_t>(srcColor.a) << 24) |
                             (static_cast<uint32_t>(srcColor.b) << 16) |
                             (static_cast<uint32_t>(srcColor.g) << 8)  |
                              static_cast<uint32_t>(srcColor.r);
        const __m256i val256 = _mm256_set1_epi32(static_cast<int>(c32));
        for (; i + 8 <= count; i += 8) {
            _mm256_storeu_si256(reinterpret_cast<__m256i*>(dst + i), val256);
        }
#endif

        for (; i < count; ++i) {
            dst[i] = srcColor;
        }
    }

    // Mesclagem linear rápida de trecho contínuo quando dst.a == 255
    static inline void blendSpanLinearNormalOpaque(
        utils::ColorRGBA* dst,
        size_t count,
        utils::ColorRGBA srcColor,
        float srcA
    ) noexcept {
        if (count == 0 || dst == nullptr || srcA <= 0.0f) return;

        if (srcA >= 0.999f) {
            blendSpanSolidOpaque(dst, count, srcColor);
            return;
        }

        size_t i = 0;
        for (; i + 4 <= count; i += 4) {
            dst[i + 0] = color::blendLinearNormalOpaque(srcColor, srcA, dst[i + 0]);
            dst[i + 1] = color::blendLinearNormalOpaque(srcColor, srcA, dst[i + 1]);
            dst[i + 2] = color::blendLinearNormalOpaque(srcColor, srcA, dst[i + 2]);
            dst[i + 3] = color::blendLinearNormalOpaque(srcColor, srcA, dst[i + 3]);
        }
        for (; i < count; ++i) {
            dst[i] = color::blendLinearNormalOpaque(srcColor, srcA, dst[i]);
        }
    }

    // Mesclagem linear geral de trecho contínuo (suporta transparência de destino)
    static inline void blendSpanLinearNormal(
        utils::ColorRGBA* dst,
        size_t count,
        utils::ColorRGBA srcColor,
        float srcA
    ) noexcept {
        if (count == 0 || dst == nullptr || srcA <= 0.0f) return;

        size_t i = 0;
        for (; i + 4 <= count; i += 4) {
            dst[i + 0] = color::blendLinearNormal(srcColor, srcA, dst[i + 0]);
            dst[i + 1] = color::blendLinearNormal(srcColor, srcA, dst[i + 1]);
            dst[i + 2] = color::blendLinearNormal(srcColor, srcA, dst[i + 2]);
            dst[i + 3] = color::blendLinearNormal(srcColor, srcA, dst[i + 3]);
        }
        for (; i < count; ++i) {
            dst[i] = color::blendLinearNormal(srcColor, srcA, dst[i]);
        }
    }
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_SIMD_SPAN_BLENDER_HPP
