#ifndef ALADYN_ENGINE_POINT2D_HPP
#define ALADYN_ENGINE_POINT2D_HPP

#include <cmath>

namespace aladyn::engine::math {

class Point2D {
public:
    double x{0.0};
    double y{0.0};

    constexpr Point2D() noexcept = default;
    constexpr Point2D(double px, double py) noexcept : x(px), y(py) {}

    [[nodiscard]] constexpr double getX() const noexcept { return x; }
    [[nodiscard]] constexpr double getY() const noexcept { return y; }

    constexpr void setX(double px) noexcept { x = px; }
    constexpr void setY(double py) noexcept { y = py; }

    [[nodiscard]] double distanceTo(const Point2D& other) const noexcept {
        const double dx = x - other.x;
        const double dy = y - other.y;
        return std::sqrt(dx * dx + dy * dy);
    }

    [[nodiscard]] double length() const noexcept {
        return std::sqrt(x * x + y * y);
    }

    [[nodiscard]] constexpr bool operator==(const Point2D& other) const noexcept {
        return x == other.x && y == other.y;
    }

    [[nodiscard]] constexpr bool operator!=(const Point2D& other) const noexcept {
        return !(*this == other);
    }

    [[nodiscard]] constexpr Point2D operator+(const Point2D& other) const noexcept {
        return Point2D{x + other.x, y + other.y};
    }

    [[nodiscard]] constexpr Point2D operator-(const Point2D& other) const noexcept {
        return Point2D{x - other.x, y - other.y};
    }

    [[nodiscard]] constexpr Point2D operator*(double scalar) const noexcept {
        return Point2D{x * scalar, y * scalar};
    }

    constexpr Point2D& operator+=(const Point2D& other) noexcept {
        x += other.x;
        y += other.y;
        return *this;
    }

    constexpr Point2D& operator-=(const Point2D& other) noexcept {
        x -= other.x;
        y -= other.y;
        return *this;
    }

    constexpr Point2D& operator*=(double scalar) noexcept {
        x *= scalar;
        y *= scalar;
        return *this;
    }
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_POINT2D_HPP
