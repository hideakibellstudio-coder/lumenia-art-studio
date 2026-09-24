#ifndef ALADYN_ENGINE_DAB_INTERPOLATOR_HPP
#define ALADYN_ENGINE_DAB_INTERPOLATOR_HPP

#include "Dab.hpp"
#include <vector>

namespace aladyn::engine::brush { class BrushProfile; }

namespace aladyn::engine::raster {

class DabInterpolator {
public:
    // Interpolação linear tradicional (segmento reto entre dois pontos)
    static std::vector<Dab> interpolate(
        const Dab& startDab,
        const Dab& endDab,
        double spacingFactor,
        double& distanceCarryover,
        const brush::BrushProfile* profile = nullptr
    );

    // Interpolação Spline Catmull-Rom Centrípeta C^1 através de 4 nós de controle
    // (p0, p1, p2, p3), amostrando o segmento contínuo entre p1 e p2.
    static std::vector<Dab> interpolateSpline(
        const Dab& p0,
        const Dab& p1,
        const Dab& p2,
        const Dab& p3,
        double spacingFactor,
        double& distanceCarryover,
        const brush::BrushProfile* profile = nullptr
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
