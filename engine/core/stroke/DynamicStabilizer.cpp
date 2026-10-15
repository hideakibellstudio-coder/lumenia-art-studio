#include "DynamicStabilizer.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::stroke {

namespace {
    constexpr size_t kMinEvents = 3;
    constexpr size_t kMaxEvents = 72;
    // A drain step gives up this close to the release point and lands on it exactly.
    constexpr double kArrivedPx = 0.35;
}

DynamicStabilizer::DynamicStabilizer(double stabilizationPercentage) noexcept
    : m_stabilizationPercentage(std::clamp(stabilizationPercentage, 0.0, 99.0)) {}

void DynamicStabilizer::setStabilizationPercentage(double percentage) noexcept {
    m_stabilizationPercentage = std::clamp(percentage, 0.0, 99.0);
}

double DynamicStabilizer::windowSeconds() const noexcept {
    const double norm = std::clamp(m_stabilizationPercentage / 100.0, 0.0, 1.0);
    // Janela temporal calibrada: ~17 ms (0%) até ~260 ms (99%).
    // Proporciona filtragem progressiva e profunda na faixa 25%-70% sem cortar curvas.
    const double events = 6.0 + 84.0 * std::pow(norm, 1.25);
    return events * kNominalEventSeconds;
}

void DynamicStabilizer::reset(utils::Point2D initialPosition, double initialPressure) noexcept {
    reset(initialPosition, initialPressure, 0.0);
}

void DynamicStabilizer::reset(utils::Point2D initialPosition, double initialPressure, double timestamp) noexcept {
    m_stabilizedPosition = initialPosition;
    m_stabilizedPressure = initialPressure;
    m_lastMovementDelta = {0.0, 0.0};
    m_count = 1;
    m_head = 0;
    m_updates = 0;
    m_lastNormalizedVelocity = 0.0;
    m_lastTime = timestamp > 0.0 ? timestamp : 0.0;
    if (timestamp > 0.0) m_clock.begin(timestamp);
    m_samples[0] = {initialPosition, initialPressure, m_lastTime};
}

const DynamicStabilizer::Sample& DynamicStabilizer::sampleAt(size_t fromOldest) const noexcept {
    return m_samples[(m_head + MAX_SAMPLES + 1 - m_count + fromOldest) % MAX_SAMPLES];
}

void DynamicStabilizer::push(const Sample& sample) noexcept {
    m_head = (m_head + 1) % MAX_SAMPLES;
    m_samples[m_head] = sample;
    m_count = std::min(m_count + 1, MAX_SAMPLES);
    m_lastTime = sample.time;
}

void DynamicStabilizer::fillGap(double until, utils::Point2D to, double toPressure) noexcept {
    if (m_count == 0 || until - m_lastTime <= kStillGapSeconds) return;
    const Sample from = m_samples[m_head];
    const double span = until - from.time;
    // Older than the window they would leave at once: start where they still count.
    double t = std::max(from.time + kStillStepSeconds, until - windowSeconds());
    for (; t < until - kStillStepSeconds * 0.5; t += kStillStepSeconds) {
        const double k = (t - from.time) / span;
        push({from.position + (to - from.position) * k, from.pressure + (toPressure - from.pressure) * k, t});
    }
}

void DynamicStabilizer::expire(double now, double window) noexcept {
    while (m_count > 1 && now - sampleAt(0).time >= window) --m_count;
}

void DynamicStabilizer::average(double now, double normalizedVelocity) noexcept {
    const double norm = std::clamp(m_stabilizationPercentage / 100.0, 0.0, 1.0);
    // Expoente progressivo: a ponta recente sempre tem peso dominante (>= 2.2).
    // Evita o arrasto lento e pegajoso de peso morto ao aumentar a estabilização.
    double exponent = 2.2 + 0.6 * norm;
    if (m_updates > 4 && normalizedVelocity > 0.40) {
        exponent += std::clamp((normalizedVelocity - 0.40) / 0.60, 0.0, 1.0) * 0.5;
    }
    const double window = windowSeconds();
    double sumX = 0.0, sumY = 0.0, sumPressure = 0.0, totalWeight = 0.0;
    for (size_t i = 0; i < m_count; ++i) {
        const Sample& s = sampleAt(i);
        const double remaining = 1.0 - (now - s.time) / window;
        if (remaining <= 0.0) continue;
        const double w = std::pow(remaining, exponent);
        sumX += s.position.x * w;
        sumY += s.position.y * w;
        sumPressure += s.pressure * w;
        totalWeight += w;
    }
    const Sample& newest = m_samples[m_head];
    const utils::Point2D next = totalWeight > 0.0
        ? utils::Point2D{sumX / totalWeight, sumY / totalWeight} : newest.position;
    m_stabilizedPressure = totalWeight > 0.0 ? sumPressure / totalWeight : newest.pressure;
    const utils::Point2D delta = next - m_stabilizedPosition;
    if (delta.length() > 0.05) m_lastMovementDelta = delta;
    m_stabilizedPosition = next;
}

void DynamicStabilizer::reanchorInitialPosition(utils::Point2D newInitialPosition) noexcept {
    if (m_count == 0) {
        reset(newInitialPosition, m_stabilizedPressure);
        return;
    }
    m_samples[(m_head + MAX_SAMPLES + 1 - m_count) % MAX_SAMPLES].position = newInitialPosition;
    if (m_count == 2) {
        average(m_lastTime, 0.0);
        m_lastMovementDelta = m_stabilizedPosition - newInitialPosition;
    }
}

utils::Point2D DynamicStabilizer::updateAt(utils::Point2D rawPosition, double rawPressure,
                                           double normalizedVelocity, double timestamp) noexcept {
    const double now = timestamp > 0.0 ? std::max(m_clock.place(timestamp), m_lastTime)
                                       : m_lastTime + kNominalEventSeconds;
    if (!isActive()) {
        m_lastMovementDelta = rawPosition - m_stabilizedPosition;
        m_stabilizedPosition = rawPosition;
        m_stabilizedPressure = rawPressure;
        push({rawPosition, rawPressure, now});
        return rawPosition;
    }
    fillGap(now, rawPosition, rawPressure);
    push({rawPosition, rawPressure, now});
    ++m_updates;
    m_lastNormalizedVelocity = normalizedVelocity;
    expire(now, windowSeconds());
    average(now, normalizedVelocity);
    return m_stabilizedPosition;
}

utils::Point2D DynamicStabilizer::update(utils::Point2D rawPosition, double rawPressure, double normalizedVelocity) noexcept {
    return updateAt(rawPosition, rawPressure, normalizedVelocity, 0.0);
}

utils::Point2D DynamicStabilizer::update(utils::Point2D rawPosition, double normalizedVelocity) noexcept {
    return updateAt(rawPosition, m_stabilizedPressure, normalizedVelocity, 0.0);
}

std::vector<DynamicStabilizer::Node> DynamicStabilizer::drain(utils::Point2D endPosition, double endPressure,
                                                              size_t maxNodes) noexcept {
    std::vector<Node> nodes;
    if (!isActive()) {
        m_lastMovementDelta = endPosition - m_stabilizedPosition;
        m_stabilizedPosition = endPosition;
        m_stabilizedPressure = endPressure;
        nodes.push_back({endPosition, endPressure});
        return nodes;
    }
    const size_t steps = std::clamp(maxNodes, static_cast<size_t>(2), static_cast<size_t>(64));
    const double window = windowSeconds();
    const double step = window / static_cast<double>(steps);
    nodes.reserve(steps + 1);
    for (size_t k = 0; k < steps; ++k) {
        if (m_stabilizedPosition.distanceTo(endPosition) < kArrivedPx) break;
        const double now = m_lastTime + step;
        push({endPosition, endPressure, now});
        expire(now, window);
        average(now, m_lastNormalizedVelocity);
        nodes.push_back({m_stabilizedPosition, m_stabilizedPressure});
    }
    if (nodes.empty() || nodes.back().position != endPosition) {
        const utils::Point2D delta = endPosition - m_stabilizedPosition;
        if (delta.length() > 0.05) m_lastMovementDelta = delta;
        m_stabilizedPosition = endPosition;
        m_stabilizedPressure = endPressure;
        if (!nodes.empty() && nodes.back().position.distanceTo(endPosition) < kArrivedPx) nodes.pop_back();
        nodes.push_back({endPosition, endPressure});
    }
    return nodes;
}

std::vector<utils::Point2D> DynamicStabilizer::flush(utils::Point2D endPosition, size_t steps) noexcept {
    std::vector<utils::Point2D> catchupPoints;
    if (m_stabilizationPercentage <= 0.5) {
        m_lastMovementDelta = endPosition - m_stabilizedPosition;
        m_stabilizedPosition = endPosition;
        catchupPoints.push_back(endPosition);
        return catchupPoints;
    }

    const size_t maxSteps = std::clamp(steps, static_cast<size_t>(2), static_cast<size_t>(12));
    catchupPoints.reserve(maxSteps);

    for (size_t s = 0; s < maxSteps; ++s) {
        const utils::Point2D delta = endPosition - m_stabilizedPosition;
        if (delta.length() < 0.25) {
            m_lastMovementDelta = endPosition - m_stabilizedPosition;
            m_stabilizedPosition = endPosition;
            catchupPoints.push_back(endPosition);
            break;
        }
        const double stepProgress = static_cast<double>(s + 1) / static_cast<double>(maxSteps);
        const double factor = std::clamp(0.40 + 0.55 * (stepProgress * stepProgress), 0.40, 0.95);
        const utils::Point2D nextPos = m_stabilizedPosition + (delta * factor);
        m_lastMovementDelta = nextPos - m_stabilizedPosition;
        m_stabilizedPosition = nextPos;
        catchupPoints.push_back(m_stabilizedPosition);
    }

    if (catchupPoints.empty() || catchupPoints.back() != endPosition) {
        m_lastMovementDelta = endPosition - m_stabilizedPosition;
        m_stabilizedPosition = endPosition;
        catchupPoints.push_back(endPosition);
    }

    return catchupPoints;
}

std::vector<utils::Point2D> DynamicStabilizer::getTaperPoints(size_t steps, double maxDistance) noexcept {
    std::vector<utils::Point2D> pts;
    const double speed = m_lastMovementDelta.length();
    // Se o traço parou antes de levantar a caneta, não gera cauda de flick
    if (speed < 0.3) {
        return pts;
    }

    const size_t numSteps = std::clamp(steps, static_cast<size_t>(2), static_cast<size_t>(8));
    pts.reserve(numSteps);

    const utils::Point2D dir = m_lastMovementDelta * (1.0 / speed);
    const double distLimit = maxDistance > 0.0 ? maxDistance : 25.0;
    const double totalDist = std::clamp(speed * 1.5, 2.0, distLimit);

    for (size_t i = 1; i <= numSteps; ++i) {
        const double progress = static_cast<double>(i) / static_cast<double>(numSteps);
        const double eased = 1.0 - std::pow(1.0 - progress, 1.3);
        pts.push_back(m_stabilizedPosition + dir * (totalDist * eased));
    }

    return pts;
}

utils::Point2D DynamicStabilizer::predictPosition(utils::Point2D currentPos, utils::Point2D velocity) const noexcept {
    if (!m_predictionEnabled) return currentPos;
    const double dtSec = m_aheadMs / 1000.0;
    return utils::Point2D{
        currentPos.x + velocity.x * dtSec,
        currentPos.y + velocity.y * dtSec
    };
}

} // namespace aladyn::engine::stroke
