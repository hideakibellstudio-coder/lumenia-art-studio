#include "EraserEngine.hpp"
#include "../raster/DabFootprint.hpp"
#include "../raster/PixelPermission.hpp"
#include "../raster/TipShape.hpp"
#include <algorithm>

namespace aladyn::engine::engines {

void EraserEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,  // NÃO USADO
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (ctx.alphaLocked) return; // Alpha Lock bloqueia alteração de transparência pela borracha
    if (dab.radius <= 0.0) return;

    const double aspect = raster::tipAspect(dab);
    const raster::DabFootprint footprint(dab, dab.radius, aspect, tileGrid);
    if (footprint.empty()) return;

    const raster::TipShape tip(profile, dab.radius);
    const raster::PixelPermission permission(ctx);
    if (tileGrid.getFormat() == canvas::PixelFormat::RGBA16) {
        footprint.forEachPixel<utils::ColorRGBA16>(6, [&](utils::ColorRGBA16& dst, const raster::DabPixel& pixel) {
            const double shape = tip.alphaAt(pixel);
            if (shape <= 0.0) return false;

            double strength = dab.opacity * shape;
            if (!permission.apply(pixel.gx, pixel.gy, strength) || strength <= 0.0) return false;

            const double remaining = (static_cast<double>(dst.a) / 65535.0) * (1.0 - strength);
            dst.a = static_cast<uint16_t>(std::clamp(remaining * 65535.0, 0.0, 65535.0));
            return true;
        });
    } else {
        footprint.forEachPixel<utils::ColorRGBA>(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
            const double shape = tip.alphaAt(pixel);
            if (shape <= 0.0) return false;

            double strength = dab.opacity * shape;
            if (!permission.apply(pixel.gx, pixel.gy, strength) || strength <= 0.0) return false;

            const double remaining = (static_cast<double>(dst.a) / 255.0) * (1.0 - strength);
            // Truncar é o certo para apagar: o alfa tem que chegar a 0, e arredondar deixaria um resíduo
            // fantasma de alguns níveis onde a força do carimbo é baixa.
            dst.a = static_cast<uint8_t>(std::clamp(remaining * 255.0, 0.0, 255.0));
            return true;
        });
    }
}

} // namespace aladyn::engine::engines
