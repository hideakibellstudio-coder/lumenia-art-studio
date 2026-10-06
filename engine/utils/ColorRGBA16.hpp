#ifndef ALADYN_ENGINE_COLOR_RGBA16_HPP
#define ALADYN_ENGINE_COLOR_RGBA16_HPP

// Cor RGBA16 (sRGB, alfa reto): o pixel de um documento de 16 bits por canal. O de 8 bits segue sendo
// `ColorRGBA` (ColorRGBA.hpp); a conversão entre os dois mora em canvas/PixelFormat.hpp.

#include <cstdint>

namespace aladyn::engine::utils {

struct ColorRGBA16 {
    uint16_t r{0};
    uint16_t g{0};
    uint16_t b{0};
    uint16_t a{65535};

    constexpr ColorRGBA16() noexcept = default;
    constexpr ColorRGBA16(uint16_t pr, uint16_t pg, uint16_t pb, uint16_t pa = 65535) noexcept
        : r(pr), g(pg), b(pb), a(pa) {}
};

} // namespace aladyn::engine::utils

#endif // ALADYN_ENGINE_COLOR_RGBA16_HPP
