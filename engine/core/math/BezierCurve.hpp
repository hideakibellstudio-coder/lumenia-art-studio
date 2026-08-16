#ifndef ALADYN_ENGINE_BEZIER_CURVE_HPP
#define ALADYN_ENGINE_BEZIER_CURVE_HPP

#include "Point2D.hpp"
#include <array>
#include <vector>

namespace aladyn::engine::math {

enum class CurvePreset {
    Linear,
    Soft,
    Hard,
    S,
    Threshold
};

class BezierCurve {
public:
    static constexpr size_t LUT_SIZE = 256;

    BezierCurve();
    explicit BezierCurve(CurvePreset preset);
    BezierCurve(Point2D p0, Point2D p1, Point2D p2, Point2D p3);

    void setControlPoints(Point2D p0, Point2D p1, Point2D p2, Point2D p3);
    void setPreset(CurvePreset preset);
    void invert();

    [[nodiscard]] double sample(double inputVal) const noexcept;
    [[nodiscard]] const std::array<Point2D, 4>& getControlPoints() const noexcept { return m_controlPoints; }
    [[nodiscard]] const std::array<double, LUT_SIZE>& getLut() const noexcept { return m_lut; }

private:
    void rebuildLut();

    std::array<Point2D, 4> m_controlPoints;
    std::array<double, LUT_SIZE> m_lut;
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_BEZIER_CURVE_HPP
