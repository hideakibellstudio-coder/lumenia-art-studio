#include "VelocityTracker.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::stroke {

VelocityTracker::VelocityTracker(double smoothingSeconds) noexcept
    : m_smoothingSeconds(std::max(smoothingSeconds, 1e-6)) {}

void VelocityTracker::reset(utils::Point2D initialPosition, double timestamp) noexcept {
    m_lastPosition = initialPosition;
    m_windowStart = timestamp;
    m_windowDistance = 0.0;
    m_smoothedVelocity = 0.0;
    m_hasReading = false;
}

double VelocityTracker::update(utils::Point2D currentPosition, double timestamp) noexcept {
    // O caminho acumula a cada evento, inclusive os de timestamp repetido: a mesa gravada
    // (Windows Ink, 59,94 Hz) entrega ~6 eventos por timestamp, e medir só o último passo
    // lia ~1/6 da velocidade real.
    m_windowDistance += m_lastPosition.distanceTo(currentPosition);
    m_lastPosition = currentPosition;

    const double elapsed = timestamp - m_windowStart;
    if (elapsed < 0.0) {
        // Relógio voltou (timestamp fora de ordem): reancora a janela sem inventar velocidade.
        m_windowStart = timestamp;
        return m_smoothedVelocity;
    }
    if (elapsed < kMinWindowSeconds) return m_smoothedVelocity;

    const double measured = std::clamp(m_windowDistance / elapsed, 0.0, kMaxVelocity);
    if (m_hasReading) {
        const double weight = 1.0 - std::exp(-elapsed / m_smoothingSeconds);
        m_smoothedVelocity += (measured - m_smoothedVelocity) * weight;
    } else {
        m_smoothedVelocity = measured;
        m_hasReading = true;
    }
    m_windowStart = timestamp;
    m_windowDistance = 0.0;
    return m_smoothedVelocity;
}

double VelocityTracker::getNormalizedVelocity(double maxVelocity) const noexcept {
    if (maxVelocity <= 0.0) return 0.0;
    return std::clamp(m_smoothedVelocity / maxVelocity, 0.0, 1.0);
}

} // namespace aladyn::engine::stroke
