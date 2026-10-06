// PointFilters16.cpp — núcleos de filtro ponto a ponto de 16 bits (S5)
// Cada pixel de saída depende só do pixel de entrada; a regra de cada filtro é a de PointFilters.cpp, com os
// parâmetros nas mesmas unidades (0..255 onde lá eram 0..255) e a conta em float arredondada ao nível de 16 bits.

#include "FilterKernels16.hpp"
#include "../../color/HsvConversion.hpp"

#include <algorithm>
#include <cmath>
#include <vector>

namespace aladyn::engine::document::filters {

namespace {

// A tabela de brilho/contraste/gama de 65536 entradas (a de 8 bits tem 256 e custa nada; esta custa 65536 `pow` com
// gama, uns 2 ms). Cada thread guarda a última: uma sequência de composições com os mesmos parâmetros (um traço sob
// uma camada de ajuste) monta a tabela uma vez só.
struct ToneCurve {
    float bright{0.0f};
    float contrast{0.0f};
    float gamma{1.0f};
    std::vector<uint16_t> lut;
};

const std::vector<uint16_t>& toneCurve(float bright, float contrast, float gamma) {
    thread_local ToneCurve cache;
    if (!cache.lut.empty() && cache.bright == bright && cache.contrast == contrast && cache.gamma == gamma) return cache.lut;
    cache.bright = bright;
    cache.contrast = contrast;
    cache.gamma = gamma;
    cache.lut.resize(65536);
    const float contrastFactor = contrast + 1.0f;
    const float invGamma = 1.0f / gamma;
    for (int i = 0; i < 65536; ++i) {
        float v = (static_cast<float>(i) / 65535.0f) + bright;
        v = (v - 0.5f) * contrastFactor + 0.5f;
        v = std::clamp(v, 0.0f, 1.0f);
        if (gamma != 1.0f) v = std::pow(v, invGamma);
        cache.lut[i] = roundChannel16(v * 65535.0f);
    }
    return cache.lut;
}

} // namespace

void applyBrightnessContrast16(const FilterSettings& filter, const FilterRegion& region) {
    const float bright = filter.getParam(0, 0.0f) / 100.0f;
    const float contrast = filter.getParam(1, 0.0f) / 100.0f;
    const float gamma = std::max(0.1f, filter.getParam(2, 1.0f));
    const uint16_t* lut = toneCurve(bright, contrast, gamma).data();
    transformPixels16(region, [lut](utils::ColorRGBA16 p) noexcept { return utils::ColorRGBA16{lut[p.r], lut[p.g], lut[p.b], p.a}; });
}

void applyColorBalance16(const FilterSettings& filter, const FilterRegion& region) {
    // 8 bits: parâmetro * 2,55 níveis de 255; 16 bits: o mesmo deslocamento em níveis de 65535.
    const float rShift = filter.getParam(0, 0.0f) * 655.35f;
    const float gShift = filter.getParam(1, 0.0f) * 655.35f;
    const float bShift = filter.getParam(2, 0.0f) * 655.35f;
    transformPixels16(region, [=](utils::ColorRGBA16 p) noexcept {
        return utils::ColorRGBA16{roundChannel16(static_cast<float>(p.r) + rShift), roundChannel16(static_cast<float>(p.g) + gShift),
                                  roundChannel16(static_cast<float>(p.b) + bShift), p.a};
    });
}

void applyInvertThreshold16(const FilterSettings& filter, const FilterRegion& region) {
    const bool isInvert = filter.getParam(0, 1.0f) > 0.5f;
    // O limiar vem em níveis de 8 bits (padrão 128); o mesmo ponto da escala em 16 bits é x257.
    const uint32_t threshold = static_cast<uint32_t>(filter.getParam(1, 128.0f) * 257.0f);
    if (isInvert) {
        transformPixels16(region, [](utils::ColorRGBA16 p) noexcept {
            return utils::ColorRGBA16{static_cast<uint16_t>(65535 - p.r), static_cast<uint16_t>(65535 - p.g), static_cast<uint16_t>(65535 - p.b), p.a};
        });
        return;
    }
    transformPixels16(region, [threshold](utils::ColorRGBA16 p) noexcept {
        const uint32_t lum = (299u * p.r + 587u * p.g + 114u * p.b) / 1000u;
        const uint16_t v = lum >= threshold ? 65535 : 0;
        return utils::ColorRGBA16{v, v, v, p.a};
    });
}

void applyHueSat16(const FilterSettings& filter, const FilterRegion& region) {
    const float hueShift = filter.getParam(0, 0.0f);
    const float satDelta = filter.getParam(1, 0.0f) / 100.0f;
    const float lightDelta = filter.getParam(2, 0.0f) / 100.0f;
    const bool colorize = filter.getParam(3, 0.0f) > 0.5f;

    if (std::abs(hueShift) < 0.001f && std::abs(satDelta) < 0.001f && std::abs(lightDelta) < 0.001f && !colorize) return;

    transformPixels16(region, [=](utils::ColorRGBA16 p) noexcept {
        float fh, fs, fv;
        color::rgbToHsv(static_cast<float>(p.r) / 65535.0f, static_cast<float>(p.g) / 65535.0f, static_cast<float>(p.b) / 65535.0f, fh, fs, fv);
        if (colorize) {
            fh = std::fmod(std::abs(hueShift), 360.0f);
            fs = std::clamp(0.5f + satDelta, 0.0f, 1.0f);
        } else {
            fh = std::fmod(fh + hueShift + 360.0f, 360.0f);
            fs = std::clamp(fs + satDelta, 0.0f, 1.0f);
        }
        fv = std::clamp(fv + lightDelta, 0.0f, 1.0f);
        float outR, outG, outB;
        color::hsvToRgb(fh, fs, fv, outR, outG, outB);
        return utils::ColorRGBA16{roundChannel16(outR * 65535.0f), roundChannel16(outG * 65535.0f), roundChannel16(outB * 65535.0f), p.a};
    });
}

} // namespace aladyn::engine::document::filters
