#ifndef ALADYN_ENGINE_DAB_INTERPOLATOR_HPP
#define ALADYN_ENGINE_DAB_INTERPOLATOR_HPP

#include "Dab.hpp"
#include <vector>

namespace aladyn::engine::raster {

class DabInterpolator {
public:
    static std::vector<Dab> interpolate(
        const Dab& startDab,
        const Dab& endDab,
        double spacingFactor = 0.15
    );
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_DAB_INTERPOLATOR_HPP
