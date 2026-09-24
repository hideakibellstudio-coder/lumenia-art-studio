#include "LargeBrushOptimizer.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::raster {

double LargeBrushOptimizer::computeAdaptiveStep(
    double radius,
    double spacingFactor,
    double segmentDistance
) noexcept {
    const double safeR = std::max(0.001, radius);
    const double safeSpacing = std::max(0.005, spacingFactor);

    if (safeR <= LARGE_BRUSH_RADIUS_THRESHOLD) {
        // Traço fino (R <= 32px): densidade puramente uniforme e nominal (100% inalterada)
        return std::max(0.75, 2.0 * safeR * safeSpacing);
    }

    // Adaptive Spacing para pincéis médios e gigantes (R > 32px até 2000px):
    // Transição suave contínua C^1 no limiar de R = 32px até R = 250px (diâmetro 500px).
    // Garante entre 4 e 5 carimbos de sobreposição (overlap ~65-75%), evitando o acúmulo
    // catastrófico de 12 a 20 carimbos sobrepostos que saturavam instantaneamente para preto sólido.
    const double u = std::clamp((safeR - LARGE_BRUSH_RADIUS_THRESHOLD) / (250.0 - LARGE_BRUSH_RADIUS_THRESHOLD), 0.0, 1.0);
    const double targetGiantSpacing = std::max(safeSpacing, 0.18);
    const double effectiveSpacing = safeSpacing + (targetGiantSpacing - safeSpacing) * smoothHermite(u);

    // Teto de segurança: o passo nunca excede 35% do diâmetro (overlap >= 65%)
    const double maxSafeStep = safeR * 0.70;
    const double calculatedStep = 2.0 * safeR * effectiveSpacing;

    return std::max(0.75, std::min(maxSafeStep, calculatedStep));
}

size_t LargeBrushOptimizer::getMaxDabsPerSegment(double radius) noexcept {
    if (radius <= LARGE_BRUSH_RADIUS_THRESHOLD) {
        return 2048; // Traços finos suportam muitos dabs por segmento
    }

    // Para pincéis gigantes, evita que rajadas ou travamentos pontuais acumulem
    // centenas de carimbos gigantes em um único micro-evento.
    if (radius >= 250.0) {
        return 32;
    }
    if (radius >= 100.0) {
        return 64;
    }
    return 128;
}

} // namespace aladyn::engine::raster
