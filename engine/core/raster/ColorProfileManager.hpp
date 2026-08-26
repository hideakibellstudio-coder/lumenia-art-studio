#ifndef ALADYN_ENGINE_COLOR_PROFILE_MANAGER_HPP
#define ALADYN_ENGINE_COLOR_PROFILE_MANAGER_HPP

#include <cstdint>
#include <cstddef>
#include <algorithm>
#include <cmath>

namespace aladyn::engine::raster {

class ColorProfileManager {
public:
    static inline uint8_t clampU8(int32_t val) noexcept {
        if (val < 0) return 0;
        if (val > 255) return 255;
        return static_cast<uint8_t>(val);
    }

    // ─── TRANSFORMAÇÃO POR PIXEL EM PONTO FIXO INTEIRO (ULTRA-RÁPIDO) ─────────
    static inline void transformPixelFixed(uint8_t* px, int profileId) noexcept {
        const int32_t r = px[0];
        const int32_t g = px[1];
        const int32_t b = px[2];

        if (profileId == 11) {
            // Acromatopsia (Monocromático Rec.709)
            // (54*R + 183*G + 19*B) >> 8
            const uint8_t lum = static_cast<uint8_t>((54 * r + 183 * g + 19 * b) >> 8);
            px[0] = lum;
            px[1] = lum;
            px[2] = lum;
            return;
        }

        if (profileId == 8) {
            // Protanopia (Sem Vermelho)
            // 0.56667*R + 0.43333*G -> (37138*R + 28398*G) >> 16
            // 0.55833*R + 0.44167*G -> (36590*R + 28946*G) >> 16
            // 0.24167*G + 0.75833*B -> (15838*G + 49698*B) >> 16
            px[0] = clampU8((37138 * r + 28398 * g) >> 16);
            px[1] = clampU8((36590 * r + 28946 * g) >> 16);
            px[2] = clampU8((15838 * g + 49698 * b) >> 16);
            return;
        }

        if (profileId == 9) {
            // Deuteranopia (Sem Verde)
            // 0.625*R + 0.375*G -> (40960*R + 24576*G) >> 16
            // 0.700*R + 0.300*G -> (45875*R + 19661*G) >> 16
            // 0.300*G + 0.700*B -> (19661*G + 45875*B) >> 16
            px[0] = clampU8((40960 * r + 24576 * g) >> 16);
            px[1] = clampU8((45875 * r + 19661 * g) >> 16);
            px[2] = clampU8((19661 * g + 45875 * b) >> 16);
            return;
        }

        if (profileId == 10) {
            // Tritanopia (Sem Azul/Amarelo)
            // 0.950*R + 0.050*G -> (62259*R + 3277*G) >> 16
            // 0.43333*G + 0.56667*B -> (28398*G + 37138*B) >> 16
            // 0.475*G + 0.525*B -> (31130*G + 34406*B) >> 16
            px[0] = clampU8((62259 * r + 3277 * g) >> 16);
            px[1] = clampU8((28398 * g + 37138 * b) >> 16);
            px[2] = clampU8((31130 * g + 34406 * b) >> 16);
            return;
        }

        if (profileId >= 4 && profileId <= 7) {
            // Impressão CMYK
            const int32_t invR = 255 - r;
            const int32_t invG = 255 - g;
            const int32_t invB = 255 - b;
            const int32_t k = std::min({invR, invG, invB});

            if (k < 255) {
                const int32_t denom = 255 - k;
                const int32_t c = ((invR - k) * 255) / denom;
                const int32_t m = ((invG - k) * 255) / denom;
                const int32_t y = ((invB - k) * 255) / denom;

                const int32_t cLim = (c * 242) >> 8;
                const int32_t mLim = (m * 235) >> 8;
                const int32_t yLim = (y * 242) >> 8;
                const int32_t kLim = std::min(242, (k * 268) >> 8);

                const int32_t remK = 255 - kLim;
                const int32_t outR = (((255 - cLim) * remK * 243) >> 16) + 8;
                const int32_t outG = (((255 - mLim) * remK * 240) >> 16) + 8;
                const int32_t outB = (((255 - yLim) * remK * 235) >> 16) + 8;

                px[0] = clampU8(outR);
                px[1] = clampU8(outG);
                px[2] = clampU8(outB);
            }
            return;
        }

        if (profileId == 1) {
            // Display P3 (Wide Gamut Boost)
            const int32_t maxC = std::max({r, g, b});
            const int32_t minC = std::min({r, g, b});
            const int32_t sat = (maxC > 0) ? ((maxC - minC) * 255) / maxC : 0;
            const int32_t boost = 256 + ((38 * sat) >> 8);

            px[0] = clampU8((r == maxC) ? ((r * boost) >> 8) : ((r * 245) >> 8));
            px[1] = clampU8((g == maxC) ? ((g * boost) >> 8) : ((g * 245) >> 8));
            px[2] = clampU8((b == maxC) ? ((b * boost) >> 8) : ((b * 245) >> 8));
            return;
        }

        if (profileId == 12) {
            // Linear sRGB (Gama 1.0 - LUT de 256 bytes)
            static const uint8_t sRGBToLinearLUT[256] = {
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1,
                1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4,
                4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 9, 9, 9,
                10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 18,
                18, 19, 19, 20, 21, 21, 22, 23, 23, 24, 25, 25, 26, 27, 28, 28,
                29, 30, 31, 32, 32, 33, 34, 35, 36, 37, 37, 38, 39, 40, 41, 42,
                43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58,
                59, 61, 62, 63, 64, 65, 67, 68, 69, 70, 72, 73, 74, 76, 77, 78,
                80, 81, 82, 84, 85, 87, 88, 89, 91, 92, 94, 95, 97, 98, 100, 101,
                103, 104, 106, 108, 109, 111, 113, 114, 116, 118, 119, 121, 123, 125, 126, 128,
                130, 132, 134, 135, 137, 139, 141, 143, 145, 147, 149, 151, 153, 155, 157, 159,
                161, 163, 165, 167, 169, 171, 173, 176, 178, 180, 182, 185, 187, 189, 191, 194,
                196, 198, 201, 203, 205, 208, 210, 213, 215, 218, 220, 223, 225, 228, 230, 233,
                236, 238, 241, 244, 246, 249, 252, 255
            };
            px[0] = sRGBToLinearLUT[r];
            px[1] = sRGBToLinearLUT[g];
            px[2] = sRGBToLinearLUT[b];
            return;
        }

        if (profileId == 13) {
            // ACEScg
            const auto acesTone = [](float x) -> float {
                constexpr float a = 2.51f, b = 0.03f, c = 2.43f, d = 0.59f, e = 0.14f;
                return std::clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0f, 1.0f);
            };
            px[0] = static_cast<uint8_t>(acesTone(r * (1.2f / 255.0f)) * 255.0f);
            px[1] = static_cast<uint8_t>(acesTone(g * (1.2f / 255.0f)) * 255.0f);
            px[2] = static_cast<uint8_t>(acesTone(b * (1.2f / 255.0f)) * 255.0f);
            return;
        }
    }

    // ─── TRANSFORMAÇÃO DE REGIÃO DELIMITADA (DIRTY RECT - ULTRA-RÁPIDO) ────────
    static void applyColorProfileRegion(
        uint8_t* ptr,
        int bufferWidth,
        int minX, int minY, int maxX, int maxY,
        int profileId
    ) noexcept {
        if (!ptr || profileId == 0) return;

        for (int y = minY; y <= maxY; ++y) {
            uint8_t* row = ptr + static_cast<size_t>((y * bufferWidth + minX) * 4);
            const int count = (maxX - minX + 1);
            for (int x = 0; x < count; ++x) {
                transformPixelFixed(row + (x * 4), profileId);
            }
        }
    }

    // ─── TRANSFORMAÇÃO DE BUFFER CONTÍGUO COMPLETO ───────────────────────────
    static void applyColorProfile(uint8_t* ptr, size_t numPixels, int profileId) noexcept {
        if (!ptr || numPixels == 0 || profileId == 0) return;

        for (size_t i = 0; i < numPixels; ++i) {
            transformPixelFixed(ptr + (i * 4), profileId);
        }
    }
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_COLOR_PROFILE_MANAGER_HPP
