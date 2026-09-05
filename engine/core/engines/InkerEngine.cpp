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

    const double flowOpacity = dab.opacity * profile.inkerParams.inkFlowRate;
    const double maxRadius = r + 1.0;
    const double maxRadiusSq = maxRadius * maxRadius;

    const double feather = std::max(0.6, r * (1.0 - std::clamp(profile.hardness, 0.0, 1.0)) * 0.25 + 0.6);
    const double solidR = r - feather;
    const double solidRSq = (solidR > 0.0) ? (solidR * solidR) : 0.0;
    const double invFeather = 1.0 / feather;
    const double ts = std::clamp(profile.inkerParams.taperSmoothing, 0.0, 1.0);
    const double dabColorAlphaNorm = static_cast<double>(dab.color.a) / 255.0;
    const double baseAlpha = dabColorAlphaNorm * flowOpacity;

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

                double edgeAlpha = 1.0;
                if (distSq > solidRSq) {
                    const double dist = std::sqrt(distSq);
                    if (dist > r - feather) {
                        const double tVal = std::clamp((r - dist) * invFeather, 0.0, 1.0);
                        edgeAlpha = tVal * tVal * (3.0 - 2.0 * tVal) * (1.0 - ts * 0.25) + (tVal * tVal * tVal) * (ts * 0.25);
                    }
                }

                if (edgeAlpha <= 0.0) continue;

                const double finalAlpha = baseAlpha * edgeAlpha;
                if (finalAlpha <= 0.0) continue;

                double curFinalAlpha = finalAlpha;
                if (ctx.selectionMask && ctx.selectionMask->hasSelection()) {
                    const int gx = tilePixelX + px;
                    const int gy = tilePixelY + py;
                    const uint8_t sVal = ctx.selectionMask->getValue(gx, gy);
                    if (sVal == 0) continue;
                    if (sVal < 255) {
                        curFinalAlpha *= (static_cast<double>(sVal) / 255.0);
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
