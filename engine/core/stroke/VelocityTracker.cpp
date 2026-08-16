#include "VelocityTracker.hpp"
#include <algorithm>

namespace aladyn::engine::stroke {

VelocityTracker::VelocityTracker(double smoothingFactor) noexcept
    : m_smoothingFactor(smoothingFactor) {}

void VelocityTracker::reset(math::Point2D initialPosition, double timestamp) noexcept {
    m_lastPosition = initialPosition;
    m_lastTimestamp = timestamp;
    m_smoothedVelocity = 0.0;
}

double VelocityTracker::update(math::Point2D currentPosition, double timestamp) noexcept {
    const double dt = timestamp - m_lastTimestamp;
    if (dt > 0.0) {
        const double distance = m_lastPosition.distanceTo(currentPosition);
        const double immediateVelocity = distance / dt;
        m_smoothedVelocity = (m_smoothedVelocity * (1.0 - m_smoothingFactor)) + (immediateVelocity * m_smoothingFactor);
    }
    m_lastPosition = currentPosition;
    m_lastTimestamp = timestamp;
    return m_smoothedVelocity;
}

double VelocityTracker::getNormalizedVelocity(double maxVelocity) const noexcept {
    if (maxVelocity <= 0.0) return 0.0;
    return std::clamp(m_smoothedVelocity / maxVelocity, 0.0, 1.0);
}

} // namespace aladyn::engine::stroke
