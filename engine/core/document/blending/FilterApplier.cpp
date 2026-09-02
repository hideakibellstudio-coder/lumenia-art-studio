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
    } else if (type == FilterType::GaussianBlur) {
        const int radius = std::clamp(static_cast<int>(filter.getParam(0, 10.0f)), 1, 100);
        const float sigma = std::max(0.5f, radius / 3.0f);
        const float twoSigmaSq = 2.0f * sigma * sigma;
        const int kSize = radius * 2 + 1;
        std::vector<float> kernel(kSize);
        float kSum = 0.0f;
        for (int k = -radius; k <= radius; ++k) {
            float val = std::exp(-(k * k) / twoSigmaSq);
            kernel[k + radius] = val;
            kSum += val;
        }
        for (auto& v : kernel) v /= kSum;

        const int regW = endX - startX + 1;
        const int regH = endY - startY + 1;
        std::vector<uint8_t> temp(static_cast<size_t>(regW) * regH * 4);

        // Pass 1: Horizontal
        #pragma omp parallel for schedule(static) if(regH > 16)
        for (int y = startY; y <= endY; ++y) {
            const int localY = y - startY;
            const uint8_t* inRow = ptr + static_cast<size_t>(y) * w * 4;
            uint8_t* outRow = temp.data() + static_cast<size_t>(localY) * regW * 4;

            for (int x = startX; x <= endX; ++x) {
                const int localX = x - startX;
                float accR = 0.0f, accG = 0.0f, accB = 0.0f, accA = 0.0f;

                for (int k = -radius; k <= radius; ++k) {
                    const int sx = std::clamp(x + k, 0, w - 1);
                    const float weight = kernel[k + radius];
                    const uint8_t* sp = inRow + static_cast<size_t>(sx) * 4;
                    accR += sp[0] * weight;
                    accG += sp[1] * weight;
                    accB += sp[2] * weight;
                    accA += sp[3] * weight;
                }

                uint8_t* dp = outRow + static_cast<size_t>(localX) * 4;
                dp[0] = static_cast<uint8_t>(std::clamp(accR, 0.0f, 255.0f));
                dp[1] = static_cast<uint8_t>(std::clamp(accG, 0.0f, 255.0f));
                dp[2] = static_cast<uint8_t>(std::clamp(accB, 0.0f, 255.0f));
                dp[3] = static_cast<uint8_t>(std::clamp(accA, 0.0f, 255.0f));
            }
        }

        // Pass 2: Vertical
        #pragma omp parallel for schedule(static) if(regW > 16)
        for (int x = startX; x <= endX; ++x) {
            const int localX = x - startX;

            for (int y = startY; y <= endY; ++y) {
                const int localY = y - startY;
                float accR = 0.0f, accG = 0.0f, accB = 0.0f, accA = 0.0f;

                for (int k = -radius; k <= radius; ++k) {
                    const int sy = std::clamp(localY + k, 0, regH - 1);
                    const float weight = kernel[k + radius];
                    const uint8_t* sp = temp.data() + (static_cast<size_t>(sy) * regW + localX) * 4;
                    accR += sp[0] * weight;
                    accG += sp[1] * weight;
                    accB += sp[2] * weight;
                    accA += sp[3] * weight;
                }

                uint8_t* dp = ptr + (static_cast<size_t>(y) * w + x) * 4;
                uint8_t bR = static_cast<uint8_t>(std::clamp(accR, 0.0f, 255.0f));
                uint8_t bG = static_cast<uint8_t>(std::clamp(accG, 0.0f, 255.0f));
                uint8_t bB = static_cast<uint8_t>(std::clamp(accB, 0.0f, 255.0f));
                uint8_t bA = static_cast<uint8_t>(std::clamp(accA, 0.0f, 255.0f));

                if (!isFullOpacity) {
                    dp[0] = static_cast<uint8_t>(dp[0] * (1.0 - opacity) + bR * opacity);
                    dp[1] = static_cast<uint8_t>(dp[1] * (1.0 - opacity) + bG * opacity);
                    dp[2] = static_cast<uint8_t>(dp[2] * (1.0 - opacity) + bB * opacity);
                    dp[3] = static_cast<uint8_t>(dp[3] * (1.0 - opacity) + bA * opacity);
                } else {
                    dp[0] = bR; dp[1] = bG; dp[2] = bB; dp[3] = bA;
                }
            }
        }
    } else if (type == FilterType::SharpenVignette) {
        const float sharpen = std::clamp(filter.getParam(0, 25.0f) / 100.0f, 0.0f, 1.0f);
        const float vignette = std::clamp(filter.getParam(1, 0.0f) / 100.0f, 0.0f, 1.0f);
        const float vRad = std::clamp(filter.getParam(2, 50.0f) / 100.0f, 0.1f, 1.0f);

        const float cx = w * 0.5f;
        const float cy = h * 0.5f;
        const float maxDist = std::sqrt(cx * cx + cy * cy) * vRad;
        const float innerDist = maxDist * 0.4f;

        const int regW = endX - startX + 1;
        const int regH = endY - startY + 1;
        std::vector<uint8_t> srcCopy;
        if (sharpen > 0.001f) {
            srcCopy.assign(ptr, ptr + static_cast<size_t>(w) * h * 4);
        }

        #pragma omp parallel for schedule(static) if(regH > 16)
        for (int y = startY; y <= endY; ++y) {
            uint8_t* row = ptr + static_cast<size_t>(y) * w * 4 + startX * 4;

            for (int x = startX; x <= endX; ++x, row += 4) {
                if (row[3] == 0) continue;

                float r = row[0];
                float g = row[1];
                float b = row[2];

                // 1. Sharpen (Laplacian 3x3 filter)
                if (sharpen > 0.001f) {
                    const int upY = std::max(0, y - 1);
                    const int dnY = std::min(h - 1, y + 1);
                    const int lfX = std::max(0, x - 1);
                    const int rgX = std::min(w - 1, x + 1);

                    const uint8_t* pUp = srcCopy.data() + (static_cast<size_t>(upY) * w + x) * 4;
                    const uint8_t* pDn = srcCopy.data() + (static_cast<size_t>(dnY) * w + x) * 4;
                    const uint8_t* pLf = srcCopy.data() + (static_cast<size_t>(y) * w + lfX) * 4;
                    const uint8_t* pRg = srcCopy.data() + (static_cast<size_t>(y) * w + rgX) * 4;

                    r = r * (1.0f + 4.0f * sharpen) - sharpen * (pUp[0] + pDn[0] + pLf[0] + pRg[0]);
                    g = g * (1.0f + 4.0f * sharpen) - sharpen * (pUp[1] + pDn[1] + pLf[1] + pRg[1]);
                    b = b * (1.0f + 4.0f * sharpen) - sharpen * (pUp[2] + pDn[2] + pLf[2] + pRg[2]);
                }

                // 2. Vignette
                if (vignette > 0.001f) {
                    const float dx = static_cast<float>(x) - cx;
                    const float dy = static_cast<float>(y) - cy;
                    const float dist = std::sqrt(dx * dx + dy * dy);
                    if (dist > innerDist) {
                        const float t = std::clamp((dist - innerDist) / (maxDist - innerDist), 0.0f, 1.0f);
                        const float smoothT = t * t * (3.0f - 2.0f * t);
                        const float vFactor = 1.0f - smoothT * vignette;
                        r *= vFactor;
                        g *= vFactor;
                        b *= vFactor;
                    }
                }

                uint8_t outR = static_cast<uint8_t>(std::clamp(r, 0.0f, 255.0f));
                uint8_t outG = static_cast<uint8_t>(std::clamp(g, 0.0f, 255.0f));
                uint8_t outB = static_cast<uint8_t>(std::clamp(b, 0.0f, 255.0f));

                if (!isFullOpacity) {
                    row[0] = static_cast<uint8_t>(row[0] * (1.0 - opacity) + outR * opacity);
                    row[1] = static_cast<uint8_t>(row[1] * (1.0 - opacity) + outG * opacity);
                    row[2] = static_cast<uint8_t>(row[2] * (1.0 - opacity) + outB * opacity);
                } else {
                    row[0] = outR;
                    row[1] = outG;
                    row[2] = outB;
                }
            }
        }
    }
}

} // namespace aladyn::engine::document::blending
