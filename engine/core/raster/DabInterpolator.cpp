#include "DabInterpolator.hpp"
#include "LargeBrushOptimizer.hpp"
#include "../brush/BrushProfile.hpp"
#include "../brush/DynamicMapper.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::raster {

std::vector<Dab> DabInterpolator::interpolate(
    const Dab& startDab,
    const Dab& endDab,
    double spacingFactor,
    double& distanceCarryover,
    const brush::BrushProfile* profile
) {
    std::vector<Dab> dabs;

    const double distance = startDab.position.distanceTo(endDab.position);
    const double safeSpacing = std::max(0.005, spacingFactor);

    // Se o movimento for um clique estacionário / ponto único inicial
    if (distance < 0.0001) {
        if (distanceCarryover <= 0.0) {
            Dab d = startDab;
            if (profile) {
                brush::DynamicMapper::applyJitter(d, *profile);
            }
            dabs.push_back(d);
            distanceCarryover = 0.0;
        }
        return dabs;
    }

    // Calcula o menor arco angular (shortest angular path)
    const double diffAngle = std::fmod((endDab.angle - startDab.angle) + 540.0, 360.0) - 180.0;

    // Passo inicial estimado via LargeBrushOptimizer (isolamento completo de traço fino vs gigante)
    const double initRadius = std::max(0.001, startDab.radius);
    const double nominalStep = LargeBrushOptimizer::computeAdaptiveStep(initRadius, safeSpacing, distance);
    const double minStepClamp = std::max(0.75, nominalStep * 0.25);
    double curStep = nominalStep;

    // Correção A6: Determina a primeira distância de emissão considerando o resíduo do segmento anterior.
    // Se distanceCarryover < 0.0 (início do traço), emite imediatamente no ponto de toque inicial (d = 0.0).
    double d;
    if (distanceCarryover < 0.0) {
        d = 0.0;
    } else {
        d = curStep - distanceCarryover;
        if (d < 0.0) d = 0.0;
    }

    // Se a distância necessária para o próximo dab exceder este micro-segmento inteiro
    if (d > distance) {
        if (distanceCarryover < 0.0) distanceCarryover = 0.0;
        distanceCarryover += distance;
        return dabs;
    }

    dabs.reserve(std::min(static_cast<size_t>(std::ceil(distance / curStep) + 2), static_cast<size_t>(256)));

    double lastDabPos = 0.0;

    while (d <= distance) {
        const double t = (distance > 0.0001) ? std::clamp(d / distance, 0.0, 1.0) : 0.0;

        const math::Point2D pos = startDab.position + (endDab.position - startDab.position) * t;
        const double radius = startDab.radius + (endDab.radius - startDab.radius) * t;
        const double opacity = startDab.opacity + (endDab.opacity - startDab.opacity) * t;
        const double pressure = startDab.pressure + (endDab.pressure - startDab.pressure) * t;
        const double angle = std::fmod(startDab.angle + diffAngle * t + 360.0, 360.0);
        const double aspect = startDab.aspectRatio + (endDab.aspectRatio - startDab.aspectRatio) * t;

        const uint8_t r = static_cast<uint8_t>(std::clamp(startDab.color.r + (endDab.color.r - startDab.color.r) * t, 0.0, 255.0));
        const uint8_t g = static_cast<uint8_t>(std::clamp(startDab.color.g + (endDab.color.g - startDab.color.g) * t, 0.0, 255.0));
        const uint8_t b = static_cast<uint8_t>(std::clamp(startDab.color.b + (endDab.color.b - startDab.color.b) * t, 0.0, 255.0));
        const uint8_t a = static_cast<uint8_t>(std::clamp(startDab.color.a + (endDab.color.a - startDab.color.a) * t, 0.0, 255.0));

        Dab dab(pos, radius, opacity, pressure, angle, startDab.blendMode, ColorRGBA{r, g, b, a}, aspect);
        // Correção B2: Aplica jitters individualmente por carimbo emitido
        if (profile) {
            brush::DynamicMapper::applyJitter(dab, *profile);
        }
        dabs.push_back(std::move(dab));

        lastDabPos = d;

        // Atualiza o passo ideal para o raio do ponto atual de emissão via LargeBrushOptimizer
        curStep = std::max(minStepClamp, LargeBrushOptimizer::computeAdaptiveStep(radius, safeSpacing, distance));

        d += curStep;

        const size_t maxDabs = LargeBrushOptimizer::getMaxDabsPerSegment(std::max(startDab.radius, endDab.radius));
        if (dabs.size() >= maxDabs) break;
    }

    // Calcula o resíduo de distância que sobrou após o último dab emitido
    distanceCarryover = std::max(0.0, distance - lastDabPos);

    return dabs;
}

std::vector<Dab> DabInterpolator::interpolateSpline(
    const Dab& p0,
    const Dab& p1,
    const Dab& p2,
    const Dab& p3,
    double spacingFactor,
    double& distanceCarryover,
    const brush::BrushProfile* profile
) {
    const double directDist = p1.position.distanceTo(p2.position);
    if (directDist < 0.0001) {
        return interpolate(p1, p2, spacingFactor, distanceCarryover, profile);
    }

    // Parametrização Centrípeta (alpha = 0.5): previne cúspides, laços e overshoots
    const double d01 = p0.position.distanceTo(p1.position);
    const double d12 = directDist;
    const double d23 = p2.position.distanceTo(p3.position);

    const double t0 = 0.0;
    const double t1 = t0 + std::max(0.001, std::sqrt(d01));
    const double t2 = t1 + std::max(0.001, std::sqrt(d12));
    const double t3 = t2 + std::max(0.001, std::sqrt(d23));

    const double inv01 = 1.0 / (t1 - t0);
    const double inv12 = 1.0 / (t2 - t1);
    const double inv23 = 1.0 / (t3 - t2);
    const double inv02 = 1.0 / (t2 - t0);
    const double inv13 = 1.0 / (t3 - t1);

    auto evalCurve = [&](double t) -> math::Point2D {
        const math::Point2D A1 = p0.position * ((t1 - t) * inv01) + p1.position * ((t - t0) * inv01);
        const math::Point2D A2 = p1.position * ((t2 - t) * inv12) + p2.position * ((t - t1) * inv12);
        const math::Point2D A3 = p2.position * ((t3 - t) * inv23) + p3.position * ((t - t2) * inv23);

        const math::Point2D B1 = A1 * ((t2 - t) * inv02) + A2 * ((t - t0) * inv02);
        const math::Point2D B2 = A2 * ((t3 - t) * inv13) + A3 * ((t - t1) * inv13);

        return B1 * ((t2 - t) * inv12) + B2 * ((t - t1) * inv12);
    };

    // Amostragem de 4 cordas para cálculo exato de comprimento de arco
    const math::Point2D q0 = p1.position;
    const math::Point2D q1 = evalCurve(t1 + 0.25 * (t2 - t1));
    const math::Point2D q2 = evalCurve(t1 + 0.50 * (t2 - t1));
    const math::Point2D q3 = evalCurve(t1 + 0.75 * (t2 - t1));
    const math::Point2D q4 = p2.position;

    const double chord01 = q0.distanceTo(q1);
    const double chord12 = q1.distanceTo(q2);
    const double chord23 = q2.distanceTo(q3);
    const double chord34 = q3.distanceTo(q4);
    const double s1 = chord01;
    const double s2 = s1 + chord12;
    const double s3 = s2 + chord23;
    const double arcLength = s3 + chord34;

    if (arcLength < 0.0001) {
        return interpolate(p1, p2, spacingFactor, distanceCarryover, profile);
    }

    auto distanceToT = [&](double dist) -> double {
        if (dist <= 0.0) return t1;
        if (dist >= arcLength) return t2;
        if (dist < s1) {
            const double frac = (s1 > 0.0) ? (dist / s1) : 0.0;
            return t1 + 0.25 * frac * (t2 - t1);
        }
        if (dist < s2) {
            const double frac = (s2 > s1) ? ((dist - s1) / (s2 - s1)) : 0.0;
            return t1 + (0.25 + 0.25 * frac) * (t2 - t1);
        }
        if (dist < s3) {
            const double frac = (s3 > s2) ? ((dist - s2) / (s3 - s2)) : 0.0;
            return t1 + (0.50 + 0.25 * frac) * (t2 - t1);
        }
        const double frac = (arcLength > s3) ? ((dist - s3) / (arcLength - s3)) : 0.0;
        return t1 + (0.75 + 0.25 * frac) * (t2 - t1);
    };

    const double safeSpacing = std::max(0.005, spacingFactor);
    const double initRadius = std::max(0.001, p1.radius);
    const double nominalStep = LargeBrushOptimizer::computeAdaptiveStep(initRadius, safeSpacing, arcLength);
    const double minStepClamp = std::max(0.75, nominalStep * 0.25);
    double curStep = nominalStep;

    double d;
    if (distanceCarryover < 0.0) {
        d = 0.0;
    } else {
        d = curStep - distanceCarryover;
        if (d < 0.0) d = 0.0;
    }

    std::vector<Dab> dabs;
    if (d > arcLength) {
        if (distanceCarryover < 0.0) distanceCarryover = 0.0;
        distanceCarryover += arcLength;
        return dabs;
    }

    dabs.reserve(std::min(static_cast<size_t>(std::ceil(arcLength / curStep) + 2), static_cast<size_t>(256)));

    const double diffAngle = std::fmod((p2.angle - p1.angle) + 540.0, 360.0) - 180.0;
    double lastDabPos = 0.0;

    while (d <= arcLength) {
        const double u = std::clamp(d / arcLength, 0.0, 1.0);
        const double t = distanceToT(d);
        const math::Point2D pos = evalCurve(t);

        const double radius = p1.radius + (p2.radius - p1.radius) * u;
        const double opacity = p1.opacity + (p2.opacity - p1.opacity) * u;
        const double pressure = p1.pressure + (p2.pressure - p1.pressure) * u;
        const double aspect = p1.aspectRatio + (p2.aspectRatio - p1.aspectRatio) * u;

        // Ângulo derivado da tangente instantânea da spline no nó t
        const double dtStep = 0.005 * (t2 - t1);
        const math::Point2D pAhead = evalCurve(std::min(t2, t + dtStep));
        const math::Point2D pBehind = evalCurve(std::max(t1, t - dtStep));
        const math::Point2D tangent = pAhead - pBehind;

        double angle;
        if (tangent.x * tangent.x + tangent.y * tangent.y > 1e-6) {
            angle = std::atan2(tangent.y, tangent.x) * (180.0 / 3.14159265358979323846);
            if (angle < 0.0) angle += 360.0;
        } else {
            angle = std::fmod(p1.angle + diffAngle * u + 360.0, 360.0);
        }


        const uint8_t r = static_cast<uint8_t>(std::clamp(p1.color.r + (p2.color.r - p1.color.r) * u, 0.0, 255.0));
        const uint8_t g = static_cast<uint8_t>(std::clamp(p1.color.g + (p2.color.g - p1.color.g) * u, 0.0, 255.0));
        const uint8_t b = static_cast<uint8_t>(std::clamp(p1.color.b + (p2.color.b - p1.color.b) * u, 0.0, 255.0));
        const uint8_t a = static_cast<uint8_t>(std::clamp(p1.color.a + (p2.color.a - p1.color.a) * u, 0.0, 255.0));

        Dab dab(pos, radius, opacity, pressure, angle, p1.blendMode, ColorRGBA{r, g, b, a}, aspect);
        if (profile) {
            brush::DynamicMapper::applyJitter(dab, *profile);
        }
        dabs.push_back(std::move(dab));

        lastDabPos = d;
        curStep = std::max(minStepClamp, LargeBrushOptimizer::computeAdaptiveStep(radius, safeSpacing, arcLength));
        d += curStep;

        const size_t maxDabs = LargeBrushOptimizer::getMaxDabsPerSegment(std::max(p1.radius, p2.radius));
        if (dabs.size() >= maxDabs) break;
    }

    distanceCarryover = std::max(0.0, arcLength - lastDabPos);
    return dabs;
}

} // namespace aladyn::engine::raster

