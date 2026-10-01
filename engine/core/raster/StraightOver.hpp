#ifndef ALADYN_ENGINE_STRAIGHT_OVER_HPP
#define ALADYN_ENGINE_STRAIGHT_OVER_HPP

#include "../../utils/ColorRGBA.hpp"
#include <algorithm>
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
            static_cast<uint8_t>(std::clamp((color.r * strength + dst.r * dstA * inverse) / denominator, 0.0, 255.0)),
            static_cast<uint8_t>(std::clamp((color.g * strength + dst.g * dstA * inverse) / denominator, 0.0, 255.0)),
            static_cast<uint8_t>(std::clamp((color.b * strength + dst.b * dstA * inverse) / denominator, 0.0, 255.0)),
            dst.a
        };
        return true;
    }

    const double outA = strength + dstA * inverse;
    if (outA <= 0.0) return false;
    dst = utils::ColorRGBA{
        static_cast<uint8_t>(std::clamp((color.r * strength + dst.r * dstA * inverse) / outA, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp((color.g * strength + dst.g * dstA * inverse) / outA, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp((color.b * strength + dst.b * dstA * inverse) / outA, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(outA * 255.0, 0.0, 255.0))
    };
    return true;
}

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_STRAIGHT_OVER_HPP
