#ifndef ALADYN_ENGINE_STRAIGHT_OVER_HPP
#define ALADYN_ENGINE_STRAIGHT_OVER_HPP

#include "../../utils/ColorRGBA.hpp"
#include "../../utils/ColorRGBA16.hpp"
#include "../../utils/MathUtils.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace aladyn::engine::raster {

// Alfa "over" em canais de 8 bits, sem gama linear: o depósito de tinta comum dos motores que não
// têm uma física própria de mistura (Lápis, Caneta, Borrar).
//
// `strength` é o alfa do depósito (0 a 1). Com Alpha Lock a cor entra e o alfa do destino fica; sem
// ele, o alfa soma. Devolve true quando o pixel mudou.
[[nodiscard]] inline bool straightOver(
    utils::ColorRGBA& dst, utils::ColorRGBA color, double strength, bool alphaLocked
) noexcept {
    const double dstA = static_cast<double>(dst.a) / 255.0;
    const double inverse = 1.0 - strength;

    if (alphaLocked) {
        if (dst.a == 0) return false;
        const double denominator = strength + dstA * inverse;
        if (denominator <= 0.0) return false;
        dst = utils::ColorRGBA{
            utils::MathUtils::roundToByte((color.r * strength + dst.r * dstA * inverse) / denominator),
            utils::MathUtils::roundToByte((color.g * strength + dst.g * dstA * inverse) / denominator),
            utils::MathUtils::roundToByte((color.b * strength + dst.b * dstA * inverse) / denominator),
            dst.a
        };
        return true;
    }

    const double outA = strength + dstA * inverse;
    if (outA <= 0.0) return false;
    dst = utils::ColorRGBA{
        utils::MathUtils::roundToByte((color.r * strength + dst.r * dstA * inverse) / outA),
        utils::MathUtils::roundToByte((color.g * strength + dst.g * dstA * inverse) / outA),
        utils::MathUtils::roundToByte((color.b * strength + dst.b * dstA * inverse) / outA),
        utils::MathUtils::roundToByte(outA * 255.0)
    };
    return true;
}

[[nodiscard]] inline bool straightOver(
    utils::ColorRGBA16& dst, utils::ColorRGBA16 color, double strength, bool alphaLocked
) noexcept {
    const double dstA = static_cast<double>(dst.a) / 65535.0;
    const double inverse = 1.0 - strength;

    const auto roundToWord = [](double val) noexcept -> uint16_t {
        return static_cast<uint16_t>(std::clamp(std::lround(val), 0L, 65535L));
    };

    if (alphaLocked) {
        if (dst.a == 0) return false;
        const double denominator = strength + dstA * inverse;
        if (denominator <= 0.0) return false;
        dst = utils::ColorRGBA16{
            roundToWord((color.r * strength + dst.r * dstA * inverse) / denominator),
            roundToWord((color.g * strength + dst.g * dstA * inverse) / denominator),
            roundToWord((color.b * strength + dst.b * dstA * inverse) / denominator),
            dst.a
        };
        return true;
    }

    const double outA = strength + dstA * inverse;
    if (outA <= 0.0) return false;
    dst = utils::ColorRGBA16{
        roundToWord((color.r * strength + dst.r * dstA * inverse) / outA),
        roundToWord((color.g * strength + dst.g * dstA * inverse) / outA),
        roundToWord((color.b * strength + dst.b * dstA * inverse) / outA),
        roundToWord(outA * 65535.0)
    };
    return true;
}

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_STRAIGHT_OVER_HPP
