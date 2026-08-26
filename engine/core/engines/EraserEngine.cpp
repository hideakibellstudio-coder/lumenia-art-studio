#include "EraserEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::engines {

void EraserEngine::renderDab(
    const raster::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,  // NÃO USADO
    canvas::TileGrid& tileGrid,
    const canvas::PixelBuffer* /*compositeBuffer*/,
    const raster::PixelContext& ctx
) {
    if (ctx.alphaLocked) return; // Alpha Lock bloqueia alteração de transparência pela borracha
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

                const double uDab = std::clamp((rotX + r) / (2.0 * r), 0.0, 1.0);
                const double vDab = std::clamp((scaledY + r) / (2.0 * r), 0.0, 1.0);

                // Forma da ponta (shapeTexture ou fallback com hardness)
                double shapeAlpha = 1.0;
                if (profile.shapeTexture) {
                    shapeAlpha = profile.shapeTexture->sampleNormalized(uDab, vDab,
                        texture::TextureWrapMode::Clamp);
                } else {
                    const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
                    if (dist > hardSpan) {
                        shapeAlpha = std::clamp((r - dist) / std::max(0.001, r - hardSpan), 0.0, 1.0);
                    }
                }

                // Subpixel anti-aliasing na extremidade
                if (dist > r - 0.5) {
                    shapeAlpha *= std::clamp((r - dist) / 0.5, 0.0, 1.0);
                }

                if (shapeAlpha <= 0.0) continue;

                // Força de apagamento = opacidade do dab × alpha da forma
                double eraseStrength = dab.opacity * shapeAlpha;
                if (ctx.selectionMask && ctx.selectionMask->hasSelection()) {
                    const int gx = tilePixelX + px;
                    const int gy = tilePixelY + py;
                    const uint8_t sVal = ctx.selectionMask->getValue(gx, gy);
                    if (sVal == 0) continue;
                    if (sVal < 255) {
                        eraseStrength *= (static_cast<double>(sVal) / 255.0);
                    }
                }

                if (ctx.clipBaseLayer) {
                    const int bTx = (tilePixelX + px) / canvas::Tile::TILE_SIZE;
                    const int bTy = (tilePixelY + py) / canvas::Tile::TILE_SIZE;
                    const int bPx = (tilePixelX + px) % canvas::Tile::TILE_SIZE;
                    const int bPy = (tilePixelY + py) % canvas::Tile::TILE_SIZE;
                    const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(ctx.clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                    if (!bTile) continue;
                    const double baseA = static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0;
                    if (baseA <= 0.0) continue;
                    eraseStrength *= baseA;
                }
                if (eraseStrength <= 0.0) continue;

                // DabBlendMode::Erase — reduz alpha do destino proporcionalmente
                raster::ColorRGBA dst = buffer.getPixel(px, py);
                const double dstA = static_cast<double>(dst.a) / 255.0;
                const double newA = dstA * (1.0 - eraseStrength);

                dst.a = static_cast<uint8_t>(std::clamp(newA * 255.0, 0.0, 255.0));
                buffer.setPixel(px, py, dst);
                tileModified = true;
            }
        }
        if (tileModified) tile->setDirty(true);
    }
}

} // namespace aladyn::engine::engines
