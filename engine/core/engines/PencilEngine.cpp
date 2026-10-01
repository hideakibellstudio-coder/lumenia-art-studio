#include "PencilEngine.hpp"
#include "../raster/DabFootprint.hpp"
#include "../raster/LargeBrushOptimizer.hpp"
#include "../raster/PixelPermission.hpp"
#include "../raster/StraightOver.hpp"
#include "../../utils/MathUtils.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::engines {

namespace {

// O que o grafite depositaria num pixel do dab: a forma da ponta, o relevo do grafite e o do papel.
// Constantes do dab ficam calculadas uma vez; `alphaAt` é só o que depende do pixel.
class GraphiteDeposit {
public:
    GraphiteDeposit(const utils::Dab& dab, const brush::BrushProfile& profile, const canvas::CanvasTexture& paper)
        : m_profile(profile), m_paper(paper),
          m_radius(dab.radius),
          m_safeRadius(std::max(0.001, dab.radius)),
          m_baseAlpha((static_cast<double>(dab.color.a) / 255.0) * dab.opacity) {
        // Lápis duro (2H) tem teto de escuridão cinza prateado (~60%); macio (6B) deposita preto profundo (100%)
        const double hardness = std::clamp(profile.pencilParams.graphiteHardness, 0.0, 1.0);
        m_darknessCap = 1.0 - std::clamp(hardness - 0.4, 0.0, 0.6) * 0.65;
        m_threshold = (1.0 - dab.pressure) + (profile.pencilParams.graphiteHardness - 0.5) * 0.4;
    }

    // 0 quando o pixel não recebe grafite.
    double alphaAt(const raster::DabPixel& pixel) const {
        const double dist = std::sqrt(pixel.distSq);
        const double u = std::clamp((pixel.rotX + m_safeRadius) / (2.0 * m_safeRadius), 0.0, 1.0);
        const double v = std::clamp((pixel.scaledY + m_safeRadius) / (2.0 * m_safeRadius), 0.0, 1.0);

        double shape = tipShape(dist, u, v);
        if (shape <= 0.0) return 0.0;

        const double globalX = static_cast<double>(pixel.gx) + 0.5;
        const double globalY = static_cast<double>(pixel.gy) + 0.5;
        const double paperHeight = paperRelief(globalX, globalY);
        const double combined = graphiteRelief(u, v) * (paperHeight * paperHeight);
        const double ink = utils::MathUtils::smoothstep(m_threshold - 0.14, m_threshold + 0.14, combined);

        // Subpixel anti-aliasing na borda extrema do dab
        if (dist > m_radius - 0.5) shape *= std::clamp((m_radius - dist) / 0.5, 0.0, 1.0);
        return m_baseAlpha * shape * ink * m_darknessCap;
    }

private:
    double tipShape(double dist, double u, double v) const {
        if (m_profile.shapeTexture) {
            return m_profile.shapeTexture->sampleNormalized(u, v, texture::TextureWrapMode::Clamp);
        }
        const double hardSpan = std::clamp(m_profile.hardness, 0.0, 0.99) * m_safeRadius;
        if (dist <= hardSpan) return 1.0;
        return raster::LargeBrushOptimizer::smoothHermite((m_safeRadius - dist) / std::max(0.001, m_safeRadius - hardSpan));
    }

    // Textura de altura do grafite, móvel com o dab.
    double graphiteRelief(double u, double v) const {
        if (!(m_profile.brushGrainEnabled && m_profile.brushHeightTexture)) return 1.0;
        double height = m_profile.brushHeightTexture->sampleNormalized(
            u * m_profile.brushGrainScale, v * m_profile.brushGrainScale, texture::TextureWrapMode::Repeat);
        if (m_profile.brushGrainInvert) height = 1.0 - height;
        height = withContrast(height, m_profile.brushGrainContrast);
        return m_profile.brushTextureCurve.sample(height);
    }

    // Textura de altura do papel, fixa no canvas (central no lápis).
    double paperRelief(double globalX, double globalY) const {
        if (!(m_paper.canvasGrainEnabled && m_paper.canvasHeightTexture)) return 1.0;
        double height = m_paper.canvasHeightTexture->sampleNormalized(
            globalX * 0.002 * m_paper.canvasGrainScale, globalY * 0.002 * m_paper.canvasGrainScale,
            texture::TextureWrapMode::Repeat);
        if (m_paper.canvasGrainInvert) height = 1.0 - height;
        height = withContrast(height, m_paper.canvasGrainContrast);
        return m_paper.canvasTextureCurve.sample(height);
    }

    static double withContrast(double height, double contrast) {
        if (contrast == 1.0 || contrast <= 0.0) return height;
        const double halfSpan = 0.5 / contrast;
        return utils::MathUtils::smoothstep(0.5 - halfSpan, 0.5 + halfSpan, height);
    }

    const brush::BrushProfile& m_profile;
    const canvas::CanvasTexture& m_paper;
    double m_radius;
    double m_safeRadius;
    double m_baseAlpha;
    double m_darknessCap{1.0};
    double m_threshold{0.0};
};

} // namespace

void PencilEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& canvasTexture,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0 || dab.color.a == 0) return;

    const double aspect = std::max(0.05, profile.tip.aspectRatio);
    const raster::DabFootprint footprint(dab, dab.radius, aspect, tileGrid);
    if (footprint.empty()) return;

    const GraphiteDeposit graphite(dab, profile, canvasTexture);
    const raster::PixelPermission permission(ctx);
    footprint.forEachPixel(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
        double alpha = graphite.alphaAt(pixel);
        if (alpha <= 0.0 || !permission.apply(pixel.gx, pixel.gy, alpha) || alpha <= 0.0) return false;
        return raster::straightOver(dst, dab.color, alpha, ctx.alphaLocked);
    });
}

} // namespace aladyn::engine::engines
