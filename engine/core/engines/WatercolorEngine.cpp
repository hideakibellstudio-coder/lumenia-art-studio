#include "WatercolorEngine.hpp"
#include "../raster/DabFootprint.hpp"
#include "../raster/PixelPermission.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::engines {

namespace {

constexpr double kPi = 3.14159265358979323846;

uint8_t toByte(double unit) {
    return static_cast<uint8_t>(std::clamp(unit * 255.0, 0.0, 255.0));
}

// Uma mancha de aquarela: miolo aquoso, anel escuro de secagem na borda (Coffee Ring), pigmento
// que se acumula nos vales do papel (granulação) e uma veladura subtrativa ao compor.
class WatercolorWash {
public:
    WatercolorWash(const utils::Dab& dab, const brush::BrushProfile& profile, const canvas::CanvasTexture& paper)
        : m_color(dab.color), m_opacity(dab.opacity),
          m_radius(reach(dab, profile)),
          m_safeRadius(std::max(0.001, m_radius)),
          m_hardSpan(std::clamp(profile.hardness, 0.0, 0.99) * m_safeRadius),
          m_water(std::clamp(profile.watercolorParams.waterLevel, 0.0, 1.0)),
          m_fringe(std::clamp(profile.watercolorParams.fringeIntensity, 0.0, 1.0)),
          m_granulation(std::clamp(profile.watercolorParams.granulation, 0.0, 1.0)),
          m_paper(paper.canvasHeightTexture.get()),
          m_srcR(static_cast<double>(dab.color.r) / 255.0),
          m_srcG(static_cast<double>(dab.color.g) / 255.0),
          m_srcB(static_cast<double>(dab.color.b) / 255.0) {}

    // No modo Wet-on-Wet (sangramento alto) o raio de expansão cresce com pigmentBleed e a água.
    static double reach(const utils::Dab& dab, const brush::BrushProfile& profile) {
        const double bleed = std::clamp(profile.watercolorParams.pigmentBleed, 0.0, 1.0);
        const double water = std::clamp(profile.watercolorParams.waterLevel, 0.0, 1.0);
        return dab.radius * (1.0 + bleed * water * 0.4);
    }

    // A opacidade da mancha neste pixel; 0 quando ele não é tocado.
    double strengthAt(const raster::DabPixel& pixel) const {
        const double dist = std::sqrt(pixel.distSq);
        const double normalizedDist = dist / m_safeRadius;

        // Falloff procedural com miolo aquoso suave
        double shape = 1.0;
        if (dist > m_hardSpan) {
            shape = std::clamp((m_safeRadius - dist) / std::max(0.001, m_safeRadius - m_hardSpan), 0.0, 1.0);
        }
        if (shape <= 0.0) return 0.0;

        return std::clamp(
            m_opacity * shape * fringe(normalizedDist) * granulation(pixel) * (0.4 + m_water * 0.6),
            0.0, 1.0);
    }

    // Veladura translúcida: a tinta tinge o que está embaixo em vez de cobri-lo. true se mudou o pixel.
    bool blend(utils::ColorRGBA& dst, double strength, bool alphaLocked) const {
        if (!alphaLocked && dst.a == 0) {
            dst = utils::ColorRGBA{m_color.r, m_color.g, m_color.b, toByte(strength)};
            return true;
        }
        if (alphaLocked && dst.a == 0) return false;

        const double dstR = static_cast<double>(dst.r) / 255.0;
        const double dstG = static_cast<double>(dst.g) / 255.0;
        const double dstB = static_cast<double>(dst.b) / 255.0;
        const double dstA = static_cast<double>(dst.a) / 255.0;
        const auto mix = [&](double src, double under) {
            // Com Alpha Lock, só o filtro do pigmento; fora dele, a diluição pela água.
            const double glaze = alphaLocked ? src * under : dilutedGlaze(src, under);
            return under * (1.0 - strength) + glaze * strength;
        };
        const uint8_t alpha = alphaLocked ? dst.a : toByte(std::clamp(dstA + strength * (1.0 - dstA) * 0.4, 0.0, 1.0));
        dst = utils::ColorRGBA{toByte(mix(m_srcR, dstR)), toByte(mix(m_srcG, dstG)), toByte(mix(m_srcB, dstB)), alpha};
        return true;
    }

private:
    // Coffee Ring Effect: anel escuro de secagem no bordo capilar da mancha.
    double fringe(double normalizedDist) const {
        if (!(m_fringe > 0.0 && normalizedDist >= 0.6)) return 1.0;
        const double ring = (normalizedDist - 0.6) / 0.4;
        return 1.0 + std::sin(ring * kPi) * m_fringe * 1.5;
    }

    // Granulação: os vales do papel (altura < 0.5) acumulam mais pigmento; as cristas retêm menos.
    double granulation(const raster::DabPixel& pixel) const {
        if (!(m_granulation > 0.0 && m_paper)) return 1.0;
        const double height = m_paper->sampleNormalized(pixel.gx * 0.02, pixel.gy * 0.02);
        const double valleyDepth = (1.0 - height) - 0.5;
        return 1.0 + valleyDepth * m_granulation * 1.2;
    }

    // Veladura subtrativa ponderada por difusão, com diluição pela água (waterLevel).
    double dilutedGlaze(double src, double under) const {
        return (src * under) * (1.0 - m_water * 0.3) + (src * 0.5 + under * 0.5) * (m_water * 0.3);
    }

    utils::ColorRGBA m_color;
    double m_opacity;
    double m_radius;
    double m_safeRadius;
    double m_hardSpan;
    double m_water;
    double m_fringe;
    double m_granulation;
    const texture::Texture2D* m_paper;
    double m_srcR, m_srcG, m_srcB;
};

} // namespace

void WatercolorEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& canvasTexture,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0 || dab.color.a == 0) return;

    const double aspect = std::max(0.05, profile.tip.aspectRatio);
    const raster::DabFootprint footprint(dab, WatercolorWash::reach(dab, profile), aspect, tileGrid);
    if (footprint.empty()) return;

    const WatercolorWash wash(dab, profile, canvasTexture);
    const raster::PixelPermission permission(ctx);
    footprint.forEachPixel(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
        double strength = wash.strengthAt(pixel);
        if (strength <= 0.0 || !permission.apply(pixel.gx, pixel.gy, strength) || strength <= 0.0) return false;
        return wash.blend(dst, strength, ctx.alphaLocked);
    });
}

} // namespace aladyn::engine::engines
