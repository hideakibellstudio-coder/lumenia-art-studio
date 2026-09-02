#include "Compositor.hpp"
#include "FilterLayer.hpp"
#include "blending/BlendEquations.hpp"
#include "blending/FilterApplier.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::document {

Compositor::Compositor(int width, int height)
    : m_width(width), m_height(height) {}

raster::ColorRGBA Compositor::blendPixel(
    raster::ColorRGBA src,
    double layerOpacity,
    raster::ColorRGBA dst,
    LayerBlendMode mode
) {
    return blending::blendPixel(src, layerOpacity, dst, mode);
}

void Compositor::applyFilterToBuffer(
    const FilterLayer& filter,
    canvas::PixelBuffer& buffer,
    int minX, int maxX, int minY, int maxY
) {
    blending::FilterApplier::apply(filter, buffer, minX, maxX, minY, maxY);
}

void Compositor::composite(
    const std::vector<const Layer*>& layers,
    canvas::PixelBuffer& outputBuffer,
    const raster::ColorRGBA& bgColor
) {
    compositeRegion(
        layers,
        math::Rect2D{0, 0, static_cast<double>(m_width), static_cast<double>(m_height)},
        outputBuffer,
        bgColor
    );
}

void Compositor::composite(
    const std::vector<std::unique_ptr<Layer>>& layers,
    canvas::PixelBuffer& outputBuffer,
    const raster::ColorRGBA& bgColor
) {
    std::vector<const Layer*> rawPtrs;
    rawPtrs.reserve(layers.size());
    for (const auto& l : layers) {
        if (l) rawPtrs.push_back(l.get());
    }
    composite(rawPtrs, outputBuffer, bgColor);
}

void Compositor::compositeRegion(
    const std::vector<const Layer*>& layers,
    const math::Rect2D& region,
    canvas::PixelBuffer& outputBuffer,
    const raster::ColorRGBA& bgColor
) {
    if (layers.empty()) return;

    bool hasBackground = false;
    for (const Layer* l : layers) {
        if (l && l->isBackground() && l->isVisible()) {
            hasBackground = true;
            break;
        }
    }

    const raster::ColorRGBA bgFill = hasBackground ? bgColor : raster::ColorRGBA{0, 0, 0, 0};

    const int minX = std::max(0, static_cast<int>(std::floor(region.getLeft())) - 2);
    const int maxX = std::min(m_width - 1, static_cast<int>(std::ceil(region.getRight())) + 2);
    const int minY = std::max(0, static_cast<int>(std::floor(region.getTop())) - 2);
    const int maxY = std::min(m_height - 1, static_cast<int>(std::ceil(region.getBottom())) + 2);

    if (minX > maxX || minY > maxY) return;

    const int startTileX = minX / canvas::Tile::TILE_SIZE;
    const int endTileX   = maxX / canvas::Tile::TILE_SIZE;
    const int startTileY = minY / canvas::Tile::TILE_SIZE;
    const int endTileY   = maxY / canvas::Tile::TILE_SIZE;

    // Reseta a área apenas na bounding box afetada
    for (int y = minY; y <= maxY; ++y) {
        for (int x = minX; x <= maxX; ++x) {
            outputBuffer.setPixel(x, y, bgFill);
        }
    }

    for (const Layer* layerPtr : layers) {
        if (!layerPtr || !layerPtr->isVisible() || layerPtr->getEffectiveOpacity() <= 0.0) {
            continue;
        }

        if (layerPtr->isFilter()) {
            const FilterLayer* filterLayer = dynamic_cast<const FilterLayer*>(layerPtr);
            if (filterLayer) {
                applyFilterToBuffer(*filterLayer, outputBuffer, minX, maxX, minY, maxY);
            }
            continue;
        }

        const Layer& layer = *layerPtr;
        const double layerOpacity = layer.getEffectiveOpacity();
        const LayerBlendMode blendMode = layer.getBlendMode();
        const canvas::TileGrid& grid = layer.getTileGrid();

        // Clipping mask
        const Layer* clipBaseLayer = nullptr;
        if (layer.isClippingMask()) {
            auto it = std::find(layers.begin(), layers.end(), layerPtr);
            if (it != layers.begin()) {
                for (auto prevIt = it - 1; ; --prevIt) {
                    if (*prevIt && !(*prevIt)->isBackground() && !(*prevIt)->isClippingMask() && !(*prevIt)->isFilter() && !(*prevIt)->isGroup() && (*prevIt)->isVisible()) {
                        clipBaseLayer = *prevIt;
                        break;
                    }
                    if (prevIt == layers.begin()) break;
                }
            }
        }

        const int maxTilesX = grid.getTilesCountX();
        const int maxTilesY = grid.getTilesCountY();
        const int clampStartTx = std::clamp(startTileX, 0, maxTilesX - 1);
        const int clampEndTx   = std::clamp(endTileX, 0, maxTilesX - 1);
        const int clampStartTy = std::clamp(startTileY, 0, maxTilesY - 1);
        const int clampEndTy   = std::clamp(endTileY, 0, maxTilesY - 1);

        for (int ty = clampStartTy; ty <= clampEndTy; ++ty) {
            for (int tx = clampStartTx; tx <= clampEndTx; ++tx) {
                const canvas::Tile* tile = const_cast<canvas::TileGrid&>(grid).getTile(tx, ty);
                if (!tile) continue;

                const canvas::PixelBuffer& tileBuf = tile->getBuffer();
                const int tilePixelX = tile->getPixelX();
                const int tilePixelY = tile->getPixelY();

                const int tileMinX = std::max(minX, tilePixelX);
                const int tileMaxX = std::min(maxX, tilePixelX + canvas::Tile::TILE_SIZE - 1);
                const int tileMinY = std::max(minY, tilePixelY);
                const int tileMaxY = std::min(maxY, tilePixelY + canvas::Tile::TILE_SIZE - 1);

                for (int globalY = tileMinY; globalY <= tileMaxY; ++globalY) {
                    const int localY = globalY - tilePixelY;

                    for (int globalX = tileMinX; globalX <= tileMaxX; ++globalX) {
                        const int localX = globalX - tilePixelX;

                        const raster::ColorRGBA src = tileBuf.getPixel(localX, localY);
                        if (src.a == 0) continue;

                        double curOpacity = layerOpacity;
                        if (clipBaseLayer) {
                            const int bTx = globalX / canvas::Tile::TILE_SIZE;
                            const int bTy = globalY / canvas::Tile::TILE_SIZE;
                            const int bPx = globalX % canvas::Tile::TILE_SIZE;
                            const int bPy = globalY % canvas::Tile::TILE_SIZE;
                            const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                            if (!bTile) continue;
                            const double baseA = (static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0) * clipBaseLayer->getEffectiveOpacity();
                            if (baseA <= 0.0) continue;
                            curOpacity *= baseA;
                        }

                        const raster::ColorRGBA dst = outputBuffer.getPixel(globalX, globalY);
                        outputBuffer.setPixel(globalX, globalY, blending::blendPixel(src, curOpacity, dst, blendMode));
                    }
                }
            }
        }
    }
}

void Compositor::compositeRegion(
    const std::vector<std::unique_ptr<Layer>>& layers,
    const math::Rect2D& region,
    canvas::PixelBuffer& outputBuffer,
    const raster::ColorRGBA& bgColor
) {
    std::vector<const Layer*> rawPtrs;
    rawPtrs.reserve(layers.size());
    for (const auto& l : layers) {
        if (l) rawPtrs.push_back(l.get());
    }
    compositeRegion(rawPtrs, region, outputBuffer, bgColor);
}

void Compositor::compositeRegionWithScratch(
    const std::vector<const Layer*>& layers,
    const math::Rect2D& region,
    canvas::PixelBuffer& outputBuffer,
    const raster::ColorRGBA& bgColor,
    const canvas::TileGrid& scratchGrid,
    const Layer* activeLayerTarget,
    LayerBlendMode scratchBlendMode,
    double scratchOpacity
) {
    if (layers.empty()) return;

    bool hasBackground = false;
    for (const Layer* l : layers) {
        if (l && l->isBackground() && l->isVisible()) { hasBackground = true; break; }
    }

    const raster::ColorRGBA bgFill = hasBackground ? bgColor : raster::ColorRGBA{0, 0, 0, 0};

    const int minX = std::max(0, static_cast<int>(std::floor(region.getLeft())) - 2);
    const int maxX = std::min(m_width - 1, static_cast<int>(std::ceil(region.getRight())) + 2);
    const int minY = std::max(0, static_cast<int>(std::floor(region.getTop())) - 2);
    const int maxY = std::min(m_height - 1, static_cast<int>(std::ceil(region.getBottom())) + 2);
    if (minX > maxX || minY > maxY) return;

    for (int y = minY; y <= maxY; ++y)
        for (int x = minX; x <= maxX; ++x)
            outputBuffer.setPixel(x, y, bgFill);

    const int startTileX = minX / canvas::Tile::TILE_SIZE;
    const int endTileX   = maxX / canvas::Tile::TILE_SIZE;
    const int startTileY = minY / canvas::Tile::TILE_SIZE;
    const int endTileY   = maxY / canvas::Tile::TILE_SIZE;

    auto composeTileGrid = [&](const canvas::TileGrid& grid, double opacity, LayerBlendMode mode, const Layer* clipBase) {
        const int maxTilesX = grid.getTilesCountX();
        const int maxTilesY = grid.getTilesCountY();
        const int cSTx = std::clamp(startTileX, 0, maxTilesX - 1);
        const int cETx = std::clamp(endTileX,   0, maxTilesX - 1);
        const int cSTy = std::clamp(startTileY, 0, maxTilesY - 1);
        const int cETy = std::clamp(endTileY,   0, maxTilesY - 1);

        for (int ty = cSTy; ty <= cETy; ++ty) {
            for (int tx = cSTx; tx <= cETx; ++tx) {
                const canvas::Tile* tile = const_cast<canvas::TileGrid&>(grid).getTile(tx, ty);
                if (!tile) continue;

                const canvas::PixelBuffer& tileBuf = tile->getBuffer();
                const int tilePixelX = tile->getPixelX();
                const int tilePixelY = tile->getPixelY();

                const int tileMinX = std::max(minX, tilePixelX);
                const int tileMaxX = std::min(maxX, tilePixelX + canvas::Tile::TILE_SIZE - 1);
                const int tileMinY = std::max(minY, tilePixelY);
                const int tileMaxY = std::min(maxY, tilePixelY + canvas::Tile::TILE_SIZE - 1);

                for (int globalY = tileMinY; globalY <= tileMaxY; ++globalY) {
                    const int localY = globalY - tilePixelY;
                    for (int globalX = tileMinX; globalX <= tileMaxX; ++globalX) {
                        const int localX = globalX - tilePixelX;
                        const raster::ColorRGBA src = tileBuf.getPixel(localX, localY);
                        if (src.a == 0) continue;

                        double curOpacity = opacity;
                        if (clipBase) {
                            const int bTx = globalX / canvas::Tile::TILE_SIZE;
                            const int bTy = globalY / canvas::Tile::TILE_SIZE;
                            const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(clipBase->getTileGrid()).getTile(bTx, bTy);
                            if (!bTile) continue;
                            const double baseA = (static_cast<double>(bTile->getBuffer().getPixel(
                                globalX % canvas::Tile::TILE_SIZE,
                                globalY % canvas::Tile::TILE_SIZE).a) / 255.0) * clipBase->getEffectiveOpacity();
                            if (baseA <= 0.0) continue;
                            curOpacity *= baseA;
                        }

                        const raster::ColorRGBA dst = outputBuffer.getPixel(globalX, globalY);
                        outputBuffer.setPixel(globalX, globalY, blending::blendPixel(src, curOpacity, dst, mode));
                    }
                }
            }
        }
    };

    for (const Layer* layerPtr : layers) {
        if (!layerPtr || !layerPtr->isVisible() || layerPtr->getEffectiveOpacity() <= 0.0) {
            continue;
        }

        if (layerPtr->isFilter()) {
            const FilterLayer* filterLayer = dynamic_cast<const FilterLayer*>(layerPtr);
            if (filterLayer) applyFilterToBuffer(*filterLayer, outputBuffer, minX, maxX, minY, maxY);
            continue;
        }

        const Layer& layer = *layerPtr;
        const double layerOpacity = layer.getEffectiveOpacity();
        const LayerBlendMode blendMode = layer.getBlendMode();

        const Layer* clipBaseLayer = nullptr;
        if (layer.isClippingMask()) {
            auto it = std::find(layers.begin(), layers.end(), layerPtr);
            if (it != layers.begin()) {
                for (auto prevIt = it - 1; ; --prevIt) {
                    if (*prevIt && !(*prevIt)->isBackground() && !(*prevIt)->isClippingMask() && !(*prevIt)->isFilter() && !(*prevIt)->isGroup() && (*prevIt)->isVisible()) {
                        clipBaseLayer = *prevIt;
                        break;
                    }
                    if (prevIt == layers.begin()) break;
                }
            }
        }

        composeTileGrid(layer.getTileGrid(), layerOpacity, blendMode, clipBaseLayer);

        if (layerPtr == activeLayerTarget && scratchOpacity > 0.0) {
            composeTileGrid(scratchGrid, scratchOpacity, scratchBlendMode, clipBaseLayer);
        }
    }
}

} // namespace aladyn::engine::document
