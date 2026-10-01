#include "MarkerEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../../utils/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::engines {

void MarkerEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0 || dab.color.a == 0) return;

    const double r = dab.radius;
    const double aspect = std::max(0.05, profile.tip.aspectRatio);

    const double wetness = std::clamp(profile.markerParams.solventWetness, 0.0, 1.0);
    const double edgeDark = std::clamp(profile.markerParams.edgeDarkening, 0.0, 1.0);

    // Expansão sutil de solvente de álcool no papel
    const double effectiveRadius = r * (1.0 + wetness * 0.12);
    const double maxR = effectiveRadius / aspect + 2.0;

    const utils::Rect2D bounds{
        dab.position.x - maxR, dab.position.y - maxR,
        maxR * 2.0, maxR * 2.0
    };

    const auto tileIndices = canvas::SpatialCuller::getIntersectingTiles(
        bounds, tileGrid.getWidth(), tileGrid.getHeight()
    );

    // ─── 1. CIRCLE-AABB CULLING ───
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
        if (dX * dX + dY * dY > maxRSq) continue;

        canvas::Tile* tile = tileGrid.getOrCreateTile(idx.x, idx.y);
        if (tile) validTiles.push_back(tile);
    }
    if (validTiles.empty()) return;

    // ─── 2. PRÉ-CÁLCULOS ───
    const bool isCircular = (aspect >= 0.999) && (std::abs(dab.angle) < 0.001);
    const double radAngle = isCircular ? 0.0 : (-dab.angle * (3.14159265358979323846 / 180.0));
    const double cosA = isCircular ? 1.0 : std::cos(radAngle);
    const double sinA = isCircular ? 0.0 : std::sin(radAngle);
    const double invAspect = isCircular ? 1.0 : (1.0 / aspect);

    const double maxRadius = effectiveRadius + 1.0;
    const double maxRadiusSq = maxRadius * maxRadius;

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
                const double dist = std::sqrt(distSq);

                const double safeR = std::max(0.001, r);
                const double normalizedDist = dist / safeR;

                // 1. Hardness & Falloff com interpolação cúbica suave (elimina degraus visíveis)
                double shapeAlpha = 1.0;
                const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * safeR;
                if (dist > hardSpan) {
                    const double span = std::max(0.001, safeR - hardSpan);
                    const double t = std::clamp((safeR - dist) / span, 0.0, 1.0);
                    shapeAlpha = t * t * (3.0 - 2.0 * t); // Smoothstep cúbico
                }
                if (shapeAlpha <= 0.0) continue;

                // 2. Edge Darkening sutil apenas na margem externa capilar
                double edgeFactor = 1.0;
                if (edgeDark > 0.0 && normalizedDist > 0.8) {
                    const double ring = (normalizedDist - 0.8) / 0.2;
                    edgeFactor += std::sin(ring * 3.14159265358979323846) * edgeDark * 0.2;
                }

                // 3. Solvent Wetness modula a opacidade efetiva por passada
                const double effectiveOpacity = std::clamp(
                    dab.opacity * shapeAlpha * edgeFactor * (1.0 - wetness * 0.2),
                    0.0, 1.0
                );
                double curOpacity = effectiveOpacity;
                if (ctx.selectionMask && ctx.selectionMask->hasSelection()) {
                    const int gx = tilePixelX + px;
                    const int gy = tilePixelY + py;
                    const uint8_t sVal = ctx.selectionMask->getValue(gx, gy);
                    if (sVal == 0) continue;
                    if (sVal < 255) {
                        curOpacity *= (static_cast<double>(sVal) / 255.0);
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
                    curOpacity *= baseA;
                }

                if (curOpacity <= 0.0) continue;

                // 4. Blending Autêntico de Marcador (Veladura translúcida contínua sem colapso de cor)
                const utils::ColorRGBA dst = buffer.getPixel(px, py);

                const double srcR = static_cast<double>(dab.color.r) / 255.0;
                const double srcG = static_cast<double>(dab.color.g) / 255.0;
                const double srcB = static_cast<double>(dab.color.b) / 255.0;

                // Limite mínimo de saturação/luminância da tinta do marcador (impede que vermelho vire preto!)
                const double minR = srcR * 0.70;
                const double minG = srcG * 0.70;
                const double minB = srcB * 0.70;

                if (ctx.alphaLocked) {
                    if (dst.a == 0) continue;
                    const double dstR = static_cast<double>(dst.r) / 255.0;
                    const double dstG = static_cast<double>(dst.g) / 255.0;
                    const double dstB = static_cast<double>(dst.b) / 255.0;

                    const double absorb = curOpacity * 0.08;
                    const double outR = std::max(minR, dstR * (1.0 - absorb * (1.0 - srcR)));
                    const double outG = std::max(minG, dstG * (1.0 - absorb * (1.0 - srcG)));
                    const double outB = std::max(minB, dstB * (1.0 - absorb * (1.0 - srcB)));

                    buffer.setPixel(px, py, utils::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(outR * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outG * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outB * 255.0, 0.0, 255.0)),
                        dst.a
                    });
                    tileModified = true;
                    continue;
                }

                if (dst.a == 0) {
                    // Primeiro depósito: veladura translúcida da tinta do marcador
                    buffer.setPixel(px, py, utils::ColorRGBA{
                        dab.color.r,
                        dab.color.g,
                        dab.color.b,
                        static_cast<uint8_t>(std::clamp(curOpacity * 255.0, 0.0, 255.0))
                    });
                } else {
                    const double dstR = static_cast<double>(dst.r) / 255.0;
                    const double dstG = static_cast<double>(dst.g) / 255.0;
                    const double dstB = static_cast<double>(dst.b) / 255.0;
                    const double dstA = static_cast<double>(dst.a) / 255.0;

                    // Opacidade cumulativa suave do marcador
                    const double outA = std::clamp(dstA + curOpacity * (1.0 - dstA) * 0.5, 0.0, 1.0);

                    // Absorção luminosa da tinta de marcador (Beer-Lambert modificada: saturação rica sem colapso de cor)
                    const double absorb = curOpacity * 0.06;
                    const double outR = std::max(minR, dstR * (1.0 - absorb * (1.0 - srcR)));
                    const double outG = std::max(minG, dstG * (1.0 - absorb * (1.0 - srcG)));
                    const double outB = std::max(minB, dstB * (1.0 - absorb * (1.0 - srcB)));

                    buffer.setPixel(px, py, utils::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(outR * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outG * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outB * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outA * 255.0, 0.0, 255.0))
                    });
                }
                tileModified = true;
            }
        }
        if (tileModified) tile->setDirty(true);
    }
}

} // namespace aladyn::engine::engines
