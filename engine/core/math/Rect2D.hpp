#ifndef ALADYN_ENGINE_RECT2D_HPP
#define ALADYN_ENGINE_RECT2D_HPP

#include "Point2D.hpp"
#include <algorithm>

namespace aladyn::engine::math {

class Rect2D {
public:
    double x{0.0};
    double y{0.0};
    double width{0.0};
    double height{0.0};

    constexpr Rect2D() noexcept = default;
    constexpr Rect2D(double px, double py, double pwidth, double pheight) noexcept
        : x(px), y(py), width(pwidth), height(pheight) {}

    [[nodiscard]] constexpr double getLeft() const noexcept { return x; }
    [[nodiscard]] constexpr double getTop() const noexcept { return y; }
    [[nodiscard]] constexpr double getRight() const noexcept { return x + width; }
    [[nodiscard]] constexpr double getBottom() const noexcept { return y + height; }

    [[nodiscard]] constexpr bool contains(const Point2D& point) const noexcept {
        return point.x >= x && point.x <= (x + width) &&
               point.y >= y && point.y <= (y + height);
    }

    [[nodiscard]] constexpr bool intersects(const Rect2D& other) const noexcept {
        return !(other.getLeft() > getRight() ||
                 other.getRight() < getLeft() ||
                 other.getTop() > getBottom() ||
                 other.getBottom() < getTop());
    }

    [[nodiscard]] Rect2D united(const Rect2D& other) const noexcept {
        const double x1 = std::min(getLeft(), other.getLeft());
        const double y1 = std::min(getTop(), other.getTop());
        const double x2 = std::max(getRight(), other.getRight());
        const double y2 = std::max(getBottom(), other.getBottom());
        return Rect2D{x1, y1, x2 - x1, y2 - y1};
    }
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_RECT2D_HPP
