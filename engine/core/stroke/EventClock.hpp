#ifndef ALADYN_ENGINE_EVENT_CLOCK_HPP
#define ALADYN_ENGINE_EVENT_CLOCK_HPP

#include <algorithm>
#include <cstddef>

namespace aladyn::engine::stroke {

// Turns device timestamps into one strictly increasing time per event (2026-10-09).
//
// On Windows the time Qt gives an input event comes from the message clock, which only
// advances every ~15.6 ms: a 125 Hz mouse sends pairs with the same time, a 1 kHz one
// sixteen, the pen bursts of six (recorded on the owner's machine). The stabilizer weighs
// samples by their age, so two events with one time weighed the same and the next tick aged
// the whole group at once: circles came out as polygons with a zigzag edge (circles drawn
// with the owner's mouse at 90%: the line turned 1.9 times as much as the same input timed
// by arrival).
//
// A repeated (or older) stamp is placed one learned event interval after the previous time,
// never more than kMaxAheadSeconds past its own stamp; a stamp later than the previous time
// is kept as it is, so devices with exact times are untouched. The interval is learned from
// how many events each tick carried (the first tick replaces the guess) and survives between
// strokes: it belongs to the device.
class EventClock {
public:
    static constexpr double kNominalSeconds = 1.0 / 360.0;  // first guess: the pen's rate
    static constexpr double kMaxAheadSeconds = 0.020;       // a tick is 15.6 ms
    static constexpr double kPauseSeconds = 0.100;          // longer gaps teach nothing about the rate
    static constexpr double kMinStepSeconds = 1.0e-4;
    static constexpr double kLearnRate = 0.25;

    void begin(double stamp) noexcept {
        m_last = stamp;
        m_groupStamp = stamp;
        m_groupCount = 1;
    }

    [[nodiscard]] double place(double stamp) noexcept {
        if (stamp > m_groupStamp) {
            const double gap = stamp - m_groupStamp;
            if (m_groupCount > 0 && gap < kPauseSeconds) {
                const double measured = gap / static_cast<double>(m_groupCount);
                m_interval = m_learned ? m_interval + (measured - m_interval) * kLearnRate : measured;
                m_learned = true;
            }
            m_groupStamp = stamp;
            m_groupCount = 1;
            if (stamp > m_last) {
                m_last = stamp;
                return stamp;
            }
        } else if (stamp == m_groupStamp) {
            ++m_groupCount;
        }
        const double next = std::min(m_last + m_interval, std::max(stamp, m_groupStamp) + kMaxAheadSeconds);
        m_last = std::max(next, m_last + kMinStepSeconds);
        return m_last;
    }

    [[nodiscard]] double interval() const noexcept { return m_interval; }

private:
    double m_interval{kNominalSeconds};
    bool m_learned{false};  // the first measured tick replaces the guess outright
    double m_last{0.0};
    double m_groupStamp{0.0};
    std::size_t m_groupCount{0};
};

} // namespace aladyn::engine::stroke

#endif // ALADYN_ENGINE_EVENT_CLOCK_HPP
