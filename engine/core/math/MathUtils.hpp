#ifndef ALADYN_ENGINE_MATH_UTILS_HPP
#define ALADYN_ENGINE_MATH_UTILS_HPP

#include <algorithm>
#include <cmath>

namespace aladyn::engine::math {

class MathUtils {
public:
    static inline double clamp(double val, double minVal, double maxVal) noexcept {
        return std::clamp(val, minVal, maxVal);
    }

    static inline double lerp(double a, double b, double t) noexcept {
        return a + (b - a) * t;
    }

    static inline double smoothstep(double edge0, double edge1, double x) noexcept {
        if (edge0 >= edge1) {
            return x >= edge0 ? 1.0 : 0.0;
        }
        const double t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0);
        return t * t * (3.0 - 2.0 * t);
    }
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_MATH_UTILS_HPP
