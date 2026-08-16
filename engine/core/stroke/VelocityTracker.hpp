#ifndef ALADYN_ENGINE_VELOCITY_TRACKER_HPP
#define ALADYN_ENGINE_VELOCITY_TRACKER_HPP

#include "../math/Point2D.hpp"

namespace aladyn::engine::stroke {

class VelocityTracker {
public:
    explicit VelocityTracker(double smoothingFactor = 0.15) noexcept;

    void reset(math::Point2D initialPosition, double timestamp) noexcept;
    double update(math::Point2D currentPosition, double timestamp) noexcept;

    [[nodiscard]] double getSmoothedVelocity() const noexcept { return m_smoothedVelocity; }
    [[nodiscard]] double getNormalizedVelocity(double maxVelocity = 1500.0) const noexcept;

private:
    double m_smoothingFactor{0.15};
    math::Point2D m_lastPosition{0.0, 0.0};
    double m_lastTimestamp{0.0};
    double m_smoothedVelocity{0.0};
};

} // namespace aladyn::engine::stroke

#endif // ALADYN_ENGINE_VELOCITY_TRACKER_HPP
