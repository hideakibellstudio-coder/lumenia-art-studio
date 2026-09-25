#ifndef ALADYN_ENGINE_BEZIER_CURVE_HPP
#define ALADYN_ENGINE_BEZIER_CURVE_HPP

#include "../../utils/Point2D.hpp"
#include <array>
#include <vector>
#include <cmath>
#include <stdexcept>

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
    BezierCurve(utils::Point2D p0, utils::Point2D p1, utils::Point2D p2, utils::Point2D p3);

    void setControlPoints(utils::Point2D p0, utils::Point2D p1, utils::Point2D p2, utils::Point2D p3);
    void setPreset(CurvePreset preset);
    void setPower(double power);
    void invert();

    [[nodiscard]] double sample(double inputVal) const noexcept;
    [[nodiscard]] const std::array<utils::Point2D, 4>& getControlPoints() const noexcept { return m_controlPoints; }
    [[nodiscard]] const std::array<double, LUT_SIZE>& getLut() const noexcept { return m_lut; }
    void setLut(const std::array<double, LUT_SIZE>& values) {
        for (double value : values) {
            if (!std::isfinite(value)) throw std::invalid_argument("Curve samples must be finite");
        }
        m_lut = values;
    }

private:
    void rebuildLut();

    std::array<utils::Point2D, 4> m_controlPoints;
    std::array<double, LUT_SIZE> m_lut;
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_BEZIER_CURVE_HPP
