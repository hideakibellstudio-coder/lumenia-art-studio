#ifndef ALADYN_ENGINE_VECTOR2D_HPP
#define ALADYN_ENGINE_VECTOR2D_HPP

#include <cmath>

namespace aladyn::engine::math {

class Vector2D {
public:
    double dx{0.0};
    double dy{0.0};

    constexpr Vector2D() noexcept = default;
    constexpr Vector2D(double pdx, double pdy) noexcept : dx(pdx), dy(pdy) {}

    [[nodiscard]] double length() const noexcept {
        return std::sqrt(dx * dx + dy * dy);
    }

    [[nodiscard]] constexpr double lengthSquared() const noexcept {
        return dx * dx + dy * dy;
    }

    [[nodiscard]] Vector2D normalized() const noexcept {
        const double len = length();
        if (len > 1e-9) {
            return Vector2D{dx / len, dy / len};
        }
        return Vector2D{0.0, 0.0};
    }

    [[nodiscard]] constexpr double dot(const Vector2D& other) const noexcept {
        return dx * other.dx + dy * other.dy;
    }

    [[nodiscard]] constexpr Vector2D operator+(const Vector2D& other) const noexcept {
        return Vector2D{dx + other.dx, dy + other.dy};
    }

    [[nodiscard]] constexpr Vector2D operator-(const Vector2D& other) const noexcept {
        return Vector2D{dx - other.dx, dy - other.dy};
    }

    [[nodiscard]] constexpr Vector2D operator*(double scalar) const noexcept {
        return Vector2D{dx * scalar, dy * scalar};
    }
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_VECTOR2D_HPP
