#ifndef ALADYN_ENGINE_POINTER_EVENT_HPP
#define ALADYN_ENGINE_POINTER_EVENT_HPP

#include "../math/Point2D.hpp"

namespace aladyn::engine::stroke {

enum class PointerEventType {
    Press,
    Move,
    Release
};

struct PointerEvent {
    PointerEventType type{PointerEventType::Move};
    math::Point2D position{0.0, 0.0};
    double pressure{1.0};
    double timestamp{0.0};
    double tiltX{0.0};
    double tiltY{0.0};

    constexpr PointerEvent() noexcept = default;
    constexpr PointerEvent(PointerEventType pType, math::Point2D pPos, double pPressure = 1.0, double pTimestamp = 0.0) noexcept
        : type(pType), position(pPos), pressure(pPressure), timestamp(pTimestamp) {}
};

} // namespace aladyn::engine::stroke

#endif // ALADYN_ENGINE_POINTER_EVENT_HPP
