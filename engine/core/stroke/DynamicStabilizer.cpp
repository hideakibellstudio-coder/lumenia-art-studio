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
    m_lastMovementDelta = {0.0, 0.0};
    m_historyCount = 1;
    m_historyHead = 0;
    m_historyBuffer[0] = initialPosition;
}

void DynamicStabilizer::reanchorInitialPosition(math::Point2D newInitialPosition) noexcept {
    if (m_historyCount == 0) {
        reset(newInitialPosition);
        return;
    }
    const size_t oldestIdx = (m_historyHead + MAX_WINDOW_SIZE + 1 - m_historyCount) % MAX_WINDOW_SIZE;
    m_historyBuffer[oldestIdx] = newInitialPosition;

    if (m_historyCount == 2) {
        const double norm = std::clamp(m_stabilizationPercentage / 100.0, 0.0, 1.0);
        const double exponent = 2.4 - 1.3 * std::pow(norm, 0.85);
        const double w0 = std::pow(1.0, exponent);
        const double w1 = std::pow(2.0, exponent);
        const double totalW = w0 + w1;
        const auto& p1 = m_historyBuffer[m_historyHead];
        m_stabilizedPosition = {
            (newInitialPosition.x * w0 + p1.x * w1) / totalW,
            (newInitialPosition.y * w0 + p1.y * w1) / totalW
        };
        m_lastMovementDelta = m_stabilizedPosition - newInitialPosition;
    }
}

math::Point2D DynamicStabilizer::update(math::Point2D rawPosition, double normalizedVelocity) noexcept {
    if (m_stabilizationPercentage <= 0.5) {
        m_lastMovementDelta = rawPosition - m_stabilizedPosition;
        m_stabilizedPosition = rawPosition;
        return rawPosition;
    }

    const double norm = std::clamp(m_stabilizationPercentage / 100.0, 0.0, 1.0);
    const size_t maxWindow = std::clamp(
        static_cast<size_t>(3 + static_cast<int>(std::round(norm * 69.0))),
        static_cast<size_t>(3),
        MAX_WINDOW_SIZE
    );

    // 1. Atualiza buffer circular de histórico
    m_historyHead = (m_historyHead + 1) % MAX_WINDOW_SIZE;
    m_historyBuffer[m_historyHead] = rawPosition;
    if (m_historyCount < maxWindow) {
        ++m_historyCount;
    } else {
        m_historyCount = maxWindow;
    }

    // 2. Expoente de peso WMA adaptativo com Velocity Bypass
    // Suprimido nas primeiras 4 amostras para garantir entrada de traço perfeitamente uniforme e estável.
    // Nas amostras subsequentes, usa fator suave (0.4) para evitar solavancos no centróide.
    double exponent = 2.4 - 1.3 * std::pow(norm, 0.85);
    if (m_historyCount > 4 && normalizedVelocity > 0.50) {
        const double vFactor = std::clamp((normalizedVelocity - 0.50) / 0.50, 0.0, 1.0);
        exponent += vFactor * 0.4;
    }

    // 3. Média Ponderada Temporal Pura (WMA - Padrão Paint Tool SAI)
    // Calcula o centróide ponderado diretamente sobre a janela de amostras.
    // Garante C1-continuidade desde o primeiro frame, eliminando dead-bands e desvios no toque inicial.
    double sumX = 0.0, sumY = 0.0, totalWeight = 0.0;
    for (size_t i = 0; i < m_historyCount; ++i) {
        const double w = std::pow(static_cast<double>(i + 1), exponent);
        const size_t idx = (m_historyHead + MAX_WINDOW_SIZE + 1 - (m_historyCount - i)) % MAX_WINDOW_SIZE;
        sumX += m_historyBuffer[idx].x * w;
        sumY += m_historyBuffer[idx].y * w;
        totalWeight += w;
    }

    const math::Point2D newPos{
        totalWeight > 0.0 ? (sumX / totalWeight) : rawPosition.x,
        totalWeight > 0.0 ? (sumY / totalWeight) : rawPosition.y
    };

    const math::Point2D delta = newPos - m_stabilizedPosition;
    if (delta.length() > 0.05) {
        m_lastMovementDelta = delta;
    }
    m_stabilizedPosition = newPos;
    return m_stabilizedPosition;
}

std::vector<math::Point2D> DynamicStabilizer::flush(math::Point2D endPosition, size_t steps) noexcept {
    std::vector<math::Point2D> catchupPoints;
    if (m_stabilizationPercentage <= 0.5) {
        m_lastMovementDelta = endPosition - m_stabilizedPosition;
        m_stabilizedPosition = endPosition;
        catchupPoints.push_back(endPosition);
        return catchupPoints;
    }

    const size_t maxSteps = std::clamp(steps, static_cast<size_t>(2), static_cast<size_t>(12));
    catchupPoints.reserve(maxSteps);

    for (size_t s = 0; s < maxSteps; ++s) {
        const math::Point2D delta = endPosition - m_stabilizedPosition;
        if (delta.length() < 0.25) {
            m_lastMovementDelta = endPosition - m_stabilizedPosition;
            m_stabilizedPosition = endPosition;
            catchupPoints.push_back(endPosition);
            break;
        }
        const double stepProgress = static_cast<double>(s + 1) / static_cast<double>(maxSteps);
        const double factor = std::clamp(0.40 + 0.55 * (stepProgress * stepProgress), 0.40, 0.95);
        const math::Point2D nextPos = m_stabilizedPosition + (delta * factor);
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

std::vector<math::Point2D> DynamicStabilizer::getTaperPoints(size_t steps, double maxDistance) noexcept {
    std::vector<math::Point2D> pts;
    const double speed = m_lastMovementDelta.length();
    // Se o traço parou antes de levantar a caneta, não gera cauda de flick
    if (speed < 0.3) {
        return pts;
    }

    const size_t numSteps = std::clamp(steps, static_cast<size_t>(2), static_cast<size_t>(8));
    pts.reserve(numSteps);

    const math::Point2D dir = m_lastMovementDelta * (1.0 / speed);
    const double distLimit = maxDistance > 0.0 ? maxDistance : 25.0;
    const double totalDist = std::clamp(speed * 1.5, 2.0, distLimit);

    for (size_t i = 1; i <= numSteps; ++i) {
        const double progress = static_cast<double>(i) / static_cast<double>(numSteps);
        const double eased = 1.0 - std::pow(1.0 - progress, 1.3);
        pts.push_back(m_stabilizedPosition + dir * (totalDist * eased));
    }

    return pts;
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
