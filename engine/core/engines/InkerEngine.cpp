#include "InkerEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::engines {

void InkerEngine::renderDab(
    const raster::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,  // NÃO USADO
    canvas::TileGrid& tileGrid,
    const canvas::PixelBuffer* /*compositeBuffer*/,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0) return;

    const double r = dab.radius;
    const double aspect = std::max(0.05, profile.tip.aspectRatio);
    const double maxR = r / aspect + 2.0;

    const math::Rect2D bounds{
        dab.position.x - maxR, dab.position.y - maxR,
        maxR * 2.0, maxR * 2.0
    };

    const auto tileIndices = canvas::SpatialCuller::getIntersectingTiles(
        bounds, tileGrid.getWidth(), tileGrid.getHeight()
    );

    const double radAngle = -dab.angle * (3.14159265358979323846 / 180.0);
    const double cosA = std::cos(radAngle);
    const double sinA = std::sin(radAngle);

    // inkFlowRate escala a opacidade de saída diretamente
    const double flowOpacity = dab.opacity * profile.inkerParams.inkFlowRate;

    for (const auto& idx : tileIndices) {
        canvas::Tile* tile = tileGrid.getOrCreateTile(idx.x, idx.y);
        if (!tile) continue;

        canvas::PixelBuffer& buffer = tile->getBuffer();
        const int tilePixelX = tile->getPixelX();
        const int tilePixelY = tile->getPixelY();

        const int minX = std::max(0, static_cast<int>(std::floor(bounds.getLeft())) - tilePixelX);
        const int maxX = std::min(canvas::Tile::TILE_SIZE - 1, static_cast<int>(std::ceil(bounds.getRight())) - tilePixelX);
        const int minY = std::max(0, static_cast<int>(std::floor(bounds.getTop())) - tilePixelY);
        const int maxY = std::min(canvas::Tile::TILE_SIZE - 1, static_cast<int>(std::ceil(bounds.getBottom())) - tilePixelY);

        bool tileModified = false;

        for (int py = minY; py <= maxY; ++py) {
            const double dy = static_cast<double>(tilePixelY + py) + 0.5 - dab.position.y;

            for (int px = minX; px <= maxX; ++px) {
                const double dx = static_cast<double>(tilePixelX + px) + 0.5 - dab.position.x;

                const double rotX = dx * cosA - dy * sinA;
                const double rotY = dx * sinA + dy * cosA;
                const double scaledY = rotY / aspect;
                const double dist = std::sqrt(rotX * rotX + scaledY * scaledY);

                if (dist > r + 1.0) continue;

                // Anti-aliasing suave por distância — sem hardness threshold,
                // InkerEngine usa apenas o subpixel de borda (1px de feather)
                double edgeAlpha;
                const double feather = std::max(0.5, r * (1.0 - std::clamp(profile.hardness, 0.0, 1.0)) * 0.3 + 0.5);
                if (dist <= r - feather) {
                    edgeAlpha = 1.0;
                } else {
                    edgeAlpha = std::clamp((r - dist) / feather, 0.0, 1.0);
                    // taperSmoothing suaviza o caimento de borda
                    const double ts = std::clamp(profile.inkerParams.taperSmoothing, 0.0, 1.0);
                    edgeAlpha = edgeAlpha * (1.0 - ts) + (edgeAlpha * edgeAlpha) * ts;
                }

                if (edgeAlpha <= 0.0) continue;

                const double finalAlpha = (static_cast<double>(dab.color.a) / 255.0)
                    * flowOpacity * edgeAlpha;
                if (finalAlpha <= 0.0) continue;

                double curFinalAlpha = finalAlpha;
                if (ctx.clipBaseLayer) {
                    const int bTx = (tilePixelX + px) / canvas::Tile::TILE_SIZE;
                    const int bTy = (tilePixelY + py) / canvas::Tile::TILE_SIZE;
                    const int bPx = (tilePixelX + px) % canvas::Tile::TILE_SIZE;
                    const int bPy = (tilePixelY + py) % canvas::Tile::TILE_SIZE;
                    const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(ctx.clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                    if (!bTile) continue;
                    const double baseA = static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0;
                    if (baseA <= 0.0) continue;
                    curFinalAlpha *= baseA;
                }

                if (curFinalAlpha <= 0.0) continue;

                const raster::ColorRGBA dst = buffer.getPixel(px, py);

                if (ctx.alphaLocked) {
                    if (dst.a == 0) continue;
                    const double srcA = curFinalAlpha;
                    const double dstA = static_cast<double>(dst.a) / 255.0;
                    const double invSrcA = 1.0 - srcA;

                    const double outR = (dab.color.r * srcA + dst.r * dstA * invSrcA) / (srcA + dstA * invSrcA);
                    const double outG = (dab.color.g * srcA + dst.g * dstA * invSrcA) / (srcA + dstA * invSrcA);
                    const double outB = (dab.color.b * srcA + dst.b * dstA * invSrcA) / (srcA + dstA * invSrcA);

                    buffer.setPixel(px, py, raster::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(outR, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outG, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outB, 0.0, 255.0)),
                        dst.a
                    });
                    tileModified = true;
                    continue;
                }

                const double dstA = static_cast<double>(dst.a) / 255.0;
                const double outA = curFinalAlpha + dstA * (1.0 - curFinalAlpha);

                if (outA > 0.0) {
                    const double outR = (dab.color.r * curFinalAlpha + dst.r * dstA * (1.0 - curFinalAlpha)) / outA;
                    const double outG = (dab.color.g * curFinalAlpha + dst.g * dstA * (1.0 - curFinalAlpha)) / outA;
                    const double outB = (dab.color.b * curFinalAlpha + dst.b * dstA * (1.0 - curFinalAlpha)) / outA;

                    buffer.setPixel(px, py, raster::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(outR, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outG, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outB, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outA * 255.0, 0.0, 255.0))
                    });
                    tileModified = true;
                }
            }
        }
        if (tileModified) tile->setDirty(true);
    }
}

} // namespace aladyn::engine::engines
