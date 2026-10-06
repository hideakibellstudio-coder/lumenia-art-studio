#ifndef ALADYN_ENGINE_TRANSFORM_SAMPLERS_HPP
#define ALADYN_ENGINE_TRANSFORM_SAMPLERS_HPP

#include "../../../utils/ColorRGBA.hpp"
#include "../../../utils/ColorRGBA16.hpp"
#include "../../canvas/PixelBuffer.hpp"
#include <algorithm>
#include <cmath>
#include <type_traits>

namespace aladyn::engine::raster::transform {

inline double cubicWeight(double t) noexcept {
    const double at = std::abs(t);
    if (at <= 1.0) {
        return 0.5 * (at * at * (3.0 * at - 5.0) + 2.0);
    } else if (at < 2.0) {
        return 0.5 * (at * (-at * at + 5.0 * at - 8.0) + 4.0);
    }
    return 0.0;
}

template <class Pixel = utils::ColorRGBA>
inline Pixel sampleNearest(const canvas::PixelBuffer& src, double u, double v) noexcept {
    const int x = static_cast<int>(std::floor(u));
    const int y = static_cast<int>(std::floor(v));
    if constexpr (std::is_same_v<Pixel, utils::ColorRGBA16>) {
        return src.getPixel16(x, y);
    } else {
        return src.getPixel(x, y);
    }
}

template <class Pixel = utils::ColorRGBA>
inline Pixel sampleBilinear(const canvas::PixelBuffer& src, double u, double v) noexcept {
    const int w = src.getWidth();
    const int h = src.getHeight();

    int x0 = static_cast<int>(std::floor(u));
    int y0 = static_cast<int>(std::floor(v));
    int x1 = x0 + 1;
    int y1 = y0 + 1;

    const double fx = u - x0;
    const double fy = v - y0;

    x0 = std::clamp(x0, 0, w - 1);
    y0 = std::clamp(y0, 0, h - 1);
    x1 = std::clamp(x1, 0, w - 1);
    y1 = std::clamp(y1, 0, h - 1);

    constexpr double maxVal = std::is_same_v<Pixel, utils::ColorRGBA16> ? 65535.0 : 255.0;

    auto getP = [&](int x, int y) {
        if constexpr (std::is_same_v<Pixel, utils::ColorRGBA16>) {
            return src.getPixel16(x, y);
        } else {
            return src.getPixel(x, y);
        }
    };

    const auto c00 = getP(x0, y0);
    const auto c10 = getP(x1, y0);
    const auto c01 = getP(x0, y1);
    const auto c11 = getP(x1, y1);

    const double a00 = c00.a / maxVal, a10 = c10.a / maxVal, a01 = c01.a / maxVal, a11 = c11.a / maxVal;
    const double r00 = c00.r * a00, r10 = c10.r * a10, r01 = c01.r * a01, r11 = c11.r * a11;
    const double g00 = c00.g * a00, g10 = c10.g * a10, g01 = c01.g * a01, g11 = c11.g * a11;
    const double b00 = c00.b * a00, b10 = c10.b * a10, b01 = c01.b * a01, b11 = c11.b * a11;

    const double topR = r00 * (1.0 - fx) + r10 * fx;
    const double topG = g00 * (1.0 - fx) + g10 * fx;
    const double topB = b00 * (1.0 - fx) + b10 * fx;
    const double topA = a00 * (1.0 - fx) + a10 * fx;

    const double botR = r01 * (1.0 - fx) + r11 * fx;
    const double botG = g01 * (1.0 - fx) + g11 * fx;
    const double botB = b01 * (1.0 - fx) + b11 * fx;
    const double botA = a01 * (1.0 - fx) + a11 * fx;

    const double outR = topR * (1.0 - fy) + botR * fy;
    const double outG = topG * (1.0 - fy) + botG * fy;
    const double outB = topB * (1.0 - fy) + botB * fy;
    const double outA = topA * (1.0 - fy) + botA * fy;

    if (outA > 0.00001) {
        using Channel = decltype(Pixel{}.r);
        return Pixel{
            static_cast<Channel>(std::clamp(outR / outA, 0.0, maxVal)),
            static_cast<Channel>(std::clamp(outG / outA, 0.0, maxVal)),
            static_cast<Channel>(std::clamp(outB / outA, 0.0, maxVal)),
            static_cast<Channel>(std::clamp(outA * maxVal, 0.0, maxVal))
        };
    }
    return Pixel{0, 0, 0, 0};
}

template <class Pixel = utils::ColorRGBA>
inline Pixel sampleBicubic(const canvas::PixelBuffer& src, double u, double v) noexcept {
    const int w = src.getWidth();
    const int h = src.getHeight();

    const int px = static_cast<int>(std::floor(u));
    const int py = static_cast<int>(std::floor(v));
    const double fx = u - px;
    const double fy = v - py;

    double weightsX[4], weightsY[4];
    for (int i = 0; i < 4; ++i) {
        weightsX[i] = cubicWeight(fx - (i - 1));
        weightsY[i] = cubicWeight(fy - (i - 1));
    }

    double accR = 0.0, accG = 0.0, accB = 0.0, accA = 0.0;
    double weightSum = 0.0;

    constexpr double maxVal = std::is_same_v<Pixel, utils::ColorRGBA16> ? 65535.0 : 255.0;
    auto getP = [&](int x, int y) {
        if constexpr (std::is_same_v<Pixel, utils::ColorRGBA16>) {
            return src.getPixel16(x, y);
        } else {
            return src.getPixel(x, y);
        }
    };

    for (int j = 0; j < 4; ++j) {
        const int y = std::clamp(py + (j - 1), 0, h - 1);
        const double wy = weightsY[j];

        for (int i = 0; i < 4; ++i) {
            const int x = std::clamp(px + (i - 1), 0, w - 1);
            const double wTotal = wy * weightsX[i];
            weightSum += wTotal;

            const auto c = getP(x, y);
            const double a = c.a / maxVal;
            accR += (c.r * a) * wTotal;
            accG += (c.g * a) * wTotal;
            accB += (c.b * a) * wTotal;
            accA += a * wTotal;
        }
    }

    if (weightSum > 0.0001) {
        accR /= weightSum;
        accG /= weightSum;
        accB /= weightSum;
        accA /= weightSum;
    }

    accA = std::clamp(accA, 0.0, 1.0);
    if (accA > 0.00001) {
        using Channel = decltype(Pixel{}.r);
        return Pixel{
            static_cast<Channel>(std::clamp(accR / accA, 0.0, maxVal)),
            static_cast<Channel>(std::clamp(accG / accA, 0.0, maxVal)),
            static_cast<Channel>(std::clamp(accB / accA, 0.0, maxVal)),
            static_cast<Channel>(std::clamp(accA * maxVal, 0.0, maxVal))
        };
    }
    return Pixel{0, 0, 0, 0};
}

} // namespace aladyn::engine::raster::transform

#endif // ALADYN_ENGINE_TRANSFORM_SAMPLERS_HPP
