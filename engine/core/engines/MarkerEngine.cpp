#include "MarkerEngine.hpp"
#include "../raster/DabFootprint.hpp"
#include "../raster/PixelPermission.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::engines {

namespace {

constexpr double kPi = 3.14159265358979323846;

// A tinta de um marcador de álcool: borda suave com um leve escurecimento no anel externo, e uma
// veladura que escurece o que já está embaixo sem nunca passar de 70% da cor da tinta (um vermelho
// não vira preto). `strengthAt` é a opacidade do pixel; `blend` põe a tinta no destino.
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
    static double reach(const utils::Dab& dab, const brush::BrushProfile& profile) {
        return dab.radius * (1.0 + std::clamp(profile.markerParams.solventWetness, 0.0, 1.0) * 0.12);
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

    // Veladura translúcida contínua sem colapso de cor. true quando o pixel mudou.
    bool blend(utils::ColorRGBA& dst, double strength, bool alphaLocked) const {
        if (alphaLocked) return absorbInto(dst, strength * 0.08, dst.a);
        if (dst.a == 0) {
            // Primeiro depósito: veladura translúcida da tinta do marcador
            dst = utils::ColorRGBA{m_color.r, m_color.g, m_color.b, quantize(strength)};
            return true;
        }
        // Opacidade cumulativa suave do marcador
        const double dstA = static_cast<double>(dst.a) / 255.0;
        const double outA = std::clamp(dstA + strength * (1.0 - dstA) * 0.5, 0.0, 1.0);
        // Absorção luminosa (Beer-Lambert modificada: saturação rica sem colapso de cor)
        return absorbInto(dst, strength * 0.06, quantize(outA));
    }

private:
    static uint8_t quantize(double unit) { return static_cast<uint8_t>(std::clamp(unit * 255.0, 0.0, 255.0)); }

    bool absorbInto(utils::ColorRGBA& dst, double absorb, uint8_t alpha) const {
        if (dst.a == 0) return false;
        const double dstR = static_cast<double>(dst.r) / 255.0;
        const double dstG = static_cast<double>(dst.g) / 255.0;
        const double dstB = static_cast<double>(dst.b) / 255.0;
        dst = utils::ColorRGBA{
            quantize(std::max(m_minR, dstR * (1.0 - absorb * (1.0 - m_srcR)))),
            quantize(std::max(m_minG, dstG * (1.0 - absorb * (1.0 - m_srcG)))),
            quantize(std::max(m_minB, dstB * (1.0 - absorb * (1.0 - m_srcB)))),
            alpha
        };
        return true;
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

void MarkerEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0 || dab.color.a == 0) return;

    const double aspect = std::max(0.05, profile.tip.aspectRatio);
    const raster::DabFootprint footprint(dab, MarkerInk::reach(dab, profile), aspect, tileGrid);
    if (footprint.empty()) return;

    const MarkerInk ink(dab, profile);
    const raster::PixelPermission permission(ctx);
    footprint.forEachPixel(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
        double strength = ink.strengthAt(pixel);
        if (strength <= 0.0 || !permission.apply(pixel.gx, pixel.gy, strength) || strength <= 0.0) return false;
        return ink.blend(dst, strength, ctx.alphaLocked);
    });
}

} // namespace aladyn::engine::engines
