#include "DabInterpolator.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::raster {

std::vector<Dab> DabInterpolator::interpolate(
    const Dab& startDab,
    const Dab& endDab,
    double spacingFactor
) {
    std::vector<Dab> dabs;
    
    const double distance = startDab.position.distanceTo(endDab.position);
    const double avgRadius = (startDab.radius + endDab.radius) * 0.5;
    const double diameter = avgRadius * 2.0;
    
    const double stepSize = std::max(1.0, diameter * std::max(0.01, spacingFactor));
    const int numSteps = static_cast<int>(std::ceil(distance / stepSize));

    if (numSteps <= 1) {
        dabs.push_back(endDab);
        return dabs;
    }

    dabs.reserve(static_cast<size_t>(numSteps));

    for (int i = 1; i <= numSteps; ++i) {
        const double t = static_cast<double>(i) / static_cast<double>(numSteps);
        
        const math::Point2D pos = startDab.position + (endDab.position - startDab.position) * t;
        const double radius = startDab.radius + (endDab.radius - startDab.radius) * t;
        const double opacity = startDab.opacity + (endDab.opacity - startDab.opacity) * t;
        const double pressure = startDab.pressure + (endDab.pressure - startDab.pressure) * t;
        const double angle = startDab.angle + (endDab.angle - startDab.angle) * t;
        
        const uint8_t r = static_cast<uint8_t>(startDab.color.r + (endDab.color.r - startDab.color.r) * t);
        const uint8_t g = static_cast<uint8_t>(startDab.color.g + (endDab.color.g - startDab.color.g) * t);
        const uint8_t b = static_cast<uint8_t>(startDab.color.b + (endDab.color.b - startDab.color.b) * t);
        const uint8_t a = static_cast<uint8_t>(startDab.color.a + (endDab.color.a - startDab.color.a) * t);

        dabs.emplace_back(pos, radius, opacity, pressure, angle, startDab.blendMode, ColorRGBA{r, g, b, a});
    }

    return dabs;
}

} // namespace aladyn::engine::raster
