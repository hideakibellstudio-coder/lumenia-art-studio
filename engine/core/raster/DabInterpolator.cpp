#include "DabInterpolator.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::raster {

std::vector<Dab> DabInterpolator::interpolate(
    const Dab& startDab,
    const Dab& endDab,
    double spacingFactor,
    double& distanceCarryover
) {
    std::vector<Dab> dabs;

    const double distance = startDab.position.distanceTo(endDab.position);
    const double safeSpacing = std::max(0.005, spacingFactor);

    // Se o movimento for um clique estacionário / ponto único inicial
    if (distance < 0.0001) {
        if (distanceCarryover == 0.0) {
            dabs.push_back(startDab);
        }
        return dabs;
    }

    // Calcula o menor arco angular (shortest angular path)
    const double diffAngle = std::fmod((endDab.angle - startDab.angle) + 540.0, 360.0) - 180.0;

    // Modulação de passo adaptativo por velocidade / distância do micro-segmento
    // Em movimentos em alta velocidade (> 12px por segmento de ~8ms), o olho humano não
    // consegue distinguir dabs sub-pixel; aplicar uma suave escala (até 1.45x) mantém 
    // a linha perfeitamente contínua e evita saturação desnecessária de dabs.
    const double velocityScale = (distance > 12.0)
        ? std::min(1.45, 1.0 + 0.018 * (distance - 12.0))
        : 1.0;

    auto calculateAdaptiveStep = [velocityScale](double r, double safeSpacing) -> double {
        const double safeR = std::max(0.001, r);
        double base;
        if (safeR <= 32.0) {
            base = std::max(0.75, 2.0 * safeR * safeSpacing);
        } else {
            const double ratio = safeR / 32.0;
            const double scale = std::min(1.5, 1.0 + 0.12 * std::log2(ratio));
            base = std::max(0.75, 2.0 * safeR * safeSpacing * scale);
        }
        return base * velocityScale;
    };

    // Raio inicial e passo inicial estimado
    const double initRadius = std::max(0.001, startDab.radius);
    const double nominalStep = calculateAdaptiveStep(initRadius, safeSpacing);
    const double minStepClamp = std::max(0.75, nominalStep * 0.25);
    double curStep = nominalStep;

    // Determina a primeira distância de emissão considerando o resíduo do segmento anterior
    double d = curStep - distanceCarryover;
    if (d < 0.0) d = 0.0;

    // Se a distância necessária para o próximo dab exceder este micro-segmento inteiro
    if (d > distance) {
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

        const uint8_t r = static_cast<uint8_t>(std::clamp(startDab.color.r + (endDab.color.r - startDab.color.r) * t, 0.0, 255.0));
        const uint8_t g = static_cast<uint8_t>(std::clamp(startDab.color.g + (endDab.color.g - startDab.color.g) * t, 0.0, 255.0));
        const uint8_t b = static_cast<uint8_t>(std::clamp(startDab.color.b + (endDab.color.b - startDab.color.b) * t, 0.0, 255.0));
        const uint8_t a = static_cast<uint8_t>(std::clamp(startDab.color.a + (endDab.color.a - startDab.color.a) * t, 0.0, 255.0));

        dabs.emplace_back(pos, radius, opacity, pressure, angle, startDab.blendMode, ColorRGBA{r, g, b, a});

        lastDabPos = d;

        // Atualiza o passo ideal para o raio do ponto atual de emissão
        curStep = std::max(minStepClamp, calculateAdaptiveStep(radius, safeSpacing));

        d += curStep;

        if (dabs.size() >= 512) break; // Teto rígido de segurança
    }

    // Calcula o resíduo de distância que sobrou após o último dab emitido
    distanceCarryover = std::max(0.0, distance - lastDabPos);

    return dabs;
}

} // namespace aladyn::engine::raster
