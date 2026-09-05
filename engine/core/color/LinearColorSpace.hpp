#ifndef ALADYN_ENGINE_LINEAR_COLOR_SPACE_HPP
#define ALADYN_ENGINE_LINEAR_COLOR_SPACE_HPP

#include "../raster/Dab.hpp"
#include <cmath>
#include <algorithm>
#include <cstdint>

namespace aladyn::engine::color {

struct LinearLutTables {
    float sRGB_to_Linear[256];
    uint8_t Linear_to_sRGB[4096];

    LinearLutTables() noexcept {
        for (int i = 0; i < 256; ++i) {
            const float s = static_cast<float>(i) / 255.0f;
            if (s <= 0.04045f) {
                sRGB_to_Linear[i] = s / 12.92f;
            } else {
                sRGB_to_Linear[i] = std::pow((s + 0.055f) / 1.055f, 2.4f);
            }
        }
        for (int i = 0; i < 4096; ++i) {
            const float l = static_cast<float>(i) / 4095.0f;
            float s;
            if (l <= 0.0031308f) {
                s = l * 12.92f;
            } else {
                s = 1.055f * std::pow(l, 1.0f / 2.4f) - 0.055f;
            }
            const int val = static_cast<int>(s * 255.0f + 0.5f);
            Linear_to_sRGB[i] = static_cast<uint8_t>(std::clamp(val, 0, 255));
        }
    }
};

inline const LinearLutTables& getLinearLutTables() noexcept {
    static const LinearLutTables tables;
    return tables;
}

inline float sRGBToLinear(uint8_t c) noexcept {
    return getLinearLutTables().sRGB_to_Linear[c];
}

inline uint8_t linearToSRGB(float l) noexcept {
    const int idx = std::clamp(static_cast<int>(l * 4095.0f + 0.5f), 0, 4095);
    return getLinearLutTables().Linear_to_sRGB[idx];
}

inline raster::ColorRGBA blendLinearNormal(
    raster::ColorRGBA src,
    float srcA,
    raster::ColorRGBA dst
) noexcept {
    if (srcA <= 0.0f) return dst;
    if (dst.a == 0) {
        return raster::ColorRGBA{
            src.r, src.g, src.b,
            static_cast<uint8_t>(std::clamp(srcA * 255.0f + 0.5f, 0.0f, 255.0f))
        };
    }

    const float dstA = static_cast<float>(dst.a) / 255.0f;
    const float outA = srcA + dstA * (1.0f - srcA);
    if (outA <= 0.0f) return raster::ColorRGBA{0, 0, 0, 0};

    const float sR = sRGBToLinear(src.r);
    const float sG = sRGBToLinear(src.g);
    const float sB = sRGBToLinear(src.b);

    const float dR = sRGBToLinear(dst.r);
    const float dG = sRGBToLinear(dst.g);
    const float dB = sRGBToLinear(dst.b);

    const float invOutA = 1.0f / outA;
    const float factorSrc = srcA * invOutA;
    const float factorDst = dstA * (1.0f - srcA) * invOutA;

    const float outLinR = sR * factorSrc + dR * factorDst;
    const float outLinG = sG * factorSrc + dG * factorDst;
    const float outLinB = sB * factorSrc + dB * factorDst;

    return raster::ColorRGBA{
        linearToSRGB(outLinR),
        linearToSRGB(outLinG),
        linearToSRGB(outLinB),
        static_cast<uint8_t>(std::clamp(outA * 255.0f + 0.5f, 0.0f, 255.0f))
    };
}

inline raster::ColorRGBA blendLinearNormalOpaque(
    raster::ColorRGBA src,
    float srcA,
    raster::ColorRGBA dst
) noexcept {
    if (srcA <= 0.0f) return dst;
    if (srcA >= 1.0f) return raster::ColorRGBA{src.r, src.g, src.b, 255};

    const float sR = sRGBToLinear(src.r);
    const float sG = sRGBToLinear(src.g);
    const float sB = sRGBToLinear(src.b);

    const float dR = sRGBToLinear(dst.r);
    const float dG = sRGBToLinear(dst.g);
    const float dB = sRGBToLinear(dst.b);

    const float invSrcA = 1.0f - srcA;
    const float outLinR = sR * srcA + dR * invSrcA;
    const float outLinG = sG * srcA + dG * invSrcA;
    const float outLinB = sB * srcA + dB * invSrcA;

    return raster::ColorRGBA{
        linearToSRGB(outLinR),
        linearToSRGB(outLinG),
        linearToSRGB(outLinB),
        255
    };
}

} // namespace aladyn::engine::color

#endif // ALADYN_ENGINE_LINEAR_COLOR_SPACE_HPP
