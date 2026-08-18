#include "MarkerEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::engines {

void MarkerEngine::renderDab(
    const raster::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const canvas::PixelBuffer* /*compositeBuffer*/,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0 || dab.color.a == 0) return;

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

    const double wetness = std::clamp(profile.markerParams.solventWetness, 0.0, 1.0);
    const double edgeDark = std::clamp(profile.markerParams.edgeDarkening, 0.0, 1.0);

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
                const raster::ColorRGBA dst = buffer.getPixel(px, py);

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

                    buffer.setPixel(px, py, raster::ColorRGBA{
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
                    buffer.setPixel(px, py, raster::ColorRGBA{
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

                    // Opacidade do traço suave: mantém a transparência uniforme
                    const double outA = std::max(dstA, curOpacity);

                    // Escurecimento suave e progressivo de tinta sem manchas pretas
                    const double buildRate = 0.02 * curOpacity;
                    const double outR = std::max(minR, dstR - (1.0 - srcR) * buildRate);
                    const double outG = std::max(minG, dstG - (1.0 - srcG) * buildRate);
                    const double outB = std::max(minB, dstB - (1.0 - srcB) * buildRate);

                    buffer.setPixel(px, py, raster::ColorRGBA{
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
