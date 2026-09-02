#include "DynamicStabilizer.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::stroke {

DynamicStabilizer::DynamicStabilizer(double stabilizationPercentage) noexcept
    : m_stabilizationPercentage(std::clamp(stabilizationPercentage, 0.0, 99.0)) {}

void DynamicStabilizer::setStabilizationPercentage(double percentage) noexcept {
    m_stabilizationPercentage = std::clamp(percentage, 0.0, 99.0);
}

void DynamicStabilizer::reset(math::Point2D initialPosition) noexcept {
    m_stabilizedPosition = initialPosition;
    m_historyCount = 1;
    m_historyHead = 0;
    m_historyBuffer[0] = initialPosition;
}

math::Point2D DynamicStabilizer::update(math::Point2D rawPosition) noexcept {
    if (m_stabilizationPercentage <= 0.5) {
        m_stabilizedPosition = rawPosition;
        return rawPosition;
    }

    // 1. Perceptual curve: 0..100% mapped smoothly across low/mid/high sensitivity
    const double norm = std::clamp(m_stabilizationPercentage / 100.0, 0.0, 1.0);
    const double curved = norm * norm; // Quadratic perceptual ramp

    // 2. Rolling Window size based on perceptual curve
    const size_t maxWindow = std::clamp(
        static_cast<size_t>(2 + static_cast<int>(curved * (MAX_WINDOW_SIZE - 2))),
        static_cast<size_t>(2),
        MAX_WINDOW_SIZE
    );

    m_historyHead = (m_historyHead + 1) % MAX_WINDOW_SIZE;
    m_historyBuffer[m_historyHead] = rawPosition;
    if (m_historyCount < maxWindow) {
        ++m_historyCount;
    } else {
        m_historyCount = maxWindow;
    }

    // 3. Weighted center-of-mass averaging with exponential recency weighting (Zero-Cost LUT)
    static const auto WEIGHT_LUT = []() {
        std::array<double, MAX_WINDOW_SIZE> arr{};
        for (size_t k = 0; k < MAX_WINDOW_SIZE; ++k) {
            arr[k] = std::pow(static_cast<double>(k + 1), 1.25);
        }
        return arr;
    }();

    double sumX = 0.0, sumY = 0.0, totalWeight = 0.0;
    for (size_t i = 0; i < m_historyCount; ++i) {
        const double w = WEIGHT_LUT[i];
        const size_t idx = (m_historyHead + MAX_WINDOW_SIZE + 1 - (m_historyCount - i)) % MAX_WINDOW_SIZE;
        sumX += m_historyBuffer[idx].x * w;
        sumY += m_historyBuffer[idx].y * w;
        totalWeight += w;
    }

    const math::Point2D windowAvg{
        totalWeight > 0.0 ? (sumX / totalWeight) : rawPosition.x,
        totalWeight > 0.0 ? (sumY / totalWeight) : rawPosition.y
    };

    // 4. Smooth spring-mass interpolation with adaptive responsiveness
    const double interpFactor = std::clamp(std::pow(1.0 - norm * 0.92, 1.6), 0.035, 1.0);
    const math::Point2D delta = windowAvg - m_stabilizedPosition;
    m_stabilizedPosition = m_stabilizedPosition + (delta * interpFactor);
    return m_stabilizedPosition;
}

std::vector<math::Point2D> DynamicStabilizer::flush(math::Point2D endPosition, size_t steps) noexcept {
    std::vector<math::Point2D> catchupPoints;
    if (m_stabilizationPercentage <= 0.5 || steps == 0) {
        m_stabilizedPosition = endPosition;
        catchupPoints.push_back(endPosition);
        return catchupPoints;
    }

    catchupPoints.reserve(steps);
    for (size_t i = 1; i <= steps; ++i) {
        const double t = static_cast<double>(i) / static_cast<double>(steps);
        const double smoothT = t * t * (3.0 - 2.0 * t); // Smoothstep
        math::Point2D pt = m_stabilizedPosition + (endPosition - m_stabilizedPosition) * smoothT;
        catchupPoints.push_back(pt);
    }
    m_stabilizedPosition = endPosition;
    return catchupPoints;
}

math::Point2D DynamicStabilizer::predictPosition(math::Point2D currentPos, math::Point2D velocity) const noexcept {
    if (!m_predictionEnabled) return currentPos;
    const double dtSec = m_aheadMs / 1000.0;
    return math::Point2D{
        currentPos.x + velocity.x * dtSec,
        currentPos.y + velocity.y * dtSec
    };
}

} // namespace aladyn::engine::stroke
