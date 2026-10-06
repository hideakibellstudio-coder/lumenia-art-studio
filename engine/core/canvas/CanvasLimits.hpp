#ifndef ALADYN_ENGINE_CANVAS_LIMITS_HPP
#define ALADYN_ENGINE_CANVAS_LIMITS_HPP

#include "PixelFormat.hpp"
#include <stdexcept>
#include <string>

namespace aladyn::engine::canvas {

// Largest side of a canvas, in pixels. One full layer at the limit is
// 16384 x 16384 x 4 bytes = 1 GiB, and the largest pixel index (2^28 - 1)
// times four still fits in a signed 32-bit int, which is what the pixel code
// indexes with. Until 2026-10-01 nothing declared a limit: 32000 x 32000
// overflowed `width * height * 4` in int (undefined behaviour) instead of being
// refused. The interface asks for this value (PaintEngineFacade::maxCanvasDimension)
// and never repeats the number.
inline constexpr int kMaxCanvasDimension = 16384;

// A 16-bit document is limited to 8192 px a side: its composite buffer is 8 bytes a pixel (512 MiB at the limit,
// plus the 8-bit display buffer), and a 16384 x 16384 buffer would be 2^31 bytes, more than the bridge hands out in one
// piece. An 8-bit document keeps 16384.
inline constexpr int kMaxCanvasDimensionRgba16 = 8192;

[[nodiscard]] constexpr int maxCanvasDimension(PixelFormat format) noexcept {
    return format == PixelFormat::RGBA16 ? kMaxCanvasDimensionRgba16 : kMaxCanvasDimension;
}

// Returns `value` when it is a legal canvas side; throws std::invalid_argument
// otherwise (the bridge turns it into ValueError). Called before any allocation.
inline int checkedCanvasDimension(int value, PixelFormat format = PixelFormat::RGBA8) {
    if (value < 1 || value > maxCanvasDimension(format)) {
        throw std::invalid_argument("canvas dimension out of range (1 to " +
                                    std::to_string(maxCanvasDimension(format)) + " px)");
    }
    return value;
}

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_CANVAS_LIMITS_HPP
