#ifndef ALADYN_ENGINE_DYNAMIC_STABILIZER_HPP
#define ALADYN_ENGINE_DYNAMIC_STABILIZER_HPP

#include "../../utils/Point2D.hpp"
#include <array>
#include <vector>
#include <cstddef>

namespace aladyn::engine::stroke {

class DynamicStabilizer {
public:
    static constexpr size_t MAX_WINDOW_SIZE = 96;

    explicit DynamicStabilizer(double stabilizationPercentage = 40.0) noexcept;

    void reset(utils::Point2D initialPosition, double initialPressure = 1.0) noexcept;
    void reanchorInitialPosition(utils::Point2D newInitialPosition) noexcept;
    utils::Point2D update(utils::Point2D rawPosition, double rawPressure, double normalizedVelocity) noexcept;
    utils::Point2D update(utils::Point2D rawPosition, double normalizedVelocity = 0.0) noexcept;
    std::vector<utils::Point2D> flush(utils::Point2D endPosition, size_t steps = 3) noexcept;
    std::vector<utils::Point2D> getTaperPoints(size_t steps = 4, double maxDistance = 30.0) noexcept;

    void setStabilizationPercentage(double percentage) noexcept;
    [[nodiscard]] double getStabilizationPercentage() const noexcept { return m_stabilizationPercentage; }
    [[nodiscard]] utils::Point2D getStabilizedPosition() const noexcept { return m_stabilizedPosition; }
    [[nodiscard]] double getStabilizedPressure() const noexcept { return m_stabilizedPressure; }
    [[nodiscard]] utils::Point2D getLastMovementDelta() const noexcept { return m_lastMovementDelta; }

    void setPredictiveExtrapolation(bool enabled, double aheadMs = 8.0) noexcept {
        m_predictionEnabled = enabled;
        m_aheadMs = aheadMs;
    }
    [[nodiscard]] bool isPredictiveEnabled() const noexcept { return m_predictionEnabled; }

    utils::Point2D predictPosition(utils::Point2D currentPos, utils::Point2D velocity) const noexcept;

private:
    double m_stabilizationPercentage{40.0};
    utils::Point2D m_stabilizedPosition{0.0, 0.0};
    double m_stabilizedPressure{1.0};
    utils::Point2D m_lastMovementDelta{0.0, 0.0};
    bool m_predictionEnabled{false};
    double m_aheadMs{8.0};

    std::array<utils::Point2D, MAX_WINDOW_SIZE> m_historyBuffer{};
    std::array<double, MAX_WINDOW_SIZE> m_pressureHistoryBuffer{};
    size_t m_historyCount{0};
    size_t m_historyHead{0};
};

} // namespace aladyn::engine::stroke

#endif // ALADYN_ENGINE_DYNAMIC_STABILIZER_HPP
