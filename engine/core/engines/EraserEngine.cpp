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

    // ─── 1. CIRCLE-AABB CULLING: Descarte antecipado ───
    const double maxRSq = maxR * maxR;
    std::vector<canvas::Tile*> validTiles;
    validTiles.reserve(tileIndices.size());

    for (const auto& idx : tileIndices) {
        const double tileX0 = static_cast<double>(idx.x * canvas::Tile::TILE_SIZE);
        const double tileX1 = tileX0 + canvas::Tile::TILE_SIZE;
        const double tileY0 = static_cast<double>(idx.y * canvas::Tile::TILE_SIZE);
        const double tileY1 = tileY0 + canvas::Tile::TILE_SIZE;

        const double clampX = std::clamp(dab.position.x, tileX0, tileX1);
        const double clampY = std::clamp(dab.position.y, tileY0, tileY1);
        const double dX = dab.position.x - clampX;
        const double dY = dab.position.y - clampY;
        if (dX * dX + dY * dY > maxRSq) {
            continue;
        }

        canvas::Tile* tile = tileGrid.getOrCreateTile(idx.x, idx.y);
        if (tile) {
            validTiles.push_back(tile);
        }
    }

    if (validTiles.empty()) return;

    // ─── 2. PRÉ-CÁLCULOS ANALÍTICOS ───
    const bool isCircular = (aspect >= 0.999) && (std::abs(dab.angle) < 0.001);
    const double radAngle = isCircular ? 0.0 : (-dab.angle * (3.14159265358979323846 / 180.0));
    const double cosA = isCircular ? 1.0 : std::cos(radAngle);
    const double sinA = isCircular ? 0.0 : std::sin(radAngle);
    const double invAspect = isCircular ? 1.0 : (1.0 / aspect);

    const double safeR = std::max(0.001, r);
    const double invTwoSafeR = 0.5 / safeR;
    const double maxRadius = r + 1.0;
    const double maxRadiusSq = maxRadius * maxRadius;
    const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * safeR;
    const double hardSpanSq = hardSpan * hardSpan;
    const double invSoftSpan = 1.0 / std::max(0.001, safeR - hardSpan);
    const double outerSubpixelThresh = safeR - 0.5;
    const double outerSubpixelThreshSq = (outerSubpixelThresh > 0.0) ? (outerSubpixelThresh * outerSubpixelThresh) : 0.0;

    // ─── 3. EXECUÇÃO PARALELA MULTI-CORE ───
    const int numTiles = static_cast<int>(validTiles.size());
    #pragma omp parallel for schedule(static) if(numTiles >= 6)
    for (int t = 0; t < numTiles; ++t) {
        canvas::Tile* tile = validTiles[t];
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

                double rotX, scaledY, distSq;
                if (isCircular) {
                    rotX = dx;
                    scaledY = dy;
                    distSq = dx * dx + dy * dy;
                } else {
                    rotX = dx * cosA - dy * sinA;
                    const double rotY = dx * sinA + dy * cosA;
                    scaledY = rotY * invAspect;
                    distSq = rotX * rotX + scaledY * scaledY;
                }

                if (distSq > maxRadiusSq) continue;

                double shapeAlpha = 1.0;
                if (profile.shapeTexture) {
                    const double uDab = std::clamp((rotX + safeR) * invTwoSafeR, 0.0, 1.0);
                    const double vDab = std::clamp((scaledY + safeR) * invTwoSafeR, 0.0, 1.0);
                    shapeAlpha = profile.shapeTexture->sampleNormalized(uDab, vDab, texture::TextureWrapMode::Clamp);
                    const double dist = std::sqrt(distSq);
                    if (dist > outerSubpixelThresh) {
                        shapeAlpha *= std::clamp((safeR - dist) * 2.0, 0.0, 1.0);
                    }
                } else {
                    if (distSq > hardSpanSq || distSq > outerSubpixelThreshSq) {
                        const double dist = std::sqrt(distSq);
                        if (dist > hardSpan) {
                            shapeAlpha = std::clamp((safeR - dist) * invSoftSpan, 0.0, 1.0);
                        }
                        if (dist > outerSubpixelThresh) {
                            shapeAlpha *= std::clamp((safeR - dist) * 2.0, 0.0, 1.0);
                        }
                    }
                }

                if (shapeAlpha <= 0.0) continue;

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
