#include "BezierCurve.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace aladyn::engine::math {

BezierCurve::BezierCurve() {
    setPreset(CurvePreset::Linear);
}

BezierCurve::BezierCurve(CurvePreset preset) {
    setPreset(preset);
}

BezierCurve::BezierCurve(Point2D p0, Point2D p1, Point2D p2, Point2D p3) {
    setControlPoints(p0, p1, p2, p3);
}

void BezierCurve::setControlPoints(Point2D p0, Point2D p1, Point2D p2, Point2D p3) {
    m_controlPoints[0] = p0;
    m_controlPoints[1] = p1;
    m_controlPoints[2] = p2;
    m_controlPoints[3] = p3;
    rebuildLut();
}

void BezierCurve::setPreset(CurvePreset preset) {
    switch (preset) {
        case CurvePreset::Linear:
            setControlPoints({0.0, 0.0}, {0.33, 0.33}, {0.66, 0.66}, {1.0, 1.0});
            break;
        case CurvePreset::Soft:
            setControlPoints({0.0, 0.0}, {0.12, 0.52}, {0.50, 0.88}, {1.0, 1.0});
            break;
        case CurvePreset::Hard:
            setControlPoints({0.0, 0.0}, {0.45, 0.10}, {0.85, 0.45}, {1.0, 1.0});
            break;
        case CurvePreset::S:
            setControlPoints({0.0, 0.0}, {0.18, 0.04}, {0.82, 0.96}, {1.0, 1.0});
            break;
        case CurvePreset::Threshold:
            setControlPoints({0.0, 0.0}, {0.48, 0.00}, {0.52, 1.00}, {1.0, 1.0});
            break;
    }
}

void BezierCurve::invert() {
    for (auto& pt : m_controlPoints) {
        pt.y = 1.0 - pt.y;
    }
    rebuildLut();
}

void BezierCurve::setPower(double power) {
    if (!std::isfinite(power) || power <= 0.0) {
        throw std::invalid_argument("pressure power must be finite and positive");
    }
    for (size_t i = 0; i < LUT_SIZE; ++i) {
        const double x = static_cast<double>(i) / (LUT_SIZE - 1);
        m_lut[i] = std::pow(x, power);
    }
    m_controlPoints = {Point2D{0.0, 0.0}, Point2D{1.0 / 3.0, std::pow(1.0 / 3.0, power)},
                      Point2D{2.0 / 3.0, std::pow(2.0 / 3.0, power)}, Point2D{1.0, 1.0}};
}

void BezierCurve::rebuildLut() {
    const auto& p = m_controlPoints;
    for (size_t i = 0; i < LUT_SIZE; ++i) {
        const double t = static_cast<double>(i) / static_cast<double>(LUT_SIZE - 1);
        const double oneMinusT = 1.0 - t;
        
        const double y = (oneMinusT * oneMinusT * oneMinusT * p[0].y)
                       + (3.0 * oneMinusT * oneMinusT * t * p[1].y)
                       + (3.0 * oneMinusT * t * t * p[2].y)
                       + (t * t * t * p[3].y);
        
        m_lut[i] = std::clamp(y, 0.0, 1.0);
    }
}

double BezierCurve::sample(double inputVal) const noexcept {
    const double clampedInput = std::clamp(inputVal, 0.0, 1.0);
    const size_t idx = static_cast<size_t>(clampedInput * static_cast<double>(LUT_SIZE - 1));
    return m_lut[idx];
}

} // namespace aladyn::engine::math
