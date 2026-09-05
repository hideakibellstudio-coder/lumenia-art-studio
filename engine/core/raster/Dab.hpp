#ifndef ALADYN_ENGINE_DAB_HPP
#define ALADYN_ENGINE_DAB_HPP

#include "../math/Point2D.hpp"
#include <cstdint>

namespace aladyn::engine::raster {

enum class DabBlendMode {
    Normal   = 0,  // Alpha Over tradicional
    Multiply = 1,  // Marcador / Feltro de álcool
    Additive = 2,  // Luz / Glow
    Erase    = 3   // Borracha — reduz alpha do destino
};

struct ColorRGBA {
    uint8_t r{0};
    uint8_t g{0};
    uint8_t b{0};
    uint8_t a{255};

    constexpr ColorRGBA() noexcept = default;
    constexpr ColorRGBA(uint8_t pr, uint8_t pg, uint8_t pb, uint8_t pa = 255) noexcept
        : r(pr), g(pg), b(pb), a(pa) {}
};

struct Dab {
    math::Point2D position{0.0, 0.0};
    double radius{1.0};
    double opacity{1.0};
    double pressure{1.0};
    double angle{0.0};
    DabBlendMode blendMode{DabBlendMode::Normal};
    ColorRGBA color{0, 0, 0, 255};
    double aspectRatio{1.0};

    constexpr Dab() noexcept = default;
    constexpr Dab(
        math::Point2D pPos,
        double pRadius,
        double pOpacity,
        double pPressure,
        double pAngle,
        DabBlendMode pBlendMode,
        ColorRGBA pColor,
        double pAspectRatio = 1.0
    ) noexcept
        : position(pPos), radius(pRadius), opacity(pOpacity),
          pressure(pPressure), angle(pAngle), blendMode(pBlendMode), color(pColor),
          aspectRatio(pAspectRatio) {}
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_DAB_HPP
