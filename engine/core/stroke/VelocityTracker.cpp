#include "VelocityTracker.hpp"
#include <algorithm>

namespace aladyn::engine::stroke {

VelocityTracker::VelocityTracker(double smoothingFactor) noexcept
    : m_smoothingFactor(smoothingFactor) {}

void VelocityTracker::reset(utils::Point2D initialPosition, double timestamp) noexcept {
    m_lastPosition = initialPosition;
    m_lastTimestamp = timestamp;
    m_smoothedVelocity = 0.0;
}

double VelocityTracker::update(utils::Point2D currentPosition, double timestamp) noexcept {
    const double dt = timestamp - m_lastTimestamp;
    if (dt > 0.0) {
        const double distance = m_lastPosition.distanceTo(currentPosition);
        // Piso temporal de 0.8ms (~1250Hz) para blindar contra rajadas de fila do SO (queue bursting)
        // sem achatar a velocidade física de mesas digitalizadoras e mouses gamer de alta taxa (500Hz-1000Hz)
        const double effectiveDt = std::max(dt, 0.0008);
        // Teto de velocidade física humana para evitar contaminação do rastreador
        const double immediateVelocity = std::clamp(distance / effectiveDt, 0.0, 3500.0);
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
