#ifndef ALADYN_ENGINE_BLEND_EQUATIONS_HPP
#define ALADYN_ENGINE_BLEND_EQUATIONS_HPP

#include "../Layer.hpp"
#include "../../raster/Dab.hpp"
#include "../../color/LinearColorSpace.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::document::blending {

// ─── CONVERSÃO DE CORES RGB <-> HSV ─────────────────────────────────────────

inline void rgbToHsv(float r, float g, float b, float& h, float& s, float& v) noexcept {
    const float minVal = std::min({r, g, b});
    const float maxVal = std::max({r, g, b});
    const float delta = maxVal - minVal;
    v = maxVal;
    if (maxVal == 0.0f || delta == 0.0f) {
        s = 0.0f;
        h = 0.0f;
        return;
    }
    s = delta / maxVal;
    if (r == maxVal) h = (g - b) / delta;
    else if (g == maxVal) h = 2.0f + (b - r) / delta;
    else h = 4.0f + (r - g) / delta;
    h *= 60.0f;
    if (h < 0.0f) h += 360.0f;
}

inline void hsvToRgb(float h, float s, float v, float& r, float& g, float& b) noexcept {
    if (s == 0.0f) {
        r = g = b = v;
        return;
    }
    h = std::fmod(h, 360.0f);
    if (h < 0.0f) h += 360.0f;
    const float c = v * s;
    const float x = c * (1.0f - std::abs(std::fmod(h / 60.0f, 2.0f) - 1.0f));
    const float m = v - c;
    float r1 = 0, g1 = 0, b1 = 0;
    if (h < 60.0f)       { r1 = c; g1 = x; b1 = 0; }
    else if (h < 120.0f) { r1 = x; g1 = c; b1 = 0; }
    else if (h < 180.0f) { r1 = 0; g1 = c; b1 = x; }
    else if (h < 240.0f) { r1 = 0; g1 = x; b1 = c; }
    else if (h < 300.0f) { r1 = x; g1 = 0; b1 = c; }
    else                 { r1 = c; g1 = 0; b1 = x; }
    r = r1 + m;
    g = g1 + m;
    b = b1 + m;
}

// ─── MATEMÁTICA PURA DE MESCLAGEM DE PIXEL (ALPHA OVER + BLEND MODES) ───────

inline raster::ColorRGBA blendPixel(
    raster::ColorRGBA src,
    double layerOpacity,
    raster::ColorRGBA dst,
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
            return raster::ColorRGBA{
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
        return raster::ColorRGBA{dst.r, dst.g, dst.b, static_cast<uint8_t>(std::clamp(newA * 255.0, 0.0, 255.0))};
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
        if (outA <= 0.0) return raster::ColorRGBA{0, 0, 0, 0};
        const double factorSrc = srcA / outA;
        const double factorDst = dstA * (1.0 - srcA) / outA;
        const auto quantize = [deepColor](double value) noexcept -> uint8_t {
            const double scaled = std::clamp(value * 255.0, 0.0, 255.0);
            return static_cast<uint8_t>(deepColor ? std::lround(scaled) : scaled);
        };
        return raster::ColorRGBA{
            quantize((static_cast<double>(src.r) / 255.0) * factorSrc + (static_cast<double>(dst.r) / 255.0) * factorDst),
            quantize((static_cast<double>(src.g) / 255.0) * factorSrc + (static_cast<double>(dst.g) / 255.0) * factorDst),
            quantize((static_cast<double>(src.b) / 255.0) * factorSrc + (static_cast<double>(dst.b) / 255.0) * factorDst),
            quantize(outA)
        };
    }

    const double dstA = static_cast<double>(dst.a) / 255.0;
    const double outA = srcA + dstA * (1.0 - srcA);
    if (outA <= 0.0) return raster::ColorRGBA{0, 0, 0, 0};

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
    return raster::ColorRGBA{
        quantize(outR), quantize(outG), quantize(outB), quantize(outA)
    };
}

} // namespace aladyn::engine::document::blending

#endif // ALADYN_ENGINE_BLEND_EQUATIONS_HPP
