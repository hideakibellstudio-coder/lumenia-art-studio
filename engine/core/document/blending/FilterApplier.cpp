#include "FilterApplier.hpp"
#include "BlendEquations.hpp"
#include <algorithm>
#include <cmath>
#include <vector>

namespace aladyn::engine::document::blending {

void FilterApplier::apply(const FilterLayer& filter, canvas::PixelBuffer& buffer, int minX, int maxX, int minY, int maxY) {
    const double opacity = filter.getEffectiveOpacity();
    if (opacity <= 0.0) return;

    const FilterType type = filter.getFilterType();
    const int w = buffer.getWidth();
    const int h = buffer.getHeight();

    int startX = std::max(0, minX);
    int endX   = (maxX < 0) ? (w - 1) : std::min(w - 1, maxX);
    int startY = std::max(0, minY);
    int endY   = (maxY < 0) ? (h - 1) : std::min(h - 1, maxY);

    if (startX > endX || startY > endY) return;

    uint8_t* ptr = buffer.getData();
    const bool isFullOpacity = (opacity >= 0.999);

    if (type == FilterType::BrightnessContrast) {
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
    } else if (type == FilterType::ColorBalance) {
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
    } else if (type == FilterType::InvertThreshold) {
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
    } else if (type == FilterType::HueSat) {
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
                rgbToHsv(r, g, b, fh, fs, fv);

                if (colorize) {
                    fh = std::fmod(std::abs(hueShift), 360.0f);
                    fs = std::clamp(0.5f + satDelta, 0.0f, 1.0f);
                } else {
                    fh = std::fmod(fh + hueShift + 360.0f, 360.0f);
                    fs = std::clamp(fs + satDelta, 0.0f, 1.0f);
                }
                fv = std::clamp(fv + lightDelta, 0.0f, 1.0f);

                float outR, outG, outB;
                hsvToRgb(fh, fs, fv, outR, outG, outB);

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
    } else if (type == FilterType::Pixelate) {
        const int blockSize = std::clamp(static_cast<int>(filter.getParam(0, 8.0f)), 2, 64);
        int alignStartY = (startY / blockSize) * blockSize;
        int alignEndY   = std::min(h - 1, ((endY / blockSize) + 1) * blockSize - 1);
        int alignStartX = (startX / blockSize) * blockSize;
        int alignEndX   = std::min(w - 1, ((endX / blockSize) + 1) * blockSize - 1);

        for (int y = alignStartY; y <= alignEndY; y += blockSize) {
            for (int x = alignStartX; x <= alignEndX; x += blockSize) {
                int sampleX = std::min(x + blockSize / 2, w - 1);
                int sampleY = std::min(y + blockSize / 2, h - 1);
                size_t sampleIdx = static_cast<size_t>(sampleY * w + sampleX);

                uint8_t sr = ptr[sampleIdx * 4 + 0];
                uint8_t sg = ptr[sampleIdx * 4 + 1];
                uint8_t sb = ptr[sampleIdx * 4 + 2];
                uint8_t sa = ptr[sampleIdx * 4 + 3];

                if (sa == 0) continue;

                int blockMaxY = std::min(y + blockSize, h);
                int blockMaxX = std::min(x + blockSize, w);

                for (int by = y; by < blockMaxY; ++by) {
                    uint8_t* row = ptr + (static_cast<size_t>(by) * w + x) * 4;
                    for (int bx = x; bx < blockMaxX; ++bx, row += 4) {
                        if (row[3] == 0) continue;

                        if (!isFullOpacity) {
                            row[0] = static_cast<uint8_t>(row[0] * (1.0 - opacity) + sr * opacity);
                            row[1] = static_cast<uint8_t>(row[1] * (1.0 - opacity) + sg * opacity);
                            row[2] = static_cast<uint8_t>(row[2] * (1.0 - opacity) + sb * opacity);
                        } else {
                            row[0] = sr;
                            row[1] = sg;
                            row[2] = sb;
                        }
                    }
                }
            }
        }
    }
}

} // namespace aladyn::engine::document::blending
