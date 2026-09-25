// PointFilters.cpp — nucleos de filtro ponto-a-ponto
// Cada pixel de saida depende apenas do pixel de entrada correspondente.
//
// Corpos extraidos SEM alteracao de FilterApplier.cpp (fatiamento por linha,
// apenas desindentados em 4 espacos). Nenhuma expressao foi reescrita.

#include "FilterKernels.hpp"
#include "../../color/HsvConversion.hpp"

#include <algorithm>
#include <cmath>
#include <vector>

namespace aladyn::engine::document::filters {

void applyBrightnessContrast(const FilterSettings& filter, const FilterRegion& region) {
    uint8_t* ptr = region.ptr;
    [[maybe_unused]] const int w = region.w;
    [[maybe_unused]] const int h = region.h;
    [[maybe_unused]] const int startX = region.startX;
    [[maybe_unused]] const int endX = region.endX;
    [[maybe_unused]] const int startY = region.startY;
    [[maybe_unused]] const int endY = region.endY;
    [[maybe_unused]] const double opacity = region.opacity;
    [[maybe_unused]] const bool isFullOpacity = region.isFullOpacity;

    const float bright = filter.getParam(0, 0.0f) / 100.0f;
    const float contrast = filter.getParam(1, 0.0f) / 100.0f;
    const float gamma = std::max(0.1f, filter.getParam(2, 1.0f));
    const float contrastFactor = contrast + 1.0f;
    const float invGamma = 1.0f / gamma;

    // OTIMIZAÇÃO 700x: Look-Up Table (LUT) de 256 bytes para eliminar 36 milhões de chamadas a std::pow por frame
    uint8_t lut[256];
    for (int i = 0; i < 256; ++i) {
        float v = (i / 255.0f) + bright;
        v = (v - 0.5f) * contrastFactor + 0.5f;
        v = std::clamp(v, 0.0f, 1.0f);
        if (gamma != 1.0f) {
            v = std::pow(v, invGamma);
        }
        lut[i] = static_cast<uint8_t>(std::clamp(v * 255.0f, 0.0f, 255.0f));
    }

    #pragma omp parallel for schedule(static) if((endY - startY) > 32)
    for (int y = startY; y <= endY; ++y) {
        uint32_t* row32 = reinterpret_cast<uint32_t*>(ptr + static_cast<size_t>(y) * w * 4);
        if (isFullOpacity) {
            for (int x = startX; x <= endX; ++x) {
                uint32_t p = row32[x];
                uint32_t a = p & 0xFF000000;
                if (a == 0) continue;
                uint32_t r = lut[p & 0xFF];
                uint32_t g = lut[(p >> 8) & 0xFF];
                uint32_t b = lut[(p >> 16) & 0xFF];
                row32[x] = a | (b << 16) | (g << 8) | r;
            }
        } else {
            const uint32_t opInt = static_cast<uint32_t>(opacity * 256.0f);
            const uint32_t invOpInt = 256 - opInt;
            for (int x = startX; x <= endX; ++x) {
                uint32_t p = row32[x];
                uint32_t a = p & 0xFF000000;
                if (a == 0) continue;
                uint32_t sR = lut[p & 0xFF];
                uint32_t sG = lut[(p >> 8) & 0xFF];
                uint32_t sB = lut[(p >> 16) & 0xFF];
                uint32_t dR = p & 0xFF;
                uint32_t dG = (p >> 8) & 0xFF;
                uint32_t dB = (p >> 16) & 0xFF;
                uint32_t finalR = (dR * invOpInt + sR * opInt) >> 8;
                uint32_t finalG = (dG * invOpInt + sG * opInt) >> 8;
                uint32_t finalB = (dB * invOpInt + sB * opInt) >> 8;
                row32[x] = a | (finalB << 16) | (finalG << 8) | finalR;
            }
        }
    }
}

void applyColorBalance(const FilterSettings& filter, const FilterRegion& region) {
    uint8_t* ptr = region.ptr;
    [[maybe_unused]] const int w = region.w;
    [[maybe_unused]] const int h = region.h;
    [[maybe_unused]] const int startX = region.startX;
    [[maybe_unused]] const int endX = region.endX;
    [[maybe_unused]] const int startY = region.startY;
    [[maybe_unused]] const int endY = region.endY;
    [[maybe_unused]] const double opacity = region.opacity;
    [[maybe_unused]] const bool isFullOpacity = region.isFullOpacity;

    const float rShift = filter.getParam(0, 0.0f) * 2.55f;
    const float gShift = filter.getParam(1, 0.0f) * 2.55f;
    const float bShift = filter.getParam(2, 0.0f) * 2.55f;

    uint8_t lutR[256], lutG[256], lutB[256];
    for (int i = 0; i < 256; ++i) {
        lutR[i] = static_cast<uint8_t>(std::clamp(i + rShift, 0.0f, 255.0f));
        lutG[i] = static_cast<uint8_t>(std::clamp(i + gShift, 0.0f, 255.0f));
        lutB[i] = static_cast<uint8_t>(std::clamp(i + bShift, 0.0f, 255.0f));
    }

    #pragma omp parallel for schedule(static) if((endY - startY) > 32)
    for (int y = startY; y <= endY; ++y) {
        uint32_t* row32 = reinterpret_cast<uint32_t*>(ptr + static_cast<size_t>(y) * w * 4);
        if (isFullOpacity) {
            for (int x = startX; x <= endX; ++x) {
                uint32_t p = row32[x];
                uint32_t a = p & 0xFF000000;
                if (a == 0) continue;
                uint32_t r = lutR[p & 0xFF];
                uint32_t g = lutG[(p >> 8) & 0xFF];
                uint32_t b = lutB[(p >> 16) & 0xFF];
                row32[x] = a | (b << 16) | (g << 8) | r;
            }
        } else {
            const uint32_t opInt = static_cast<uint32_t>(opacity * 256.0f);
            const uint32_t invOpInt = 256 - opInt;
            for (int x = startX; x <= endX; ++x) {
                uint32_t p = row32[x];
                uint32_t a = p & 0xFF000000;
                if (a == 0) continue;
                uint32_t sR = lutR[p & 0xFF];
                uint32_t sG = lutG[(p >> 8) & 0xFF];
                uint32_t sB = lutB[(p >> 16) & 0xFF];
                uint32_t dR = p & 0xFF;
                uint32_t dG = (p >> 8) & 0xFF;
                uint32_t dB = (p >> 16) & 0xFF;
                uint32_t finalR = (dR * invOpInt + sR * opInt) >> 8;
                uint32_t finalG = (dG * invOpInt + sG * opInt) >> 8;
                uint32_t finalB = (dB * invOpInt + sB * opInt) >> 8;
                row32[x] = a | (finalB << 16) | (finalG << 8) | finalR;
            }
        }
    }
}

void applyInvertThreshold(const FilterSettings& filter, const FilterRegion& region) {
    uint8_t* ptr = region.ptr;
    [[maybe_unused]] const int w = region.w;
    [[maybe_unused]] const int h = region.h;
    [[maybe_unused]] const int startX = region.startX;
    [[maybe_unused]] const int endX = region.endX;
    [[maybe_unused]] const int startY = region.startY;
    [[maybe_unused]] const int endY = region.endY;
    [[maybe_unused]] const double opacity = region.opacity;
    [[maybe_unused]] const bool isFullOpacity = region.isFullOpacity;

    const bool isInvert = filter.getParam(0, 1.0f) > 0.5f;
    const float threshold = filter.getParam(1, 128.0f);

    uint8_t lut[256];
    if (isInvert) {
        for (int i = 0; i < 256; ++i) lut[i] = static_cast<uint8_t>(255 - i);
    }

    #pragma omp parallel for schedule(static) if((endY - startY) > 32)
    for (int y = startY; y <= endY; ++y) {
        uint32_t* row32 = reinterpret_cast<uint32_t*>(ptr + static_cast<size_t>(y) * w * 4);
        if (isFullOpacity) {
            for (int x = startX; x <= endX; ++x) {
                uint32_t p = row32[x];
                uint32_t a = p & 0xFF000000;
                if (a == 0) continue;
                uint32_t finalR, finalG, finalB;
                if (isInvert) {
                    finalR = lut[p & 0xFF];
                    finalG = lut[(p >> 8) & 0xFF];
                    finalB = lut[(p >> 16) & 0xFF];
                } else {
                    uint32_t lum = (299 * (p & 0xFF) + 587 * ((p >> 8) & 0xFF) + 114 * ((p >> 16) & 0xFF)) / 1000;
                    uint32_t v = (lum >= static_cast<uint32_t>(threshold)) ? 255 : 0;
                    finalR = finalG = finalB = v;
                }
                row32[x] = a | (finalB << 16) | (finalG << 8) | finalR;
            }
        } else {
            const uint32_t opInt = static_cast<uint32_t>(opacity * 256.0f);
            const uint32_t invOpInt = 256 - opInt;
            for (int x = startX; x <= endX; ++x) {
                uint32_t p = row32[x];
                uint32_t a = p & 0xFF000000;
                if (a == 0) continue;
                uint32_t sR, sG, sB;
                if (isInvert) {
                    sR = lut[p & 0xFF];
                    sG = lut[(p >> 8) & 0xFF];
                    sB = lut[(p >> 16) & 0xFF];
                } else {
                    uint32_t lum = (299 * (p & 0xFF) + 587 * ((p >> 8) & 0xFF) + 114 * ((p >> 16) & 0xFF)) / 1000;
                    uint32_t v = (lum >= static_cast<uint32_t>(threshold)) ? 255 : 0;
                    sR = sG = sB = v;
                }
                uint32_t dR = p & 0xFF;
                uint32_t dG = (p >> 8) & 0xFF;
                uint32_t dB = (p >> 16) & 0xFF;
                uint32_t finalR = (dR * invOpInt + sR * opInt) >> 8;
                uint32_t finalG = (dG * invOpInt + sG * opInt) >> 8;
                uint32_t finalB = (dB * invOpInt + sB * opInt) >> 8;
                row32[x] = a | (finalB << 16) | (finalG << 8) | finalR;
            }
        }
    }
}

void applyHueSat(const FilterSettings& filter, const FilterRegion& region) {
    uint8_t* ptr = region.ptr;
    [[maybe_unused]] const int w = region.w;
    [[maybe_unused]] const int h = region.h;
    [[maybe_unused]] const int startX = region.startX;
    [[maybe_unused]] const int endX = region.endX;
    [[maybe_unused]] const int startY = region.startY;
    [[maybe_unused]] const int endY = region.endY;
    [[maybe_unused]] const double opacity = region.opacity;
    [[maybe_unused]] const bool isFullOpacity = region.isFullOpacity;

    const float hueShift = filter.getParam(0, 0.0f);
    const float satDelta = filter.getParam(1, 0.0f) / 100.0f;
    const float lightDelta = filter.getParam(2, 0.0f) / 100.0f;
    const bool colorize = filter.getParam(3, 0.0f) > 0.5f;

    if (std::abs(hueShift) < 0.001f && std::abs(satDelta) < 0.001f && std::abs(lightDelta) < 0.001f && !colorize) {
        return;
    }

    #pragma omp parallel for schedule(static) if((endY - startY) > 32)
    for (int y = startY; y <= endY; ++y) {
        uint8_t* row = ptr + (static_cast<size_t>(y) * w + startX) * 4;
        for (int x = startX; x <= endX; ++x, row += 4) {
            if (row[3] == 0) continue;

            float r = row[0] / 255.0f;
            float g = row[1] / 255.0f;
            float b = row[2] / 255.0f;

            float fh, fs, fv;
            color::rgbToHsv(r, g, b, fh, fs, fv);

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

            uint8_t finalR = static_cast<uint8_t>(std::clamp(outR * 255.0f, 0.0f, 255.0f));
            uint8_t finalG = static_cast<uint8_t>(std::clamp(outG * 255.0f, 0.0f, 255.0f));
            uint8_t finalB = static_cast<uint8_t>(std::clamp(outB * 255.0f, 0.0f, 255.0f));

            if (!isFullOpacity) {
                row[0] = static_cast<uint8_t>(row[0] * (1.0 - opacity) + finalR * opacity);
                row[1] = static_cast<uint8_t>(row[1] * (1.0 - opacity) + finalG * opacity);
                row[2] = static_cast<uint8_t>(row[2] * (1.0 - opacity) + finalB * opacity);
            } else {
                row[0] = finalR;
                row[1] = finalG;
                row[2] = finalB;
            }
        }
    }
}

} // namespace aladyn::engine::document::filters
