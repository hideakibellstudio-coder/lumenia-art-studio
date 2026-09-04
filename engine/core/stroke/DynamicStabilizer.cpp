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

    // 1. Mapeamento linear contínuo baseado nos níveis do SAI (0 a 22, onde 15 = Nível 15 e 22 = S-7)
    const double norm = std::clamp(m_stabilizationPercentage / 100.0, 0.0, 1.0);
    const double L = norm * 22.0;

    // 2. Tamanho da Janela de Amostras e Inércia Hiperbólica (Zero zona morta)
    size_t maxWindow = 2;
    double alpha = 1.0;

    if (L <= 15.0) {
        // Níveis normais 1 a 15 do SAI
        maxWindow = std::clamp(static_cast<size_t>(2 + static_cast<int>(L * 1.7)), static_cast<size_t>(2), MAX_WINDOW_SIZE);
        alpha = 1.0 / (1.0 + L * 0.30);
    } else {
        // Níveis Super S-1 a S-7 do SAI
        const double sIndex = L - 15.0; // 0.0 a 7.0
        maxWindow = std::clamp(static_cast<size_t>(27 + static_cast<int>(sIndex * 9.8)), static_cast<size_t>(2), MAX_WINDOW_SIZE);
        alpha = 1.0 / (5.5 + sIndex * 3.5);
    }

    m_historyHead = (m_historyHead + 1) % MAX_WINDOW_SIZE;
    m_historyBuffer[m_historyHead] = rawPosition;
    if (m_historyCount < maxWindow) {
        ++m_historyCount;
    } else {
        m_historyCount = maxWindow;
    }

    // 3. Núcleo ponderado parabólico com expoente gamma = 1.40 do SAI Ver.2
    static const auto WEIGHT_LUT = []() {
        std::array<double, MAX_WINDOW_SIZE> arr{};
        for (size_t k = 0; k < MAX_WINDOW_SIZE; ++k) {
            arr[k] = std::pow(static_cast<double>(k + 1), 1.40);
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

    // 4. Inércia Elástica Trailing Spring contínua (SAI Trailing Spring)
    const double clampedAlpha = std::clamp(alpha, 0.025, 1.0);
    const math::Point2D delta = windowAvg - m_stabilizedPosition;
    m_stabilizedPosition = m_stabilizedPosition + (delta * clampedAlpha);
    return m_stabilizedPosition;
}

std::vector<math::Point2D> DynamicStabilizer::flush(math::Point2D endPosition, size_t steps) noexcept {
    std::vector<math::Point2D> catchupPoints;
    if (m_stabilizationPercentage <= 0.5) {
        m_stabilizedPosition = endPosition;
        catchupPoints.push_back(endPosition);
        return catchupPoints;
    }

    const double norm = std::clamp(m_stabilizationPercentage / 100.0, 0.0, 1.0);
    const double L = norm * 22.0;
    double alpha = 1.0;
    if (L <= 15.0) {
        alpha = 1.0 / (1.0 + L * 0.30);
    } else {
        alpha = 1.0 / (5.5 + (L - 15.0) * 3.5);
    }

    const double closeAlpha = std::clamp(alpha * 2.2, 0.14, 0.92);
    const size_t maxSteps = std::clamp(static_cast<size_t>(steps * 8 + 8), static_cast<size_t>(8), static_cast<size_t>(48));

    for (size_t i = 0; i < maxSteps; ++i) {
        const double dist = m_stabilizedPosition.distanceTo(endPosition);
        if (dist < 0.25) {
            catchupPoints.push_back(endPosition);
            m_stabilizedPosition = endPosition;
            break;
        }
        m_stabilizedPosition = m_stabilizedPosition + (endPosition - m_stabilizedPosition) * closeAlpha;
        catchupPoints.push_back(m_stabilizedPosition);
    }
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
