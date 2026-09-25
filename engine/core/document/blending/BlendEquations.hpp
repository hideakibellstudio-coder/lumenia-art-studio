#ifndef ALADYN_ENGINE_BLEND_EQUATIONS_HPP
#define ALADYN_ENGINE_BLEND_EQUATIONS_HPP

#include "LayerBlendMode.hpp"
#include "../../../utils/ColorRGBA.hpp"
#include "../../color/LinearColorSpace.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::document::blending {

// ─── MATEMÁTICA PURA DE MESCLAGEM DE PIXEL (ALPHA OVER + BLEND MODES) ───────

inline utils::ColorRGBA blendPixel(
    utils::ColorRGBA src,
    double layerOpacity,
    utils::ColorRGBA dst,
    LayerBlendMode mode,
    bool linearGamma = true,
    bool deepColor = false
) noexcept {
    if (src.a == 0) return dst;

    if (mode == LayerBlendMode::Normal && layerOpacity == 1.0 && !deepColor) {
        if (src.a == 255) return src;
        if (dst.a == 255 && !linearGamma) {
            const uint32_t sA = src.a;
            const uint32_t invA = 255 - sA;
            return utils::ColorRGBA{
                static_cast<uint8_t>((src.r * sA + dst.r * invA) / 255),
                static_cast<uint8_t>((src.g * sA + dst.g * invA) / 255),
                static_cast<uint8_t>((src.b * sA + dst.b * invA) / 255),
                255
            };
        }
    }

    const double srcA = (static_cast<double>(src.a) / 255.0) * layerOpacity;
    if (srcA <= 0.0) return dst;

    if (mode == LayerBlendMode::Erase) {
        const double dstA = static_cast<double>(dst.a) / 255.0;
        const double newA = std::max(0.0, dstA * (1.0 - srcA));
        return utils::ColorRGBA{dst.r, dst.g, dst.b, static_cast<uint8_t>(std::clamp(newA * 255.0, 0.0, 255.0))};
    }

    if (mode == LayerBlendMode::Normal) {
        if (linearGamma) {
            if (deepColor) {
                return color::blendLinearNormalHighPrecision(src, srcA, dst);
            }
            if (dst.a == 255) {
                return color::blendLinearNormalOpaque(src, static_cast<float>(srcA), dst);
            }
            return color::blendLinearNormal(src, static_cast<float>(srcA), dst);
        }

        // Mistura sRGB direta (compatível com pipelines que mantêm a gama
        // codificada). Em modo Deep Color o cálculo continua em double e a
        // quantização final usa arredondamento, evitando a perda sistemática
        // causada por truncar cada composição intermediária.
        const double dstA = static_cast<double>(dst.a) / 255.0;
        const double outA = srcA + dstA * (1.0 - srcA);
        if (outA <= 0.0) return utils::ColorRGBA{0, 0, 0, 0};
        const double factorSrc = srcA / outA;
        const double factorDst = dstA * (1.0 - srcA) / outA;
        const auto quantize = [deepColor](double value) noexcept -> uint8_t {
            const double scaled = std::clamp(value * 255.0, 0.0, 255.0);
            return static_cast<uint8_t>(deepColor ? std::lround(scaled) : scaled);
        };
        return utils::ColorRGBA{
            quantize((static_cast<double>(src.r) / 255.0) * factorSrc + (static_cast<double>(dst.r) / 255.0) * factorDst),
            quantize((static_cast<double>(src.g) / 255.0) * factorSrc + (static_cast<double>(dst.g) / 255.0) * factorDst),
            quantize((static_cast<double>(src.b) / 255.0) * factorSrc + (static_cast<double>(dst.b) / 255.0) * factorDst),
            quantize(outA)
        };
    }

    const double dstA = static_cast<double>(dst.a) / 255.0;
    const double outA = srcA + dstA * (1.0 - srcA);
    if (outA <= 0.0) return utils::ColorRGBA{0, 0, 0, 0};

    const double sR = static_cast<double>(src.r) / 255.0;
    const double sG = static_cast<double>(src.g) / 255.0;
    const double sB = static_cast<double>(src.b) / 255.0;

    const double dR = static_cast<double>(dst.r) / 255.0;
    const double dG = static_cast<double>(dst.g) / 255.0;
    const double dB = static_cast<double>(dst.b) / 255.0;

    double blendR = sR, blendG = sG, blendB = sB;

    switch (mode) {
        case LayerBlendMode::Multiply:
            blendR = sR * dR;
            blendG = sG * dG;
            blendB = sB * dB;
            break;
        case LayerBlendMode::Screen:
            blendR = 1.0 - (1.0 - sR) * (1.0 - dR);
            blendG = 1.0 - (1.0 - sG) * (1.0 - dG);
            blendB = 1.0 - (1.0 - sB) * (1.0 - dB);
            break;
        case LayerBlendMode::Overlay:
            blendR = (dR < 0.5) ? (2.0 * dR * sR) : (1.0 - 2.0 * (1.0 - dR) * (1.0 - sR));
            blendG = (dG < 0.5) ? (2.0 * dG * sG) : (1.0 - 2.0 * (1.0 - dG) * (1.0 - sG));
            blendB = (dB < 0.5) ? (2.0 * dB * sB) : (1.0 - 2.0 * (1.0 - dB) * (1.0 - sB));
            break;
        case LayerBlendMode::Darken:
            blendR = std::min(sR, dR);
            blendG = std::min(sG, dG);
            blendB = std::min(sB, dB);
            break;
        case LayerBlendMode::Lighten:
            blendR = std::max(sR, dR);
            blendG = std::max(sG, dG);
            blendB = std::max(sB, dB);
            break;
        case LayerBlendMode::ColorDodge:
            blendR = std::min(1.0, dR / (1.0 - sR + 1e-5));
            blendG = std::min(1.0, dG / (1.0 - sG + 1e-5));
            blendB = std::min(1.0, dB / (1.0 - sB + 1e-5));
            break;
        case LayerBlendMode::ColorBurn:
            blendR = 1.0 - std::min(1.0, (1.0 - dR) / (sR + 1e-5));
            blendG = 1.0 - std::min(1.0, (1.0 - dG) / (sG + 1e-5));
            blendB = 1.0 - std::min(1.0, (1.0 - dB) / (sB + 1e-5));
            break;
        case LayerBlendMode::Difference:
            blendR = std::abs(dR - sR);
            blendG = std::abs(dG - sG);
            blendB = std::abs(dB - sB);
            break;
        case LayerBlendMode::Exclusion:
            blendR = dR + sR - 2.0 * dR * sR;
            blendG = dG + sG - 2.0 * dG * sG;
            blendB = dB + sB - 2.0 * dB * sB;
            break;
        case LayerBlendMode::Add:
            blendR = std::min(1.0, dR + sR);
            blendG = std::min(1.0, dG + sG);
            blendB = std::min(1.0, dB + sB);
            break;
        case LayerBlendMode::Normal:
        default:
            blendR = sR; blendG = sG; blendB = sB;
            break;
    }

    // Interpolação Alpha Over
    const double outR = (blendR * srcA + dR * dstA * (1.0 - srcA)) / outA;
    const double outG = (blendG * srcA + dG * dstA * (1.0 - srcA)) / outA;
    const double outB = (blendB * srcA + dB * dstA * (1.0 - srcA)) / outA;

    const auto quantize = [deepColor](double value) noexcept -> uint8_t {
        const double scaled = std::clamp(value * 255.0, 0.0, 255.0);
        return static_cast<uint8_t>(deepColor ? std::lround(scaled) : scaled);
    };
    return utils::ColorRGBA{
        quantize(outR), quantize(outG), quantize(outB), quantize(outA)
    };
}

} // namespace aladyn::engine::document::blending

#endif // ALADYN_ENGINE_BLEND_EQUATIONS_HPP
