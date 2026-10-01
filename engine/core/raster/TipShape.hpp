#ifndef ALADYN_ENGINE_TIP_SHAPE_HPP
#define ALADYN_ENGINE_TIP_SHAPE_HPP

#include "DabFootprint.hpp"
#include "LargeBrushOptimizer.hpp"
#include "../brush/BrushProfile.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::raster {

// O alfa que a forma da ponta dá a um pixel do dab: a textura de forma, ou o disco com dureza
// (miolo sólido e queda de Hermite), e o anti-aliasing de meio pixel na borda externa.
//
// É a forma do pincel padrão e da borracha. Os outros motores têm a queda própria (lineal, cúbica,
// com anel de secagem) e não passam por aqui.
class TipShape {
public:
    TipShape(const brush::BrushProfile& profile, double radius) noexcept
        : m_texture(profile.shapeTexture.get()),
          m_safeRadius(std::max(0.001, radius)),
          m_invTwoSafeRadius(0.5 / m_safeRadius),
          m_hardSpan(std::clamp(profile.hardness, 0.0, 0.99) * m_safeRadius),
          m_hardSpanSq(m_hardSpan * m_hardSpan),
          m_invSoftSpan(1.0 / std::max(0.001, m_safeRadius - m_hardSpan)),
          m_outerThreshold(m_safeRadius - 0.5),
          m_outerThresholdSq(m_outerThreshold > 0.0 ? m_outerThreshold * m_outerThreshold : 0.0) {}

    [[nodiscard]] double alphaAt(const DabPixel& pixel) const {
        double alpha = 1.0;
        if (m_texture) {
            const double u = (pixel.rotX + m_safeRadius) * m_invTwoSafeRadius;
            const double v = (pixel.scaledY + m_safeRadius) * m_invTwoSafeRadius;
            alpha = m_texture->sampleNormalized(u, v, texture::TextureWrapMode::Clamp);
            if (m_outerThreshold <= 0.0 || pixel.distSq > m_outerThresholdSq) alpha *= edgeFalloff(std::sqrt(pixel.distSq));
            return alpha;
        }
        // No miolo sólido dispensa o sqrt e as divisões.
        if (pixel.distSq > m_hardSpanSq || pixel.distSq > m_outerThresholdSq) {
            const double dist = std::sqrt(pixel.distSq);
            if (dist > m_hardSpan) alpha = LargeBrushOptimizer::smoothHermite((m_safeRadius - dist) * m_invSoftSpan);
            alpha *= edgeFalloff(dist);
        }
        return alpha;
    }

private:
    // O meio pixel externo do dab some em rampa (1 dentro, 0 na borda).
    double edgeFalloff(double dist) const noexcept {
        return dist > m_outerThreshold ? std::clamp((m_safeRadius - dist) * 2.0, 0.0, 1.0) : 1.0;
    }

    const texture::Texture2D* m_texture;
    double m_safeRadius;
    double m_invTwoSafeRadius;
    double m_hardSpan;
    double m_hardSpanSq;
    double m_invSoftSpan;
    double m_outerThreshold;
    double m_outerThresholdSq;
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_TIP_SHAPE_HPP
