#include "DynamicMapper.hpp"
#include <algorithm>
#include <random>

namespace aladyn::engine::brush {

MappedBrushState DynamicMapper::map(
    const BrushProfile& profile,
    math::Point2D position,
    double rawPressure,
    double normalizedVelocity,
    double strokeAngle
) noexcept {
    static thread_local std::mt19937 rng(1337);
    std::uniform_real_distribution<double> distJitter(-1.0, 1.0);

    // Factor base de tamanho
    double fSize = 1.0;
    if (profile.pressureSizeEnabled) {
        fSize *= profile.pressureSizeCurve.sample(rawPressure);
    } else {
        fSize *= rawPressure;
    }

    if (profile.velocitySizeEnabled) {
        const double vFactor = profile.velocitySizeCurve.sample(normalizedVelocity);
        fSize *= vFactor;
    }

    fSize = std::clamp(fSize, 0.0, 1.0);

    // Factor base de fluxo/opacidade
    double fFlow = profile.pressureFlowEnabled ? profile.pressureFlowCurve.sample(rawPressure) : rawPressure;
    fFlow = std::clamp(fFlow, 0.0, 1.0);

    // ─── FLUXO E MODULAÇÃO DINÂMICA DA PONTA ────────────────────────────────
    const double minOpPercent = std::clamp(profile.minOpacityPercent, 0.0, 1.0);
    const double mappedFlow = minOpPercent + (1.0 - minOpPercent) * fFlow;

    // Jitter de Tamanho
    if (profile.tip.jitterSize > 0.0) {
        const double sizeFactor = 1.0 + (distJitter(rng) * profile.tip.jitterSize * 0.5);
        fSize = std::clamp(fSize * sizeFactor, 0.0, 1.5);
    }

    // ─── ALGORITMO DO PAINTTOOL SAI 2 (brsize + szmin %) ──────────────────────
    const double minPercent = std::clamp(profile.minSizePercent, 0.0, 1.0);
    const double minSizePx = profile.brushSize * minPercent;
    const double thickness = minSizePx + (profile.brushSize - minSizePx) * fSize;
    const double radius = thickness * 0.5;

    // ─── CÁLCULO DE ÂNGULO E ACHATAMENTO REATIVOS À PRESSÃO ─────────────────
    double angle = profile.tip.angle;
    if (profile.tip.followStroke) {
        angle += strokeAngle;
    }

    if (profile.pressureToAngle != 0.0) {
        angle += rawPressure * profile.pressureToAngle;
    }

    // Jitter de Ângulo
    if (profile.tip.jitterAngle > 0.0) {
        angle += distJitter(rng) * profile.tip.jitterAngle * 180.0;
    }

    // Jitter de Posição (Dispersão)
    math::Point2D finalPos = position;
    if (profile.tip.jitterPosition > 0.0) {
        const double scatterRadius = radius * profile.tip.jitterPosition * 2.0;
        finalPos.x += distJitter(rng) * scatterRadius;
        finalPos.y += distJitter(rng) * scatterRadius;
    }

    raster::ColorRGBA color = profile.baseColor;
    color.a = static_cast<uint8_t>(std::clamp(mappedFlow * 255.0, 0.0, 255.0));

    return MappedBrushState{finalPos, radius, mappedFlow, rawPressure, angle, color};
}

std::vector<MappedBrushState> DynamicMapper::map_scatter(
    const BrushProfile& profile,
    math::Point2D position,
    double rawPressure,
    double normalizedVelocity,
    double strokeAngle
) {
    int count = std::max(1, profile.scatterCount);
    std::vector<MappedBrushState> states;
    states.reserve(static_cast<size_t>(count));

    for (int i = 0; i < count; ++i) {
        states.push_back(map(profile, position, rawPressure, normalizedVelocity, strokeAngle));
    }

    return states;
}

} // namespace aladyn::engine::brush
