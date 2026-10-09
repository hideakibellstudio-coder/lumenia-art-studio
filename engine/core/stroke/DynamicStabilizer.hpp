#ifndef ALADYN_ENGINE_DYNAMIC_STABILIZER_HPP
#define ALADYN_ENGINE_DYNAMIC_STABILIZER_HPP

#include "../../utils/Point2D.hpp"
#include "EventClock.hpp"
#include <array>
#include <vector>
#include <cstddef>

namespace aladyn::engine::stroke {

// Weighted moving average of the pointer over a window of TIME (2026-10-09).
//
// The weight of a sample falls with its age: w = (1 - age / window) ^ exponent, the
// continuous form of the SAI-style (i + 1) ^ exponent the class used before. Until
// 2026-10-09 the window counted EVENTS (3 to 72), so the lag depended on how often the
// device reports: a 60 Hz mouse lagged six times more than the pen it was tuned on
// (Windows Ink, ~360 events/s in bursts of 6), circles closed with a straight chord and
// the line bent where the window filled up. The window is now the time those events
// spanned at the pen's rate, the same for every device, and a sample leaves it with
// weight zero, so nothing bends when it goes.
//
// Event times go through an EventClock: Windows stamps input in ~15.6 ms ticks, and a
// group of events with one time must not weigh the same (circles came out as polygons).
// A gap with no events is filled with samples on the way from the last position to the new
// one: a held mouse sends nothing and its next event lands next to where it stopped, so the
// fill stands still there; an event that is merely late does not pull the line back.
// `drain` holds the release point at pen-up so the line reaches it along the path.
class DynamicStabilizer {
public:
    // Ring capacity: 200 ms of a 1 kHz mouse fit with room to spare.
    static constexpr size_t MAX_SAMPLES = 512;
    // Event interval of the pen the count window was tuned on: window = events x this.
    static constexpr double kNominalEventSeconds = 1.0 / 360.0;
    // Longer than this without events gets filled (a 60 Hz frame is 16.7 ms).
    static constexpr double kStillGapSeconds = 0.025;
    // Spacing of the fill samples.
    static constexpr double kStillStepSeconds = 1.0 / 60.0;

    struct Node {
        utils::Point2D position{0.0, 0.0};
        double pressure{1.0};
    };

    explicit DynamicStabilizer(double stabilizationPercentage = 40.0) noexcept;

    void reset(utils::Point2D initialPosition, double initialPressure = 1.0) noexcept;
    void reset(utils::Point2D initialPosition, double initialPressure, double timestamp) noexcept;
    void reanchorInitialPosition(utils::Point2D newInitialPosition) noexcept;
    // Timestamp in seconds; <= 0 means unknown and advances an internal clock by one nominal event.
    utils::Point2D updateAt(utils::Point2D rawPosition, double rawPressure, double normalizedVelocity,
                            double timestamp) noexcept;
    utils::Point2D update(utils::Point2D rawPosition, double rawPressure, double normalizedVelocity) noexcept;
    utils::Point2D update(utils::Point2D rawPosition, double normalizedVelocity = 0.0) noexcept;
    // Pen-up: the pointer rests on `endPosition` while time runs out the window. Returns the
    // stabilized positions on the way (at most maxNodes + 1), the last one exactly endPosition.
    std::vector<Node> drain(utils::Point2D endPosition, double endPressure, size_t maxNodes = 12) noexcept;
    std::vector<utils::Point2D> flush(utils::Point2D endPosition, size_t steps = 3) noexcept;
    std::vector<utils::Point2D> getTaperPoints(size_t steps = 4, double maxDistance = 30.0) noexcept;

    void setStabilizationPercentage(double percentage) noexcept;
    [[nodiscard]] double getStabilizationPercentage() const noexcept { return m_stabilizationPercentage; }
    [[nodiscard]] bool isActive() const noexcept { return m_stabilizationPercentage > 0.5; }
    [[nodiscard]] double windowSeconds() const noexcept;
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
    struct Sample {
        utils::Point2D position{0.0, 0.0};
        double pressure{1.0};
        double time{0.0};
    };

    void push(const Sample& sample) noexcept;
    void fillGap(double until, utils::Point2D to, double toPressure) noexcept;
    void expire(double now, double window) noexcept;
    void average(double now, double normalizedVelocity) noexcept;
    [[nodiscard]] const Sample& sampleAt(size_t fromOldest) const noexcept;

    double m_stabilizationPercentage{40.0};
    utils::Point2D m_stabilizedPosition{0.0, 0.0};
    double m_stabilizedPressure{1.0};
    utils::Point2D m_lastMovementDelta{0.0, 0.0};
    bool m_predictionEnabled{false};
    double m_aheadMs{8.0};

    std::array<Sample, MAX_SAMPLES> m_samples{};
    size_t m_count{0};
    size_t m_head{0};          // index of the newest sample
    size_t m_updates{0};       // updates since reset (the velocity bypass waits for 5)
    double m_lastNormalizedVelocity{0.0};  // kept through the drain: same weights to the end
    double m_lastTime{0.0};    // time of the newest sample
    EventClock m_clock;        // device stamps -> one increasing time per event
};

} // namespace aladyn::engine::stroke

#endif // ALADYN_ENGINE_DYNAMIC_STABILIZER_HPP
