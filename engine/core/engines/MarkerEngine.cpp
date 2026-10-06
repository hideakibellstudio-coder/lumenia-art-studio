#include "MarkerEngine.hpp"
#include "../raster/DabFootprint.hpp"
#include "../raster/PixelPermission.hpp"
#include "../raster/StrokeInkLedger.hpp"
#include "../../utils/MathUtils.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::engines {

namespace {

constexpr double kPi = 3.14159265358979323846;

// A tinta de um marcador de álcool: borda suave com um leve escurecimento no anel externo, e uma
// veladura que multiplica a cor do que já está embaixo sem nunca passar de 70% da cor da tinta (um
// vermelho não vira preto). `strengthAt` é a opacidade do pixel; `blend` põe a tinta no destino.
//
// A cor sai do pixel como ele era ANTES do traço (`StrokeInkLedger`) e da cobertura que o traço já
// alcançou: o miolo de um traço tem a cor da tinta, uma vez só; carimbo sobre carimbo não escurece.
// Só um traço novo por cima multiplica a cor de novo (até o piso de 70%).
class MarkerInk {
public:
    MarkerInk(const utils::Dab& dab, const brush::BrushProfile& profile)
        : m_color(dab.color), m_opacity(dab.opacity), m_safeRadius(std::max(0.001, dab.radius)),
          m_wetness(std::clamp(profile.markerParams.solventWetness, 0.0, 1.0)),
          m_edgeDarkening(std::clamp(profile.markerParams.edgeDarkening, 0.0, 1.0)),
          m_hardness(std::clamp(profile.hardness, 0.0, 0.99)),
          m_srcR(static_cast<double>(dab.color.r) / 255.0),
          m_srcG(static_cast<double>(dab.color.g) / 255.0),
          m_srcB(static_cast<double>(dab.color.b) / 255.0) {
        // Limite mínimo de saturação/luminância da tinta do marcador (impede que vermelho vire preto!)
        m_minR = m_srcR * 0.70;
        m_minG = m_srcG * 0.70;
        m_minB = m_srcB * 0.70;
    }

    // Expansão sutil de solvente de álcool no papel.
    static double reachScale(const brush::BrushProfile& profile) {
        return 1.0 + std::clamp(profile.markerParams.solventWetness, 0.0, 1.0) * 0.12;
    }
    static double reach(const utils::Dab& dab, const brush::BrushProfile& profile) {
        return dab.radius * reachScale(profile);
    }

    // 0 quando o pixel não recebe tinta.
    double strengthAt(const raster::DabPixel& pixel) const {
        const double dist = std::sqrt(pixel.distSq);
        const double normalizedDist = dist / m_safeRadius;

        // Hardness & Falloff com interpolação cúbica suave (elimina degraus visíveis)
        double shape = 1.0;
        const double hardSpan = m_hardness * m_safeRadius;
        if (dist > hardSpan) {
            const double span = std::max(0.001, m_safeRadius - hardSpan);
            const double t = std::clamp((m_safeRadius - dist) / span, 0.0, 1.0);
            shape = t * t * (3.0 - 2.0 * t);
        }
        if (shape <= 0.0) return 0.0;

        // Edge Darkening sutil apenas na margem externa capilar
        double edge = 1.0;
        if (m_edgeDarkening > 0.0 && normalizedDist > 0.8) {
            const double ring = (normalizedDist - 0.8) / 0.2;
            edge += std::sin(ring * kPi) * m_edgeDarkening * 0.2;
        }

        // Solvent Wetness modula a opacidade efetiva por passada
        return std::clamp(m_opacity * shape * edge * (1.0 - m_wetness * 0.2), 0.0, 1.0);
    }

    // Veladura translúcida: o alfa acumula carimbo a carimbo; a cor vem da base do traço e da cobertura.
    // true quando o pixel mudou.
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
            alpha = quantize(dst.a == 0 ? strength : std::clamp(dstA + strength * (1.0 - dstA) * kBuildUp, 0.0, 1.0));
        }
        const double baseAlpha = static_cast<double>(cell.base.a) / 255.0;
        dst = utils::ColorRGBA{
            inked(cell.base.r, m_srcR, m_minR, baseAlpha, coverage),
            inked(cell.base.g, m_srcG, m_minG, baseAlpha, coverage),
            inked(cell.base.b, m_srcB, m_minB, baseAlpha, coverage),
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
            const double dstA = static_cast<double>(dst.a) / 65535.0;
            alpha = quantize16(dst.a == 0 ? strength : std::clamp(dstA + strength * (1.0 - dstA) * kBuildUp, 0.0, 1.0));
        }
        const double baseAlpha = static_cast<double>(cell.base.a) / 65535.0;
        dst = utils::ColorRGBA16{
            inked16(cell.base.r, m_srcR, m_minR, baseAlpha, coverage),
            inked16(cell.base.g, m_srcG, m_minG, baseAlpha, coverage),
            inked16(cell.base.b, m_srcB, m_minB, baseAlpha, coverage),
            alpha
        };
        return true;
    }

private:
    // Quanto do alfa novo vem de cada carimbo depois do primeiro (o marcador deposita devagar).
    static constexpr double kBuildUp = 0.5;

    static uint8_t quantize(double unit) { return utils::MathUtils::unitToByte(unit); }
    static uint16_t quantize16(double unit) {
        return static_cast<uint16_t>(std::clamp(std::lround(unit * 65535.0), 0L, 65535L));
    }

    // Um canal da cor: sobre pixel sem tinta a cor é a da tinta (o alfa leva a cobertura); sobre tinta ou
    // papel, a tinta multiplica a base (com o piso) e a cobertura decide quanto disso aparece.
    static uint8_t inked(uint8_t base, double ink, double floor, double baseAlpha, double coverage) {
        if (baseAlpha <= 0.0) return quantize(ink);
        const double under = static_cast<double>(base) / 255.0;
        const double glaze = std::max(floor, under * ink);
        const double target = ink + (glaze - ink) * baseAlpha;
        return quantize(under + (target - under) * coverage);
    }

    static uint16_t inked16(uint16_t base, double ink, double floor, double baseAlpha, double coverage) {
        if (baseAlpha <= 0.0) return quantize16(ink);
        const double under = static_cast<double>(base) / 65535.0;
        const double glaze = std::max(floor, under * ink);
        const double target = ink + (glaze - ink) * baseAlpha;
        return quantize16(under + (target - under) * coverage);
    }

    utils::ColorRGBA m_color;
    double m_opacity;
    double m_safeRadius;
    double m_wetness;
    double m_edgeDarkening;
    double m_hardness;
    double m_srcR, m_srcG, m_srcB;
    double m_minR{0.0}, m_minG{0.0}, m_minB{0.0};
};

} // namespace

double MarkerEngine::reachScale(const brush::BrushProfile& profile) const noexcept {
    return MarkerInk::reachScale(profile);
}

void MarkerEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0 || dab.color.a == 0) return;

    const double aspect = raster::tipAspect(dab);
    const raster::DabFootprint footprint(dab, MarkerInk::reach(dab, profile), aspect, tileGrid);
    if (footprint.empty()) return;

    const MarkerInk ink(dab, profile);
    const raster::PixelPermission permission(ctx);
    if (tileGrid.getFormat() == canvas::PixelFormat::RGBA16) {
        m_ledger16.prepare(footprint.bounds(), tileGrid);
        footprint.forEachPixel<utils::ColorRGBA16>(6, [&](utils::ColorRGBA16& dst, const raster::DabPixel& pixel) {
            double strength = ink.strengthAt(pixel);
            if (strength <= 0.0 || !permission.apply(pixel.gx, pixel.gy, strength) || strength <= 0.0) return false;
            return ink.blend16(dst, m_ledger16.at(pixel.gx, pixel.gy), strength, ctx.alphaLocked);
        });
    } else {
        m_ledger.prepare(footprint.bounds(), tileGrid);
        footprint.forEachPixel<utils::ColorRGBA>(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
            double strength = ink.strengthAt(pixel);
            if (strength <= 0.0 || !permission.apply(pixel.gx, pixel.gy, strength) || strength <= 0.0) return false;
            return ink.blend(dst, m_ledger.at(pixel.gx, pixel.gy), strength, ctx.alphaLocked);
        });
    }
}

} // namespace aladyn::engine::engines
