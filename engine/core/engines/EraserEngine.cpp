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

    const double aspect = std::max(0.05, profile.tip.aspectRatio);
    const raster::DabFootprint footprint(dab, dab.radius, aspect, tileGrid);
    if (footprint.empty()) return;

    const raster::TipShape tip(profile, dab.radius);
    const raster::PixelPermission permission(ctx);
    footprint.forEachPixel(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
        const double shape = tip.alphaAt(pixel);
        if (shape <= 0.0) return false;

        double strength = dab.opacity * shape;
        if (!permission.apply(pixel.gx, pixel.gy, strength) || strength <= 0.0) return false;

        const double remaining = (static_cast<double>(dst.a) / 255.0) * (1.0 - strength);
        dst.a = static_cast<uint8_t>(std::clamp(remaining * 255.0, 0.0, 255.0));
        return true;
    });
}

} // namespace aladyn::engine::engines
