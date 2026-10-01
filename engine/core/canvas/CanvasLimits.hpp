#ifndef ALADYN_ENGINE_CANVAS_LIMITS_HPP
#define ALADYN_ENGINE_CANVAS_LIMITS_HPP

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

// Returns `value` when it is a legal canvas side; throws std::invalid_argument
// otherwise (the bridge turns it into ValueError). Called before any allocation.
inline int checkedCanvasDimension(int value) {
    if (value < 1 || value > kMaxCanvasDimension) {
        throw std::invalid_argument("canvas dimension out of range (1 to " +
                                    std::to_string(kMaxCanvasDimension) + " px)");
    }
    return value;
}

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_CANVAS_LIMITS_HPP
