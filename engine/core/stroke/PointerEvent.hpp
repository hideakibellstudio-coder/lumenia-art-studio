#ifndef ALADYN_ENGINE_POINTER_EVENT_HPP
#define ALADYN_ENGINE_POINTER_EVENT_HPP

#include "../../utils/Point2D.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::stroke {

enum class PointerEventType {
    Press,
    Move,
    Release
};

struct PointerEvent {
    PointerEventType type{PointerEventType::Move};
    utils::Point2D position{0.0, 0.0};
    double pressure{1.0};
    double timestamp{0.0};
    double tiltX{0.0};
    double tiltY{0.0};
    double twist{0.0};
    double altitude{90.0};
    double azimuth{0.0};

    constexpr PointerEvent() noexcept = default;
    constexpr PointerEvent(
        PointerEventType pType,
        utils::Point2D pPos,
        double pPressure = 1.0,
        double pTimestamp = 0.0,
        double pTiltX = 0.0,
        double pTiltY = 0.0,
        double pTwist = 0.0
    ) noexcept
        : type(pType), position(pPos), pressure(pPressure), timestamp(pTimestamp),
          tiltX(pTiltX), tiltY(pTiltY), twist(pTwist) {}

    void computeAltitudeAzimuthFromTilt() noexcept {
        if (std::abs(tiltX) < 0.001 && std::abs(tiltY) < 0.001) {
            altitude = 90.0;
            azimuth = 0.0;
            return;
        }
        constexpr double deg2rad = 3.14159265358979323846 / 180.0;
        constexpr double rad2deg = 180.0 / 3.14159265358979323846;

        const double radX = tiltX * deg2rad;
        const double radY = tiltY * deg2rad;
        const double tanX = std::tan(radX);
        const double tanY = std::tan(radY);

        const double tanTilt = std::sqrt(tanX * tanX + tanY * tanY);
        const double tiltAngle = std::atan(tanTilt) * rad2deg;
        altitude = std::clamp(90.0 - tiltAngle, 0.0, 90.0);

        double az = std::atan2(tanY, tanX) * rad2deg;
        if (az < 0.0) az += 360.0;
        azimuth = az;
    }
};

} // namespace aladyn::engine::stroke

#endif // ALADYN_ENGINE_POINTER_EVENT_HPP
