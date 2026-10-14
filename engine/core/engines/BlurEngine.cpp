#include "BlurEngine.hpp"
#include "BlurredRegion.hpp"
#include "../canvas/PixelFormat.hpp"
#include "../raster/DabFootprint.hpp"
#include "../raster/LargeBrushOptimizer.hpp"
#include "../raster/PixelPermission.hpp"
#include "../../utils/ColorRGBA16.hpp"
#include "../../utils/MathUtils.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::engines {

namespace {

// Acima disto (16 MB por campo, um pincel de uns 600 px) a memória de trabalho não fica guardada entre carimbos.
constexpr std::size_t kMaxRetainedFloats = 4u * 1024u * 1024u;

// Mistura o pixel original com o desfocado na proporção `mix`; com Alpha Lock o alfa fica.
utils::ColorRGBA mixTowardBlur(
    utils::ColorRGBA original, const BlurredRegion<utils::ColorRGBA>::Blurred& blurred, double mix, bool alphaLocked
) {
    float targetR = static_cast<float>(original.r);
    float targetG = static_cast<float>(original.g);
    float targetB = static_cast<float>(original.b);
    if (blurred.alphaWeight > 0.0f) {
        targetR = blurred.r / blurred.alphaWeight;
        targetG = blurred.g / blurred.alphaWeight;
        targetB = blurred.b / blurred.alphaWeight;
    }
    const auto toward = [mix](uint8_t from, float to) {
        return static_cast<double>(from) * (1.0 - mix) + static_cast<double>(to) * mix;
    };
    double outA = static_cast<double>(original.a);
    if (!alphaLocked) {
        const double smoothedA = (blurred.totalWeight > 0.0f) ? static_cast<double>(blurred.a / blurred.totalWeight)
                                                              : static_cast<double>(original.a);
        outA = static_cast<double>(original.a) * (1.0 - mix) + smoothedA * mix;
    }
    const auto byte = [](double v) { return utils::MathUtils::roundToByte(v); };
    return utils::ColorRGBA{byte(toward(original.r, targetR)), byte(toward(original.g, targetG)),
                            byte(toward(original.b, targetB)), byte(outA)};
}

utils::ColorRGBA16 mixTowardBlur16(
    utils::ColorRGBA16 original, const BlurredRegion<utils::ColorRGBA16>::Blurred& blurred, double mix, bool alphaLocked
) {
    float targetR = static_cast<float>(original.r);
    float targetG = static_cast<float>(original.g);
    float targetB = static_cast<float>(original.b);
    if (blurred.alphaWeight > 0.0f) {
        targetR = blurred.r / blurred.alphaWeight;
        targetG = blurred.g / blurred.alphaWeight;
        targetB = blurred.b / blurred.alphaWeight;
    }
    const auto toward = [mix](uint16_t from, float to) {
        return static_cast<double>(from) * (1.0 - mix) + static_cast<double>(to) * mix;
    };
    double outA = static_cast<double>(original.a);
    if (!alphaLocked) {
        const double smoothedA = (blurred.totalWeight > 0.0f) ? static_cast<double>(blurred.a / blurred.totalWeight)
                                                              : static_cast<double>(original.a);
        outA = static_cast<double>(original.a) * (1.0 - mix) + smoothedA * mix;
    }
    const auto word = [](double v) { return static_cast<uint16_t>(std::clamp(std::lround(v), 0L, 65535L)); };
    return utils::ColorRGBA16{word(toward(original.r, targetR)), word(toward(original.g, targetG)),
                              word(toward(original.b, targetB)), word(outA)};
}

} // namespace

void BlurEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0) return;

    const double r    = dab.radius;
    const double maxR = r + 2.0;  // o desfoque ignora o achatamento da ponta: o dab é sempre um círculo

    const int blurRadiusSetting = std::clamp(profile.blurParams.blurRadius, 1, 5);
    const double strength       = std::clamp(profile.blurParams.blurStrength, 0.0, 1.0);

    // Raio do kernel proporcional ao dab (mínimo 2px, máximo 20px)
    const int kernelRadius = std::clamp(
        static_cast<int>(std::round(r * 0.20 * static_cast<double>(blurRadiusSetting))), 2, 20);
    const double sigma = std::max(0.8, static_cast<double>(kernelRadius) * (0.35 + strength * 0.45));

    // Caixa do dab com a margem do kernel, para a cópia da área
    const BlurBox roi{
        std::max(0, static_cast<int>(std::floor(dab.position.x - maxR))),
        std::min(tileGrid.getWidth() - 1, static_cast<int>(std::ceil(dab.position.x + maxR))),
        std::max(0, static_cast<int>(std::floor(dab.position.y - maxR))),
        std::min(tileGrid.getHeight() - 1, static_cast<int>(std::ceil(dab.position.y + maxR)))};
    if (roi.empty()) return;

    // O desfoque ignora a rotação e o achatamento da ponta: o dab é sempre um círculo.
    utils::Dab disc = dab;
    disc.angle = 0.0;
    const raster::DabFootprint footprint(disc, r, 1.0, tileGrid);
    if (footprint.empty()) return;

    const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
    const double spanInv  = 1.0 / std::max(0.001, r - hardSpan);
    const raster::PixelPermission permission(ctx);

    if (tileGrid.getFormat() == canvas::PixelFormat::RGBA16) {
        const BlurredRegion<utils::ColorRGBA16> region(m_scratch, tileGrid, roi, kernelRadius, sigma);
        if (region.empty()) return;
        footprint.forEachPixel<utils::ColorRGBA16>(6, [&](utils::ColorRGBA16& dst, const raster::DabPixel& pixel) {
            if (!roi.contains(pixel.gx, pixel.gy)) return false;
            const double dist = std::sqrt(pixel.distSq);
            const double shape = dist > hardSpan ? raster::LargeBrushOptimizer::smoothHermite((r - dist) * spanInv) : 1.0;
            double mix = dab.opacity * shape * strength;
            if (shape <= 0.0 || mix <= 0.0) return false;

            const utils::ColorRGBA16 original = dst;  // ainda não escrito neste carimbo: cada pixel é visitado uma vez
            const auto blurred = region.blurredAt(pixel.gx, pixel.gy);
            if (original.a == 0 && blurred.alphaWeight <= 0.0f) return false;
            if (ctx.alphaLocked && original.a == 0) return false;

            if (!permission.apply(pixel.gx, pixel.gy, mix) || mix <= 0.0) return false;
            dst = mixTowardBlur16(original, blurred, mix, ctx.alphaLocked);
            return true;
        });
    } else {
        const BlurredRegion<utils::ColorRGBA> region(m_scratch, tileGrid, roi, kernelRadius, sigma);
        if (region.empty()) return;
        footprint.forEachPixel<utils::ColorRGBA>(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
            if (!roi.contains(pixel.gx, pixel.gy)) return false;
            const double dist = std::sqrt(pixel.distSq);
            const double shape = dist > hardSpan ? raster::LargeBrushOptimizer::smoothHermite((r - dist) * spanInv) : 1.0;
            double mix = dab.opacity * shape * strength;
            if (shape <= 0.0 || mix <= 0.0) return false;

            const utils::ColorRGBA original = dst;  // ainda não escrito neste carimbo: cada pixel é visitado uma vez
            const auto blurred = region.blurredAt(pixel.gx, pixel.gy);
            if (original.a == 0 && blurred.alphaWeight <= 0.0f) return false;
            if (ctx.alphaLocked && original.a == 0) return false;

            if (!permission.apply(pixel.gx, pixel.gy, mix) || mix <= 0.0) return false;
            dst = mixTowardBlur(original, blurred, mix, ctx.alphaLocked);
            return true;
        });
    }
    m_scratch.releaseIfLarge(kMaxRetainedFloats);
}

} // namespace aladyn::engine::engines
