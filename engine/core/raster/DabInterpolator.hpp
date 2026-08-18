#ifndef ALADYN_ENGINE_DAB_INTERPOLATOR_HPP
#define ALADYN_ENGINE_DAB_INTERPOLATOR_HPP

#include "Dab.hpp"
#include <vector>

namespace aladyn::engine::raster {

class DabInterpolator {
public:
    // Interpolação profissional com avanço incremental adaptativo ao raio
    // e transporte contínuo de resíduo de distância (distanceCarryover) entre eventos
    static std::vector<Dab> interpolate(
        const Dab& startDab,
        const Dab& endDab,
        double spacingFactor,
        double& distanceCarryover
    );

    // Sobrecarga de conveniência para renderizações pontuais
    static std::vector<Dab> interpolate(
        const Dab& startDab,
        const Dab& endDab,
        double spacingFactor = 0.15
    ) {
        double dummyCarryover = 0.0;
        return interpolate(startDab, endDab, spacingFactor, dummyCarryover);
    }
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_DAB_INTERPOLATOR_HPP
