#ifndef ALADYN_ENGINE_TRANSFORM_INVERSE_MAPPED_COMPOSITE_HPP
#define ALADYN_ENGINE_TRANSFORM_INVERSE_MAPPED_COMPOSITE_HPP

// Núcleo comum dos commits de transformação (livre e distorcer): para cada
// pixel de destino, a função `inverso` diz de onde ele vem na imagem-fonte; o
// resto -- registro dos tiles no desfazer, amostragem e composição "source
// over" -- é o mesmo para qualquer mapeamento. Extraído de
// TransformEngine::commitTransform em 2026-09-23 sem mudar a aritmética.

#include "TransformSamplers.hpp"
#include "../../canvas/TileGrid.hpp"
#include "../../history/TileUndoManager.hpp"
#include <algorithm>

namespace aladyn::engine::raster::transform {

namespace {
inline int divFloor(int a, int b) noexcept {
    int res = a / b;
    int rem = a % b;
    if (rem != 0 && ((a < 0) ^ (b < 0))) {
        --res;
    }
    return res;
}
} // namespace

/// inverso(destX, destY, u, v) -> bool: coordenada (u, v) no buffer-fonte;
/// false quando o pixel de destino não recebe nada.
template <class InverseFn>
void compositeInverseMapped(
    canvas::TileGrid& grid,
    const canvas::PixelBuffer& source,
    int minDx, int minDy, int maxDx, int maxDy,
    int interpMode,
    history::TileUndoManager& undoManager,
    int activeLayerIndex,
    InverseFn&& inverse
) {
    const int startTileX = divFloor(minDx, canvas::Tile::TILE_SIZE);
    const int endTileX   = divFloor(maxDx, canvas::Tile::TILE_SIZE);
    const int startTileY = divFloor(minDy, canvas::Tile::TILE_SIZE);
    const int endTileY   = divFloor(maxDy, canvas::Tile::TILE_SIZE);

    const uint8_t* emptyData = canvas::zeroTileData();
    const size_t emptyBytes = canvas::Tile::bytesFor(grid.getFormat());

    for (int ty = startTileY; ty <= endTileY; ++ty) {
        for (int tx = startTileX; tx <= endTileX; ++tx) {
            canvas::Tile* tile = grid.getTile(tx, ty);
            if (tile) {
                const auto& buf = tile->getBuffer();
                undoManager.recordTileBefore(activeLayerIndex, tx, ty, buf.getData(), buf.getSizeInBytes());
            } else {
                undoManager.recordTileBefore(activeLayerIndex, tx, ty, emptyData, emptyBytes);
            }
        }
    }

    const bool is16 = (grid.getFormat() == canvas::PixelFormat::RGBA16);

    // Mapeamento inverso para cada pixel de destino
    for (int ty = startTileY; ty <= endTileY; ++ty) {
        for (int tx = startTileX; tx <= endTileX; ++tx) {
            canvas::Tile* tile = grid.getOrCreateTile(tx, ty);
            auto& buf = tile->getBuffer();
            int tpx = tile->getPixelX();
            int tpy = tile->getPixelY();

            for (int ly = 0; ly < canvas::Tile::TILE_SIZE; ++ly) {
                int destY = tpy + ly;
                if (destY < minDy || destY > maxDy) continue;

                for (int lx = 0; lx < canvas::Tile::TILE_SIZE; ++lx) {
                    int destX = tpx + lx;
                    if (destX < minDx || destX > maxDx) continue;

                    double u = 0.0, v = 0.0;
                    if (inverse(destX, destY, u, v)) {
                        if (is16) {
                            utils::ColorRGBA16 sampled;
                            if (interpMode == static_cast<int>(InterpolationMode::Nearest)) {
                                sampled = sampleNearest<utils::ColorRGBA16>(source, u, v);
                            } else if (interpMode == static_cast<int>(InterpolationMode::Bilinear)) {
                                sampled = sampleBilinear<utils::ColorRGBA16>(source, u, v);
                            } else {
                                sampled = sampleBicubic<utils::ColorRGBA16>(source, u, v);
                            }

                            if (sampled.a > 0) {
                                auto cur = buf.getPixel16(lx, ly);
                                double srcA = sampled.a / 65535.0;
                                double dstA = cur.a / 65535.0;
                                double outA = srcA + dstA * (1.0 - srcA);

                                if (outA > 0.00001) {
                                    cur.r = static_cast<uint16_t>(std::clamp((sampled.r * srcA + cur.r * dstA * (1.0 - srcA)) / outA, 0.0, 65535.0));
                                    cur.g = static_cast<uint16_t>(std::clamp((sampled.g * srcA + cur.g * dstA * (1.0 - srcA)) / outA, 0.0, 65535.0));
                                    cur.b = static_cast<uint16_t>(std::clamp((sampled.b * srcA + cur.b * dstA * (1.0 - srcA)) / outA, 0.0, 65535.0));
                                    cur.a = static_cast<uint16_t>(std::clamp(outA * 65535.0, 0.0, 65535.0));
                                    buf.setPixel16(lx, ly, cur);
                                    tile->setDirty(true);
                                }
                            }
                        } else {
                            utils::ColorRGBA sampled;
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
}

} // namespace aladyn::engine::raster::transform

#endif // ALADYN_ENGINE_TRANSFORM_INVERSE_MAPPED_COMPOSITE_HPP
