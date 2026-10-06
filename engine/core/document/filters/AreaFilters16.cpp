// AreaFilters16.cpp — núcleos de filtro de área de 16 bits (S5)
// Cada pixel de saída depende da vizinhança, então há uma cópia auxiliar do recorte. A regra de cada filtro é a de
// AreaFilters.cpp (o mesmo kernel, o mesmo alcance, a mesma regra do alfa 0), com a conta em float arredondada ao
// nível de 16 bits e a mistura com a opacidade em 16 bits.

#include "FilterKernels16.hpp"

#include <algorithm>
#include <cmath>
#include <vector>

namespace aladyn::engine::document::filters {

using utils::ColorRGBA16;

void applyPixelate16(const FilterSettings& filter, const FilterRegion& region) {
    ColorRGBA16* ptr = reinterpret_cast<ColorRGBA16*>(region.ptr);
    const int w = region.w;
    const int h = region.h;
    const uint32_t weight = opacityWeight16(region.opacity);

    const int blockSize = std::clamp(static_cast<int>(filter.getParam(0, 8.0f)), 2, 64);
    const int alignStartY = (region.startY / blockSize) * blockSize;
    const int alignEndY = std::min(h - 1, ((region.endY / blockSize) + 1) * blockSize - 1);
    const int alignStartX = (region.startX / blockSize) * blockSize;
    const int alignEndX = std::min(w - 1, ((region.endX / blockSize) + 1) * blockSize - 1);

    for (int y = alignStartY; y <= alignEndY; y += blockSize) {
        for (int x = alignStartX; x <= alignEndX; x += blockSize) {
            const int sampleX = std::min(x + blockSize / 2, w - 1);
            const int sampleY = std::min(y + blockSize / 2, h - 1);
            const ColorRGBA16 sample = ptr[static_cast<size_t>(sampleY) * w + sampleX];
            if (sample.a == 0) continue;

            const int blockMaxY = std::min(y + blockSize, h);
            const int blockMaxX = std::min(x + blockSize, w);
            for (int by = y; by < blockMaxY; ++by) {
                ColorRGBA16* row = ptr + static_cast<size_t>(by) * w + x;
                for (int bx = x; bx < blockMaxX; ++bx, ++row) {
                    if (row->a == 0) continue;
                    if (region.isFullOpacity) {
                        row->r = sample.r;
                        row->g = sample.g;
                        row->b = sample.b;
                    } else {
                        row->r = mixChannel16(row->r, sample.r, weight);
                        row->g = mixChannel16(row->g, sample.g, weight);
                        row->b = mixChannel16(row->b, sample.b, weight);
                    }
                }
            }
        }
    }
}

void applyGaussianBlur16(const FilterSettings& filter, const FilterRegion& region) {
    ColorRGBA16* ptr = reinterpret_cast<ColorRGBA16*>(region.ptr);
    const int w = region.w;
    const int startX = region.startX, endX = region.endX, startY = region.startY, endY = region.endY;
    const uint32_t weight = opacityWeight16(region.opacity);

    const int radius = std::clamp(static_cast<int>(filter.getParam(0, 10.0f)), 1, 100);
    const float sigma = std::max(0.5f, radius / 3.0f);
    const float twoSigmaSq = 2.0f * sigma * sigma;
    std::vector<float> kernel(radius * 2 + 1);
    float kSum = 0.0f;
    for (int k = -radius; k <= radius; ++k) {
        const float val = std::exp(-(k * k) / twoSigmaSq);
        kernel[k + radius] = val;
        kSum += val;
    }
    for (auto& v : kernel) v /= kSum;

    const int regW = endX - startX + 1;
    const int regH = endY - startY + 1;
    std::vector<ColorRGBA16> temp(static_cast<size_t>(regW) * regH);

    // Passo 1: horizontal, da imagem para o auxiliar.
    #pragma omp parallel for schedule(static) if(regH > 16)
    for (int y = startY; y <= endY; ++y) {
        const ColorRGBA16* inRow = ptr + static_cast<size_t>(y) * w;
        ColorRGBA16* outRow = temp.data() + static_cast<size_t>(y - startY) * regW;
        for (int x = startX; x <= endX; ++x) {
            float accR = 0.0f, accG = 0.0f, accB = 0.0f, accA = 0.0f;
            for (int k = -radius; k <= radius; ++k) {
                const ColorRGBA16 sp = inRow[std::clamp(x + k, 0, w - 1)];
                const float weightK = kernel[k + radius];
                accR += sp.r * weightK;
                accG += sp.g * weightK;
                accB += sp.b * weightK;
                accA += sp.a * weightK;
            }
            outRow[x - startX] = ColorRGBA16{roundChannel16(accR), roundChannel16(accG), roundChannel16(accB), roundChannel16(accA)};
        }
    }

    // Passo 2: vertical, do auxiliar de volta à imagem.
    #pragma omp parallel for schedule(static) if(regW > 16)
    for (int x = startX; x <= endX; ++x) {
        const int localX = x - startX;
        for (int y = startY; y <= endY; ++y) {
            const int localY = y - startY;
            float accR = 0.0f, accG = 0.0f, accB = 0.0f, accA = 0.0f;
            for (int k = -radius; k <= radius; ++k) {
                const ColorRGBA16 sp = temp[static_cast<size_t>(std::clamp(localY + k, 0, regH - 1)) * regW + localX];
                const float weightK = kernel[k + radius];
                accR += sp.r * weightK;
                accG += sp.g * weightK;
                accB += sp.b * weightK;
                accA += sp.a * weightK;
            }
            const ColorRGBA16 blurred{roundChannel16(accR), roundChannel16(accG), roundChannel16(accB), roundChannel16(accA)};
            ColorRGBA16& dp = ptr[static_cast<size_t>(y) * w + x];
            dp = region.isFullOpacity ? blurred
                                      : ColorRGBA16{mixChannel16(dp.r, blurred.r, weight), mixChannel16(dp.g, blurred.g, weight),
                                                    mixChannel16(dp.b, blurred.b, weight), mixChannel16(dp.a, blurred.a, weight)};
        }
    }
}

void applySharpenVignette16(const FilterSettings& filter, const FilterRegion& region) {
    ColorRGBA16* ptr = reinterpret_cast<ColorRGBA16*>(region.ptr);
    const int w = region.w;
    const int h = region.h;
    const uint32_t weight = opacityWeight16(region.opacity);

    const float sharpen = std::clamp(filter.getParam(0, 25.0f) / 100.0f, 0.0f, 1.0f);
    const float vignette = std::clamp(filter.getParam(1, 0.0f) / 100.0f, 0.0f, 1.0f);
    const float vRad = std::clamp(filter.getParam(2, 50.0f) / 100.0f, 0.1f, 1.0f);

    const float cx = w * 0.5f;
    const float cy = h * 0.5f;
    const float maxDist = std::sqrt(cx * cx + cy * cy) * vRad;
    const float innerDist = maxDist * 0.4f;

    const int regH = region.endY - region.startY + 1;
    std::vector<ColorRGBA16> srcCopy;
    if (sharpen > 0.001f) srcCopy.assign(ptr, ptr + static_cast<size_t>(w) * h);

    #pragma omp parallel for schedule(static) if(regH > 16)
    for (int y = region.startY; y <= region.endY; ++y) {
        ColorRGBA16* row = ptr + static_cast<size_t>(y) * w + region.startX;
        for (int x = region.startX; x <= region.endX; ++x, ++row) {
            if (row->a == 0) continue;
            float r = row->r;
            float g = row->g;
            float b = row->b;

            // 1. Nitidez (Laplaciano 3x3)
            if (sharpen > 0.001f) {
                const int upY = std::max(0, y - 1);
                const int dnY = std::min(h - 1, y + 1);
                const int lfX = std::max(0, x - 1);
                const int rgX = std::min(w - 1, x + 1);
                const ColorRGBA16 up = srcCopy[static_cast<size_t>(upY) * w + x];
                const ColorRGBA16 dn = srcCopy[static_cast<size_t>(dnY) * w + x];
                const ColorRGBA16 lf = srcCopy[static_cast<size_t>(y) * w + lfX];
                const ColorRGBA16 rg = srcCopy[static_cast<size_t>(y) * w + rgX];
                r = r * (1.0f + 4.0f * sharpen) - sharpen * (up.r + dn.r + lf.r + rg.r);
                g = g * (1.0f + 4.0f * sharpen) - sharpen * (up.g + dn.g + lf.g + rg.g);
                b = b * (1.0f + 4.0f * sharpen) - sharpen * (up.b + dn.b + lf.b + rg.b);
            }

            // 2. Vinheta
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

            const uint16_t outR = roundChannel16(r), outG = roundChannel16(g), outB = roundChannel16(b);
            if (region.isFullOpacity) {
                row->r = outR;
                row->g = outG;
                row->b = outB;
            } else {
                row->r = mixChannel16(row->r, outR, weight);
                row->g = mixChannel16(row->g, outG, weight);
                row->b = mixChannel16(row->b, outB, weight);
            }
        }
    }
}

} // namespace aladyn::engine::document::filters
