#ifndef ALADYN_ENGINE_TRANSFORM_INVERSE_MAPPED_COMPOSITE_HPP
#define ALADYN_ENGINE_TRANSFORM_INVERSE_MAPPED_COMPOSITE_HPP

// Núcleo comum dos commits de transformação (livre e distorcer): para cada
// pixel de destino, a função `inverso` diz de onde ele vem na imagem-fonte; o
// resto -- registro dos tiles no desfazer, amostragem e composição "source
// over" -- é o mesmo para qualquer mapeamento. Extraído de
// TransformEngine::commitTransform em 2026-09-23 sem mudar a aritmética.

#include "TransformSamplers.hpp"
#include "../TransformEngine.hpp"
#include "../../canvas/TileGrid.hpp"
#include "../../canvas/TileUndoManager.hpp"
#include <algorithm>

namespace aladyn::engine::raster::transform {

/// inverso(destX, destY, u, v) -> bool: coordenada (u, v) no buffer-fonte;
/// false quando o pixel de destino não recebe nada.
template <class Inverso>
void compositeInverseMapped(
    canvas::TileGrid& grid,
    const canvas::PixelBuffer& source,
    int minDx, int minDy, int maxDx, int maxDy,
    int interpMode,
    canvas::TileUndoManager& undoManager,
    int activeLayerIndex,
    Inverso&& inverso
) {
    const int startTileX = minDx / canvas::Tile::TILE_SIZE;
    const int endTileX   = maxDx / canvas::Tile::TILE_SIZE;
    const int startTileY = minDy / canvas::Tile::TILE_SIZE;
    const int endTileY   = maxDy / canvas::Tile::TILE_SIZE;

    for (int ty = startTileY; ty <= endTileY; ++ty) {
        for (int tx = startTileX; tx <= endTileX; ++tx) {
            canvas::Tile* tile = grid.getTile(tx, ty);
            if (tile) {
                const auto& buf = tile->getBuffer();
                undoManager.recordTileBefore(activeLayerIndex, tx, ty, buf.getData(), buf.getSizeInBytes());
            } else {
                canvas::PixelBuffer emptyBuf(canvas::Tile::TILE_SIZE, canvas::Tile::TILE_SIZE, {0, 0, 0, 0});
                undoManager.recordTileBefore(activeLayerIndex, tx, ty, emptyBuf.getData(), emptyBuf.getSizeInBytes());
            }
        }
    }

    // Mapeamento inverso para cada pixel de destino
    for (int ty = startTileY; ty <= endTileY; ++ty) {
        for (int tx = startTileX; tx <= endTileX; ++tx) {
            canvas::Tile* tile = grid.getOrCreateTile(tx, ty);
            auto& buf = tile->getBuffer();
            int tpx = tile->getPixelX();
            int tpy = tile->getPixelY();

            for (int ly = 0; ly < canvas::Tile::TILE_SIZE; ++ly) {
                int destY = tpy + ly;
                if (destY > maxDy) break;

                for (int lx = 0; lx < canvas::Tile::TILE_SIZE; ++lx) {
                    int destX = tpx + lx;
                    if (destX > maxDx) break;

                    double u = 0.0, v = 0.0;
                    if (inverso(destX, destY, u, v)) {
                        ColorRGBA sampled;
                        if (interpMode == static_cast<int>(InterpolationMode::Nearest)) {
                            sampled = sampleNearest(source, u, v);
                        } else if (interpMode == static_cast<int>(InterpolationMode::Bilinear)) {
                            sampled = sampleBilinear(source, u, v);
                        } else {
                            sampled = sampleBicubic(source, u, v);
                        }

                        if (sampled.a > 0) {
                            auto cur = buf.getPixel(lx, ly);
                            double srcA = sampled.a / 255.0;
                            double dstA = cur.a / 255.0;
                            double outA = srcA + dstA * (1.0 - srcA);

                            if (outA > 0.001) {
                                cur.r = static_cast<uint8_t>(std::clamp((sampled.r * srcA + cur.r * dstA * (1.0 - srcA)) / outA, 0.0, 255.0));
                                cur.g = static_cast<uint8_t>(std::clamp((sampled.g * srcA + cur.g * dstA * (1.0 - srcA)) / outA, 0.0, 255.0));
                                cur.b = static_cast<uint8_t>(std::clamp((sampled.b * srcA + cur.b * dstA * (1.0 - srcA)) / outA, 0.0, 255.0));
                                cur.a = static_cast<uint8_t>(std::clamp(outA * 255.0, 0.0, 255.0));
                                buf.setPixel(lx, ly, cur);
                                tile->setDirty(true);
                            }
                        }
                    }
                }
            }
        }
    }
}

} // namespace aladyn::engine::raster::transform

#endif // ALADYN_ENGINE_TRANSFORM_INVERSE_MAPPED_COMPOSITE_HPP
