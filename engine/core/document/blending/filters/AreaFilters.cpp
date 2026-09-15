// AreaFilters.cpp — nucleos de filtro de area
// Cada pixel de saida depende da vizinhanca, exigindo copia auxiliar do recorte.
//
// Corpos extraidos SEM alteracao de FilterApplier.cpp (fatiamento por linha,
// apenas desindentados em 4 espacos). Nenhuma expressao foi reescrita.

#include "FilterKernels.hpp"
#include "../BlendEquations.hpp"

#include <algorithm>
#include <cmath>
#include <vector>

namespace aladyn::engine::document::blending::filters {

void applyPixelate(const FilterLayer& filter, const FilterRegion& region) {
    uint8_t* ptr = region.ptr;
    [[maybe_unused]] const int w = region.w;
    [[maybe_unused]] const int h = region.h;
    [[maybe_unused]] const int startX = region.startX;
    [[maybe_unused]] const int endX = region.endX;
    [[maybe_unused]] const int startY = region.startY;
    [[maybe_unused]] const int endY = region.endY;
    [[maybe_unused]] const double opacity = region.opacity;
    [[maybe_unused]] const bool isFullOpacity = region.isFullOpacity;

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

void applyGaussianBlur(const FilterLayer& filter, const FilterRegion& region) {
    uint8_t* ptr = region.ptr;
    [[maybe_unused]] const int w = region.w;
    [[maybe_unused]] const int h = region.h;
    [[maybe_unused]] const int startX = region.startX;
    [[maybe_unused]] const int endX = region.endX;
    [[maybe_unused]] const int startY = region.startY;
    [[maybe_unused]] const int endY = region.endY;
    [[maybe_unused]] const double opacity = region.opacity;
    [[maybe_unused]] const bool isFullOpacity = region.isFullOpacity;

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
}

void applySharpenVignette(const FilterLayer& filter, const FilterRegion& region) {
    uint8_t* ptr = region.ptr;
    [[maybe_unused]] const int w = region.w;
    [[maybe_unused]] const int h = region.h;
    [[maybe_unused]] const int startX = region.startX;
    [[maybe_unused]] const int endX = region.endX;
    [[maybe_unused]] const int startY = region.startY;
    [[maybe_unused]] const int endY = region.endY;
    [[maybe_unused]] const double opacity = region.opacity;
    [[maybe_unused]] const bool isFullOpacity = region.isFullOpacity;

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

} // namespace aladyn::engine::document::blending::filters
