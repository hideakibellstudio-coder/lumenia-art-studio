#ifndef ALADYN_ENGINE_DYNAMIC_STABILIZER_HPP
#define ALADYN_ENGINE_DYNAMIC_STABILIZER_HPP

#include "../math/Point2D.hpp"
#include <array>
#include <vector>
#include <cstddef>

namespace aladyn::engine::stroke {

class DynamicStabilizer {
public:
    static constexpr size_t MAX_WINDOW_SIZE = 32;

    explicit DynamicStabilizer(double stabilizationPercentage = 40.0) noexcept;

    void reset(math::Point2D initialPosition) noexcept;
    math::Point2D update(math::Point2D rawPosition) noexcept;
    std::vector<math::Point2D> flush(math::Point2D endPosition, size_t steps = 3) noexcept;

    void setStabilizationPercentage(double percentage) noexcept;
    [[nodiscard]] double getStabilizationPercentage() const noexcept { return m_stabilizationPercentage; }
    [[nodiscard]] math::Point2D getStabilizedPosition() const noexcept { return m_stabilizedPosition; }

    void setPredictiveExtrapolation(bool enabled, double aheadMs = 8.0) noexcept {
        m_predictionEnabled = enabled;
        m_aheadMs = aheadMs;
    }
    [[nodiscard]] bool isPredictiveEnabled() const noexcept { return m_predictionEnabled; }

    math::Point2D predictPosition(math::Point2D currentPos, math::Point2D velocity) const noexcept;

private:
    double m_stabilizationPercentage{40.0};
    math::Point2D m_stabilizedPosition{0.0, 0.0};
    bool m_predictionEnabled{false};
    double m_aheadMs{8.0};

    std::array<math::Point2D, MAX_WINDOW_SIZE> m_historyBuffer{};
    size_t m_historyCount{0};
    size_t m_historyHead{0};
};

} // namespace aladyn::engine::stroke

#endif // ALADYN_ENGINE_DYNAMIC_STABILIZER_HPP
