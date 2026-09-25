#ifndef ALADYN_ENGINE_COLOR_RGBA_HPP
#define ALADYN_ENGINE_COLOR_RGBA_HPP

// Cor RGBA8 (sRGB, alfa reto): o tipo de pixel do motor inteiro.

#include <cstdint>

namespace aladyn::engine::utils {

struct ColorRGBA {
    uint8_t r{0};
    uint8_t g{0};
    uint8_t b{0};
    uint8_t a{255};

    constexpr ColorRGBA() noexcept = default;
    constexpr ColorRGBA(uint8_t pr, uint8_t pg, uint8_t pb, uint8_t pa = 255) noexcept
        : r(pr), g(pg), b(pb), a(pa) {}
};

} // namespace aladyn::engine::utils

#endif // ALADYN_ENGINE_COLOR_RGBA_HPP
