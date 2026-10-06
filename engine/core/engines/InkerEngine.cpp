#include "InkerEngine.hpp"
#include "../raster/DabFootprint.hpp"
#include "../raster/PixelPermission.hpp"
#include "../raster/StraightOver.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::engines {

namespace {

// A borda de uma caneta: sólida até perto do raio e, na franja, uma curva suave cujo
// afunilamento (taperSmoothing) puxa um pouco para o cúbico. Fluxo de tinta (inkFlowRate) escala o alfa.
class InkEdge {
public:
    InkEdge(const utils::Dab& dab, const brush::BrushProfile& profile)
        : m_radius(dab.radius),
          m_feather(std::max(0.6, dab.radius * (1.0 - std::clamp(profile.hardness, 0.0, 1.0)) * 0.25 + 0.6)),
          m_taper(std::clamp(profile.inkerParams.taperSmoothing, 0.0, 1.0)),
          m_baseAlpha((static_cast<double>(dab.color.a) / 255.0) * (dab.opacity * profile.inkerParams.inkFlowRate)) {
        const double solidRadius = m_radius - m_feather;
        m_solidRadiusSq = (solidRadius > 0.0) ? (solidRadius * solidRadius) : 0.0;
        m_invFeather = 1.0 / m_feather;
    }

    // 0 quando o pixel não recebe tinta.
    double alphaAt(const raster::DabPixel& pixel) const {
        double edge = 1.0;
        if (pixel.distSq > m_solidRadiusSq) {
            const double dist = std::sqrt(pixel.distSq);
            if (dist > m_radius - m_feather) {
                const double t = std::clamp((m_radius - dist) * m_invFeather, 0.0, 1.0);
                edge = t * t * (3.0 - 2.0 * t) * (1.0 - m_taper * 0.25) + (t * t * t) * (m_taper * 0.25);
            }
        }
        if (edge <= 0.0) return 0.0;
        return m_baseAlpha * edge;
    }

private:
    double m_radius;
    double m_feather;
    double m_taper;
    double m_baseAlpha;
    double m_solidRadiusSq{0.0};
    double m_invFeather{1.0};
};

} // namespace

void InkerEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,  // NÃO USADO
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0) return;

    const double aspect = raster::tipAspect(dab);
    const raster::DabFootprint footprint(dab, dab.radius, aspect, tileGrid);
    if (footprint.empty()) return;

    const InkEdge ink(dab, profile);
    const raster::PixelPermission permission(ctx);
    if (tileGrid.getFormat() == canvas::PixelFormat::RGBA16) {
        const utils::ColorRGBA16 color16 = canvas::widen(dab.color);
        footprint.forEachPixel<utils::ColorRGBA16>(6, [&](utils::ColorRGBA16& dst, const raster::DabPixel& pixel) {
            double alpha = ink.alphaAt(pixel);
            if (alpha <= 0.0 || !permission.apply(pixel.gx, pixel.gy, alpha) || alpha <= 0.0) return false;
            return raster::straightOver(dst, color16, alpha, ctx.alphaLocked);
        });
    } else {
        footprint.forEachPixel<utils::ColorRGBA>(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
            double alpha = ink.alphaAt(pixel);
            if (alpha <= 0.0 || !permission.apply(pixel.gx, pixel.gy, alpha) || alpha <= 0.0) return false;
            return raster::straightOver(dst, dab.color, alpha, ctx.alphaLocked);
        });
    }
}

} // namespace aladyn::engine::engines
