#include "OilImpastoEngine.hpp"
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

// Um pixel de tinta a óleo: a opacidade que a pincelada deposita e o brilho especular que ela soma.
struct OilSample {
    double strength;
    double specular;
};

// Tinta a óleo: ranhuras de cerda paralelas ao traço, crista de impasto nas bordas, brilho especular
// úmido de uma luz no canto superior esquerdo e uma fração de tinta fresca que a cerda carrega do
// que já está no canvas.
class OilPaint {
public:
    OilPaint(const utils::Dab& dab, const brush::BrushProfile& profile)
        : m_color(dab.color), m_opacity(dab.opacity), m_safeRadius(std::max(0.001, dab.radius)),
          m_hardSpan(std::clamp(profile.hardness, 0.0, 0.99) * m_safeRadius),
          m_impasto(std::clamp(profile.oilParams.impastoDepth, 0.0, 1.0)),
          m_bristles(std::clamp(profile.oilParams.bristleGrooves, 0.0, 1.0)),
          m_viscosity(std::clamp(profile.oilParams.viscosity, 0.0, 1.0)),
          m_specular(std::clamp(profile.oilParams.specularBrilliance, 0.0, 1.0)) {}

    // `strength` 0: o pixel não recebe tinta.
    OilSample sampleAt(const raster::DabPixel& pixel) const {
        const double dist = std::sqrt(pixel.distSq);
        const double normalizedDist = dist / m_safeRadius;

        // Dureza e falloff da borda do dab
        double shape = 1.0;
        if (dist > m_hardSpan) {
            shape = std::clamp((m_safeRadius - dist) / std::max(0.001, m_safeRadius - m_hardSpan), 0.0, 1.0);
        }
        if (shape <= 0.0) return {0.0, 0.0};

        const double bristle = bristleModulation(pixel.rotX);
        const double ridge = impastoRidge(normalizedDist);
        const double strength = std::clamp(m_opacity * shape * bristle * ridge * (0.6 + m_viscosity * 0.4), 0.0, 1.0);
        return {strength, specularHighlight(pixel, normalizedDist, bristle)};
    }

    // Compositing normal viscoso com brilho especular 3D. true se mudou o pixel.
    bool blend(utils::ColorRGBA& dst, const OilSample& sample, bool alphaLocked) const {
        if (alphaLocked && dst.a == 0) return false;

        const double srcA = (static_cast<double>(m_color.a) / 255.0) * sample.strength;
        const double dstR = static_cast<double>(dst.r) / 255.0;
        const double dstG = static_cast<double>(dst.g) / 255.0;
        const double dstB = static_cast<double>(dst.b) / 255.0;
        const double dstA = static_cast<double>(dst.a) / 255.0;

        // Mistura úmida (Wet Oil Mixing): o pincel carrega uma fração sutil da tinta fresca de baixo
        double pickup = 0.0;
        if (dstA > 0.0 && m_viscosity < 1.0) pickup = (1.0 - m_viscosity) * 0.18 * sample.strength;
        const double mixedR = mixWithCanvas(static_cast<double>(m_color.r) / 255.0, dstR, pickup);
        const double mixedG = mixWithCanvas(static_cast<double>(m_color.g) / 255.0, dstG, pickup);
        const double mixedB = mixWithCanvas(static_cast<double>(m_color.b) / 255.0, dstB, pickup);

        const double inverse = 1.0 - srcA;
        const double outA = srcA + dstA * inverse;
        if (!alphaLocked && !(outA > 0.0)) return false;

        // Com Alpha Lock o denominador é o mesmo e só o alfa do destino fica
        const double denominator = outA;
        dst = utils::ColorRGBA{
            toByte((mixedR * srcA + dstR * dstA * inverse) / denominator + sample.specular),
            toByte((mixedG * srcA + dstG * dstA * inverse) / denominator + sample.specular),
            toByte((mixedB * srcA + dstB * dstA * inverse) / denominator + sample.specular),
            alphaLocked ? dst.a : toByte(outA)
        };
        return true;
    }

private:
    // Ranhuras de cerdas (Bristle Grooves): frequência transversal.
    double bristleModulation(double rotX) const {
        if (!(m_bristles > 0.0)) return 1.0;
        const double wave = std::abs(std::sin(rotX * 0.45));
        return (1.0 - m_bristles * 0.6) + wave * m_bristles * 0.6;
    }

    // Acúmulo de crista de impasto (Impasto Ridge) nas bordas.
    double impastoRidge(double normalizedDist) const {
        if (!(m_impasto > 0.0 && normalizedDist >= 0.65 && normalizedDist <= 0.95)) return 1.0;
        const double ridge = std::sin((normalizedDist - 0.65) / 0.3 * kPi);
        return 1.0 + ridge * m_impasto * 0.8;
    }

    // Highlight especular úmido (Luster Gloss 3D): reflexo direcional de uma luz no canto superior esquerdo.
    double specularHighlight(const raster::DabPixel& pixel, double normalizedDist, double bristle) const {
        if (!(m_specular > 0.0 && normalizedDist <= 0.85)) return 0.0;
        const double normalX = pixel.rotX / m_safeRadius;
        const double normalY = pixel.rotY / m_safeRadius;
        const double lightX = -0.577;
        const double lightY = -0.577;
        const double dotL = std::max(0.0, -(normalX * lightX + normalY * lightY));
        return std::pow(dotL, 4.0) * m_specular * 0.35 * bristle;
    }

    static double mixWithCanvas(double src, double under, double pickup) {
        return pickup > 0.0 ? src * (1.0 - pickup) + under * pickup : src;
    }

    utils::ColorRGBA m_color;
    double m_opacity;
    double m_safeRadius;
    double m_hardSpan;
    double m_impasto;
    double m_bristles;
    double m_viscosity;
    double m_specular;
};

} // namespace

void OilImpastoEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0 || dab.color.a == 0) return;

    const double aspect = std::max(0.05, profile.tip.aspectRatio);
    const raster::DabFootprint footprint(dab, dab.radius, aspect, tileGrid);
    if (footprint.empty()) return;

    const OilPaint paint(dab, profile);
    const raster::PixelPermission permission(ctx);
    footprint.forEachPixel(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
        OilSample sample = paint.sampleAt(pixel);
        if (sample.strength <= 0.0 || !permission.apply(pixel.gx, pixel.gy, sample.strength) || sample.strength <= 0.0) return false;
        return paint.blend(dst, sample, ctx.alphaLocked);
    });
}

} // namespace aladyn::engine::engines
