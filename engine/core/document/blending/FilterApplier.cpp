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
    const size_t totalPixels = static_cast<size_t>(w * h);

    if (type == FilterType::HueSat) {
        const float hueShift = filter.getParam(0, 0.0f);
        const float satDelta = filter.getParam(1, 0.0f) / 100.0f;
        const float lightDelta = filter.getParam(2, 0.0f) / 100.0f;
        const bool colorize = filter.getParam(3, 0.0f) > 0.5f;

        for (int y = startY; y <= endY; ++y) {
            for (int x = startX; x <= endX; ++x) {
                size_t i = static_cast<size_t>(y * w + x);
                uint8_t a = ptr[i * 4 + 3];
                if (a == 0) continue;

                float r = ptr[i * 4 + 0] / 255.0f;
                float g = ptr[i * 4 + 1] / 255.0f;
                float b = ptr[i * 4 + 2] / 255.0f;

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

                if (opacity < 1.0) {
                    ptr[i * 4 + 0] = static_cast<uint8_t>(ptr[i * 4 + 0] * (1.0 - opacity) + finalR * opacity);
                    ptr[i * 4 + 1] = static_cast<uint8_t>(ptr[i * 4 + 1] * (1.0 - opacity) + finalG * opacity);
                    ptr[i * 4 + 2] = static_cast<uint8_t>(ptr[i * 4 + 2] * (1.0 - opacity) + finalB * opacity);
                } else {
                    ptr[i * 4 + 0] = finalR;
                    ptr[i * 4 + 1] = finalG;
                    ptr[i * 4 + 2] = finalB;
                }
            }
        }
    } else if (type == FilterType::BrightnessContrast) {
        const float bright = filter.getParam(0, 0.0f) / 100.0f;
        const float contrast = filter.getParam(1, 0.0f) / 100.0f;
        const float gamma = std::max(0.1f, filter.getParam(2, 1.0f));
        const float contrastFactor = contrast + 1.0f;

        for (int y = startY; y <= endY; ++y) {
            for (int x = startX; x <= endX; ++x) {
                size_t i = static_cast<size_t>(y * w + x);
                uint8_t a = ptr[i * 4 + 3];
                if (a == 0) continue;

                float r = ptr[i * 4 + 0] / 255.0f + bright;
                float g = ptr[i * 4 + 1] / 255.0f + bright;
                float b = ptr[i * 4 + 2] / 255.0f + bright;

                r = (r - 0.5f) * contrastFactor + 0.5f;
                g = (g - 0.5f) * contrastFactor + 0.5f;
                b = (b - 0.5f) * contrastFactor + 0.5f;

                if (gamma != 1.0f) {
                    r = std::pow(std::clamp(r, 0.0f, 1.0f), 1.0f / gamma);
                    g = std::pow(std::clamp(g, 0.0f, 1.0f), 1.0f / gamma);
                    b = std::pow(std::clamp(b, 0.0f, 1.0f), 1.0f / gamma);
                }

                uint8_t finalR = static_cast<uint8_t>(std::clamp(r * 255.0f, 0.0f, 255.0f));
                uint8_t finalG = static_cast<uint8_t>(std::clamp(g * 255.0f, 0.0f, 255.0f));
                uint8_t finalB = static_cast<uint8_t>(std::clamp(b * 255.0f, 0.0f, 255.0f));

                if (opacity < 1.0) {
                    ptr[i * 4 + 0] = static_cast<uint8_t>(ptr[i * 4 + 0] * (1.0 - opacity) + finalR * opacity);
                    ptr[i * 4 + 1] = static_cast<uint8_t>(ptr[i * 4 + 1] * (1.0 - opacity) + finalG * opacity);
                    ptr[i * 4 + 2] = static_cast<uint8_t>(ptr[i * 4 + 2] * (1.0 - opacity) + finalB * opacity);
                } else {
                    ptr[i * 4 + 0] = finalR;
                    ptr[i * 4 + 1] = finalG;
                    ptr[i * 4 + 2] = finalB;
                }
            }
        }
    } else if (type == FilterType::InvertThreshold) {
        const bool isInvert = filter.getParam(0, 1.0f) > 0.5f;
        const float threshold = filter.getParam(1, 128.0f);

        for (int y = startY; y <= endY; ++y) {
            for (int x = startX; x <= endX; ++x) {
                size_t i = static_cast<size_t>(y * w + x);
                uint8_t a = ptr[i * 4 + 3];
                if (a == 0) continue;

                uint8_t r = ptr[i * 4 + 0];
                uint8_t g = ptr[i * 4 + 1];
                uint8_t b = ptr[i * 4 + 2];

                uint8_t finalR, finalG, finalB;
                if (isInvert) {
                    finalR = 255 - r;
                    finalG = 255 - g;
                    finalB = 255 - b;
                } else {
                    float lum = 0.299f * r + 0.587f * g + 0.114f * b;
                    uint8_t v = (lum >= threshold) ? 255 : 0;
                    finalR = finalG = finalB = v;
                }

                if (opacity < 1.0) {
                    ptr[i * 4 + 0] = static_cast<uint8_t>(r * (1.0 - opacity) + finalR * opacity);
                    ptr[i * 4 + 1] = static_cast<uint8_t>(g * (1.0 - opacity) + finalG * opacity);
                    ptr[i * 4 + 2] = static_cast<uint8_t>(b * (1.0 - opacity) + finalB * opacity);
                } else {
                    ptr[i * 4 + 0] = finalR;
                    ptr[i * 4 + 1] = finalG;
                    ptr[i * 4 + 2] = finalB;
                }
            }
        }
    } else if (type == FilterType::ColorBalance) {
        const float rShift = filter.getParam(0, 0.0f) * 2.55f;
        const float gShift = filter.getParam(1, 0.0f) * 2.55f;
        const float bShift = filter.getParam(2, 0.0f) * 2.55f;

        for (int y = startY; y <= endY; ++y) {
            for (int x = startX; x <= endX; ++x) {
                size_t i = static_cast<size_t>(y * w + x);
                uint8_t a = ptr[i * 4 + 3];
                if (a == 0) continue;

                uint8_t r = ptr[i * 4 + 0];
                uint8_t g = ptr[i * 4 + 1];
                uint8_t b = ptr[i * 4 + 2];

                uint8_t finalR = static_cast<uint8_t>(std::clamp(r + rShift, 0.0f, 255.0f));
                uint8_t finalG = static_cast<uint8_t>(std::clamp(g + gShift, 0.0f, 255.0f));
                uint8_t finalB = static_cast<uint8_t>(std::clamp(b + bShift, 0.0f, 255.0f));

                if (opacity < 1.0) {
                    ptr[i * 4 + 0] = static_cast<uint8_t>(r * (1.0 - opacity) + finalR * opacity);
                    ptr[i * 4 + 1] = static_cast<uint8_t>(g * (1.0 - opacity) + finalG * opacity);
                    ptr[i * 4 + 2] = static_cast<uint8_t>(b * (1.0 - opacity) + finalB * opacity);
                } else {
                    ptr[i * 4 + 0] = finalR;
                    ptr[i * 4 + 1] = finalG;
                    ptr[i * 4 + 2] = finalB;
                }
            }
        }
    } else if (type == FilterType::Pixelate) {
        const int blockSize = std::clamp(static_cast<int>(filter.getParam(0, 8.0f)), 2, 64);
        std::vector<uint8_t> origBuffer(ptr, ptr + totalPixels * 4);

        int alignStartY = (startY / blockSize) * blockSize;
        int alignEndY   = std::min(h - 1, ((endY / blockSize) + 1) * blockSize - 1);
        int alignStartX = (startX / blockSize) * blockSize;
        int alignEndX   = std::min(w - 1, ((endX / blockSize) + 1) * blockSize - 1);

        for (int y = alignStartY; y <= alignEndY; y += blockSize) {
            for (int x = alignStartX; x <= alignEndX; x += blockSize) {
                int sampleX = std::min(x + blockSize / 2, w - 1);
                int sampleY = std::min(y + blockSize / 2, h - 1);
                size_t sampleIdx = static_cast<size_t>(sampleY * w + sampleX);

                uint8_t sr = origBuffer[sampleIdx * 4 + 0];
                uint8_t sg = origBuffer[sampleIdx * 4 + 1];
                uint8_t sb = origBuffer[sampleIdx * 4 + 2];
                uint8_t sa = origBuffer[sampleIdx * 4 + 3];

                if (sa == 0) continue;

                int blockMaxY = std::min(y + blockSize, h);
                int blockMaxX = std::min(x + blockSize, w);

                for (int by = y; by < blockMaxY; ++by) {
                    for (int bx = x; bx < blockMaxX; ++bx) {
                        size_t pxIdx = static_cast<size_t>(by * w + bx);
                        uint8_t a = ptr[pxIdx * 4 + 3];
                        if (a == 0) continue;

                        if (opacity < 1.0) {
                            ptr[pxIdx * 4 + 0] = static_cast<uint8_t>(ptr[pxIdx * 4 + 0] * (1.0 - opacity) + sr * opacity);
                            ptr[pxIdx * 4 + 1] = static_cast<uint8_t>(ptr[pxIdx * 4 + 1] * (1.0 - opacity) + sg * opacity);
                            ptr[pxIdx * 4 + 2] = static_cast<uint8_t>(ptr[pxIdx * 4 + 2] * (1.0 - opacity) + sb * opacity);
                        } else {
                            ptr[pxIdx * 4 + 0] = sr;
                            ptr[pxIdx * 4 + 1] = sg;
                            ptr[pxIdx * 4 + 2] = sb;
                        }
                    }
                }
            }
        }
    }
}

} // namespace aladyn::engine::document::blending
