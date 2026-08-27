#include "DynamicStabilizer.hpp"
#include <algorithm>

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

    // 1. Dual-Stage Rolling Window (SAI 2 / Clip Studio style)
    const size_t maxWindow = std::clamp(
        static_cast<size_t>(2 + static_cast<int>(m_stabilizationPercentage / 3.0)),
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

    // 2. Weighted center-of-mass averaging across the history window
    double sumX = 0.0, sumY = 0.0, totalWeight = 0.0;
    for (size_t i = 0; i < m_historyCount; ++i) {
        // Linear weight increasing towards newest sample
        const double w = static_cast<double>(i + 1);
        const size_t idx = (m_historyHead + MAX_WINDOW_SIZE + 1 - (m_historyCount - i)) % MAX_WINDOW_SIZE;
        sumX += m_historyBuffer[idx].x * w;
        sumY += m_historyBuffer[idx].y * w;
        totalWeight += w;
    }

    const math::Point2D windowAvg{
        totalWeight > 0.0 ? (sumX / totalWeight) : rawPosition.x,
        totalWeight > 0.0 ? (sumY / totalWeight) : rawPosition.y
    };

    // 3. Spring-mass smooth interpolation towards the window average
    const double interpFactor = std::clamp(1.0 - (m_stabilizationPercentage / 105.0), 0.05, 1.0);
    const math::Point2D delta = windowAvg - m_stabilizedPosition;
    m_stabilizedPosition = m_stabilizedPosition + (delta * interpFactor);
    return m_stabilizedPosition;
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
