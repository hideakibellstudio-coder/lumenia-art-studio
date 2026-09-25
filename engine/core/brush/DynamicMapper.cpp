#include "DynamicMapper.hpp"
#include <algorithm>
#include <random>

namespace aladyn::engine::brush {

MappedBrushState DynamicMapper::map(
    const BrushProfile& profile,
    utils::Point2D position,
    double rawPressure,
    double normalizedVelocity,
    double strokeAngle,
    double twist,
    double altitude,
    double azimuth
) noexcept {
    static thread_local std::mt19937 rng(1337);
    std::uniform_real_distribution<double> distJitter(-1.0, 1.0);

    // Factor base de tamanho
    double fSize = 1.0;
    if (profile.pressureSizeEnabled) {
        fSize *= profile.pressureSizeCurve.sample(rawPressure);
    } else {
        fSize = 1.0;
    }

    if (profile.velocitySizeEnabled) {
        const double vFactor = profile.velocitySizeCurve.sample(normalizedVelocity);
        fSize *= vFactor;
    }

    fSize = std::clamp(fSize, 0.0, 1.0);

    // Factor base de fluxo/opacidade
    double fFlow = profile.pressureFlowEnabled ? profile.pressureFlowCurve.sample(rawPressure) : 1.0;
    fFlow = std::clamp(fFlow, 0.0, 1.0);

    // ─── FLUXO E MODULAÇÃO DINÂMICA DA PONTA (OPACIDADE COMO FLUXO) ──────────
    const double minOpPercent = std::clamp(profile.minOpacityPercent, 0.0, 1.0);
    const double brushOpacity = std::clamp(profile.opacity, 0.0, 1.0);
    const double mappedFlow = (minOpPercent + (1.0 - minOpPercent) * fFlow) * brushOpacity;

    // ─── ALGORITMO DO PAINTTOOL SAI 2 (brsize + szmin %) ──────────────────────
    const double minPercent = std::clamp(profile.minSizePercent, 0.0, 1.0);
    const double minSizePx = profile.brushSize * minPercent;
    const double thickness = minSizePx + (profile.brushSize - minSizePx) * fSize;
    const double radius = thickness * 0.5;

    // ─── CÁLCULO DE ÂNGULO E ROTAÇÃO DINÂMICA (CANETA & TRAÇO) ─────────────────
    double angle = profile.tip.angle;
    if (profile.tip.followStroke) {
        angle += strokeAngle;
    }

    if (profile.tip.useTwistForAngle) {
        angle += twist;
    }

    if (profile.tip.tiltToAngle > 0.0) {
        angle += azimuth * profile.tip.tiltToAngle;
    }

    if (profile.pressureToAngle != 0.0) {
        angle += rawPressure * profile.pressureToAngle;
    }

    angle = std::fmod(angle, 360.0);
    if (angle < 0.0) angle += 360.0;

    // ─── CÁLCULO DO ACHATAMENTO ELÍPTICO (ASPECT RATIO) ───────────────────────
    double aspect = profile.tip.aspectRatio;
    if (profile.pressureToAspect > 0.0) {
        aspect = std::clamp(aspect - (rawPressure * profile.pressureToAspect), 0.05, 1.0);
    }
    if (profile.tip.tiltToAspect > 0.0) {
        const double tiltFlatness = std::clamp((90.0 - altitude) / 70.0, 0.0, 1.0);
        aspect = std::clamp(aspect * (1.0 - tiltFlatness * profile.tip.tiltToAspect), 0.05, 1.0);
    }
    aspect = std::clamp(aspect, 0.05, 1.0);

    utils::Point2D finalPos = position;
    utils::ColorRGBA color = profile.baseColor;

    return MappedBrushState{finalPos, radius, mappedFlow, rawPressure, angle, color, aspect};
}

void DynamicMapper::applyJitter(
    utils::Dab& dab,
    const BrushProfile& profile
) noexcept {
    static thread_local std::mt19937 rng(1337);
    std::uniform_real_distribution<double> distJitter(-1.0, 1.0);

    if (profile.tip.jitterSize > 0.0) {
        const double sizeFactor = 1.0 + (distJitter(rng) * profile.tip.jitterSize * 0.5);
        dab.radius = std::max(0.25, dab.radius * sizeFactor);
    }

    if (profile.tip.jitterAngle > 0.0) {
        dab.angle += distJitter(rng) * profile.tip.jitterAngle * 180.0;
        dab.angle = std::fmod(dab.angle, 360.0);
        if (dab.angle < 0.0) dab.angle += 360.0;
    }

    if (profile.tip.jitterPosition > 0.0) {
        const double scatterRadius = dab.radius * profile.tip.jitterPosition * 2.0;
        dab.position.x += distJitter(rng) * scatterRadius;
        dab.position.y += distJitter(rng) * scatterRadius;
    }

    if (profile.tip.jitterHue > 0.0 || profile.tip.jitterSaturation > 0.0 || profile.tip.jitterBrightness > 0.0) {
        float r = static_cast<float>(dab.color.r) / 255.0f;
        float g = static_cast<float>(dab.color.g) / 255.0f;
        float b = static_cast<float>(dab.color.b) / 255.0f;

        const float minVal = std::min({r, g, b});
        const float maxVal = std::max({r, g, b});
        const float delta = maxVal - minVal;
        float h = 0.0f, s = 0.0f, v = maxVal;
        if (maxVal > 0.0f && delta > 0.0f) {
            s = delta / maxVal;
            if (r == maxVal) h = (g - b) / delta;
            else if (g == maxVal) h = 2.0f + (b - r) / delta;
            else h = 4.0f + (r - g) / delta;
            h *= 60.0f;
            if (h < 0.0f) h += 360.0f;
        }

        if (profile.tip.jitterHue > 0.0) {
            h += static_cast<float>(distJitter(rng) * profile.tip.jitterHue * 180.0);
            h = std::fmod(h, 360.0f);
            if (h < 0.0f) h += 360.0f;
        }
        if (profile.tip.jitterSaturation > 0.0) {
            s = std::clamp(s + static_cast<float>(distJitter(rng) * profile.tip.jitterSaturation), 0.0f, 1.0f);
        }
        if (profile.tip.jitterBrightness > 0.0) {
            v = std::clamp(v + static_cast<float>(distJitter(rng) * profile.tip.jitterBrightness), 0.0f, 1.0f);
        }

        if (s == 0.0f) {
            r = g = b = v;
        } else {
            const float c = v * s;
            const float x = c * (1.0f - std::abs(std::fmod(h / 60.0f, 2.0f) - 1.0f));
            const float m = v - c;
            float r1 = 0.0f, g1 = 0.0f, b1 = 0.0f;
            if (h < 60.0f)       { r1 = c; g1 = x; b1 = 0.0f; }
            else if (h < 120.0f) { r1 = x; g1 = c; b1 = 0.0f; }
            else if (h < 180.0f) { r1 = 0.0f; g1 = c; b1 = x; }
            else if (h < 240.0f) { r1 = 0.0f; g1 = x; b1 = c; }
            else if (h < 300.0f) { r1 = x; g1 = 0.0f; b1 = c; }
            else                 { r1 = c; g1 = 0.0f; b1 = x; }
            r = r1 + m; g = g1 + m; b = b1 + m;
        }
        dab.color.r = static_cast<uint8_t>(std::clamp(r * 255.0f, 0.0f, 255.0f));
        dab.color.g = static_cast<uint8_t>(std::clamp(g * 255.0f, 0.0f, 255.0f));
        dab.color.b = static_cast<uint8_t>(std::clamp(b * 255.0f, 0.0f, 255.0f));
    }
}

std::vector<MappedBrushState> DynamicMapper::map_scatter(
    const BrushProfile& profile,
    utils::Point2D position,
    double rawPressure,
    double normalizedVelocity,
    double strokeAngle,
    double twist,
    double altitude,
    double azimuth
) {
    int count = std::max(1, profile.scatterCount);
    std::vector<MappedBrushState> states;
    states.reserve(static_cast<size_t>(count));

    for (int i = 0; i < count; ++i) {
        states.push_back(map(profile, position, rawPressure, normalizedVelocity, strokeAngle, twist, altitude, azimuth));
    }

    return states;
}

} // namespace aladyn::engine::brush
