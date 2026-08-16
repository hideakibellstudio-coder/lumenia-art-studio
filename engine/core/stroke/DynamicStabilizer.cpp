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
}

math::Point2D DynamicStabilizer::update(math::Point2D rawPosition) noexcept {
    const double interpFactor = 1.0 - (m_stabilizationPercentage / 100.0);
    const math::Point2D delta = rawPosition - m_stabilizedPosition;
    m_stabilizedPosition = m_stabilizedPosition + (delta * interpFactor);
    return m_stabilizedPosition;
}

} // namespace aladyn::engine::stroke
