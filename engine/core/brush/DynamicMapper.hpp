#ifndef ALADYN_ENGINE_DYNAMIC_MAPPER_HPP
#define ALADYN_ENGINE_DYNAMIC_MAPPER_HPP

#include "BrushProfile.hpp"
#include "../raster/Dab.hpp"

namespace aladyn::engine::brush {

struct MappedBrushState {
    math::Point2D position{0.0, 0.0};
    double radius{1.0};
    double opacity{1.0};
    double pressure{1.0};
    double angle{0.0};
    raster::ColorRGBA color{0, 0, 0, 255};
};

class DynamicMapper {
public:
    static MappedBrushState map(
        const BrushProfile& profile,
        math::Point2D position,
        double rawPressure,
        double normalizedVelocity,
        double strokeAngle = 0.0
    ) noexcept;

    static std::vector<MappedBrushState> map_scatter(
        const BrushProfile& profile,
        math::Point2D position,
        double rawPressure,
        double normalizedVelocity,
        double strokeAngle = 0.0
    );
};

} // namespace aladyn::engine::brush

#endif // ALADYN_ENGINE_DYNAMIC_MAPPER_HPP
