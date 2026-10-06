#include "WatercolorEngine.hpp"
#include "../raster/DabFootprint.hpp"
#include "../raster/PixelPermission.hpp"
#include "../raster/StrokeInkLedger.hpp"
#include "../../utils/MathUtils.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::engines {

namespace {

constexpr double kPi = 3.14159265358979323846;

uint8_t toByte(double unit) {
    return utils::MathUtils::unitToByte(unit);
}

// Uma mancha de aquarela: miolo aquoso, anel escuro de secagem na borda (Coffee Ring), pigmento
// que se acumula nos vales do papel (granulação) e uma veladura subtrativa ao compor.
//
// A cor sai do pixel como ele era ANTES do traço (`StrokeInkLedger`) e da cobertura que o traço já
// alcançou: o pigmento filtra o fundo uma vez só. Até 2026-10-02 cada carimbo filtrava o resultado do
// anterior, e o miolo de um traço azul (30, 90, 170) chegava a (2, 7, 31).
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
    static double reachScale(const brush::BrushProfile& profile) {
        const double bleed = std::clamp(profile.watercolorParams.pigmentBleed, 0.0, 1.0);
        const double water = std::clamp(profile.watercolorParams.waterLevel, 0.0, 1.0);
        return 1.0 + bleed * water * 0.4;
    }
    static double reach(const utils::Dab& dab, const brush::BrushProfile& profile) {
        return dab.radius * reachScale(profile);
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

    // Veladura translúcida: a tinta tinge o que está embaixo em vez de cobri-lo. O alfa acumula carimbo a
    // carimbo; a cor vem da base do traço e da cobertura. true se mudou o pixel.
    bool blend(utils::ColorRGBA& dst, raster::StrokeInkLedger<utils::ColorRGBA>::Cell& cell, double strength, bool alphaLocked) const {
        if (alphaLocked && dst.a == 0) return false;
        const bool firstTouch = cell.coverage <= 0.0f;
        if (firstTouch) cell.base = dst;
        const double covered = firstTouch ? 0.0 : static_cast<double>(cell.coverage);
        const double coverage = firstTouch ? strength : std::clamp(covered + strength * (1.0 - covered) * kBuildUp, 0.0, 1.0);
        cell.coverage = static_cast<float>(coverage);

        uint8_t alpha = dst.a;
        if (!alphaLocked) {
            const double dstA = static_cast<double>(dst.a) / 255.0;  // dst.a == 0: primeiro depósito
            alpha = toByte(dst.a == 0 ? strength : std::clamp(dstA + strength * (1.0 - dstA) * kBuildUp, 0.0, 1.0));
        }
        const double baseAlpha = static_cast<double>(cell.base.a) / 255.0;
        dst = utils::ColorRGBA{
            washed(cell.base.r, m_srcR, baseAlpha, coverage, alphaLocked),
            washed(cell.base.g, m_srcG, baseAlpha, coverage, alphaLocked),
            washed(cell.base.b, m_srcB, baseAlpha, coverage, alphaLocked),
            alpha
        };
        return true;
    }

    bool blend16(utils::ColorRGBA16& dst, raster::StrokeInkLedger<utils::ColorRGBA16>::Cell& cell, double strength, bool alphaLocked) const {
        if (alphaLocked && dst.a == 0) return false;
        const bool firstTouch = cell.coverage <= 0.0f;
        if (firstTouch) cell.base = dst;
        const double covered = firstTouch ? 0.0 : static_cast<double>(cell.coverage);
        const double coverage = firstTouch ? strength : std::clamp(covered + strength * (1.0 - covered) * kBuildUp, 0.0, 1.0);
        cell.coverage = static_cast<float>(coverage);

        uint16_t alpha = dst.a;
        if (!alphaLocked) {
            const double dstA = static_cast<double>(dst.a) / 65535.0;  // dst.a == 0: primeiro depósito
            alpha = toWord(dst.a == 0 ? strength : std::clamp(dstA + strength * (1.0 - dstA) * kBuildUp, 0.0, 1.0));
        }
        const double baseAlpha = static_cast<double>(cell.base.a) / 65535.0;
        dst = utils::ColorRGBA16{
            washed16(cell.base.r, m_srcR, baseAlpha, coverage, alphaLocked),
            washed16(cell.base.g, m_srcG, baseAlpha, coverage, alphaLocked),
            washed16(cell.base.b, m_srcB, baseAlpha, coverage, alphaLocked),
            alpha
        };
        return true;
    }

private:
    // Quanto do alfa novo vem de cada carimbo depois do primeiro (a mancha deposita devagar).
    static constexpr double kBuildUp = 0.4;

    static uint16_t toWord(double unit) {
        return static_cast<uint16_t>(std::clamp(std::lround(unit * 65535.0), 0L, 65535L));
    }

    // Um canal da cor: sobre pixel sem tinta a cor é a do pigmento (o alfa leva a cobertura); sobre tinta
    // ou papel, o pigmento filtra a base (com Alpha Lock só o filtro; fora dele, diluído pela água) e a
    // cobertura decide quanto disso aparece.
    uint8_t washed(uint8_t base, double src, double baseAlpha, double coverage, bool alphaLocked) const {
        if (baseAlpha <= 0.0) return toByte(src);
        const double under = static_cast<double>(base) / 255.0;
        const double glaze = alphaLocked ? src * under : dilutedGlaze(src, under);
        const double target = src + (glaze - src) * baseAlpha;
        return toByte(under + (target - under) * coverage);
    }

    uint16_t washed16(uint16_t base, double src, double baseAlpha, double coverage, bool alphaLocked) const {
        if (baseAlpha <= 0.0) return toWord(src);
        const double under = static_cast<double>(base) / 65535.0;
        const double glaze = alphaLocked ? src * under : dilutedGlaze(src, under);
        const double target = src + (glaze - src) * baseAlpha;
        return toWord(under + (target - under) * coverage);
    }

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

double WatercolorEngine::reachScale(const brush::BrushProfile& profile) const noexcept {
    return WatercolorWash::reachScale(profile);
}

void WatercolorEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& canvasTexture,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0 || dab.color.a == 0) return;

    const double aspect = raster::tipAspect(dab);
    const raster::DabFootprint footprint(dab, WatercolorWash::reach(dab, profile), aspect, tileGrid);
    if (footprint.empty()) return;

    const WatercolorWash wash(dab, profile, canvasTexture);
    const raster::PixelPermission permission(ctx);
    if (tileGrid.getFormat() == canvas::PixelFormat::RGBA16) {
        m_ledger16.prepare(footprint.bounds(), tileGrid);
        footprint.forEachPixel<utils::ColorRGBA16>(6, [&](utils::ColorRGBA16& dst, const raster::DabPixel& pixel) {
            double strength = wash.strengthAt(pixel);
            if (strength <= 0.0 || !permission.apply(pixel.gx, pixel.gy, strength) || strength <= 0.0) return false;
            return wash.blend16(dst, m_ledger16.at(pixel.gx, pixel.gy), strength, ctx.alphaLocked);
        });
    } else {
        m_ledger.prepare(footprint.bounds(), tileGrid);
        footprint.forEachPixel<utils::ColorRGBA>(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
            double strength = wash.strengthAt(pixel);
            if (strength <= 0.0 || !permission.apply(pixel.gx, pixel.gy, strength) || strength <= 0.0) return false;
            return wash.blend(dst, m_ledger.at(pixel.gx, pixel.gy), strength, ctx.alphaLocked);
        });
    }
}

} // namespace aladyn::engine::engines
