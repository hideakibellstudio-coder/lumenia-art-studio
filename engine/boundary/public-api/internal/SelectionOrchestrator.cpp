#include "SelectionOrchestrator.hpp"

namespace aladyn::engine::boundary::internal {

bool SelectionOrchestrator::magicWandSelect(
    int seedX, int seedY, int tolerance, bool contiguous,
    int expandPx, bool antiAliasing, int mode, bool sampleAllLayers,
    int width, int height,
    const canvas::PixelBuffer& outputBuffer,
    const document::LayerStack& layerStack,
    raster::SelectionMask& selectionMask
) {
    if (seedX < 0 || seedX >= width || seedY < 0 || seedY >= height) {
        return false;
    }

    const canvas::PixelBuffer* srcBuf = nullptr;
    std::unique_ptr<canvas::PixelBuffer> tempBuf;

    if (sampleAllLayers) {
        srcBuf = &outputBuffer;
    } else {
        const document::Layer* activeLayer = layerStack.getActiveLayer();
        if (!activeLayer) return false;
        tempBuf = std::make_unique<canvas::PixelBuffer>(width, height, raster::ColorRGBA{0, 0, 0, 0});
        const auto& grid = activeLayer->getTileGrid();
        for (int ty = 0; ty < grid.getTilesCountY(); ++ty) {
            for (int tx = 0; tx < grid.getTilesCountX(); ++tx) {
                const auto* tile = const_cast<canvas::TileGrid&>(grid).getTile(tx, ty);
                if (tile) {
                    int px0 = tile->getPixelX();
                    int py0 = tile->getPixelY();
                    const auto& tBuf = tile->getBuffer();
                    for (int py = 0; py < canvas::Tile::TILE_SIZE && py0 + py < height; ++py) {
                        for (int px = 0; px < canvas::Tile::TILE_SIZE && px0 + px < width; ++px) {
                            tempBuf->setPixel(px0 + px, py0 + py, tBuf.getPixel(px, py));
                        }
                    }
                }
            }
        }
        srcBuf = tempBuf.get();
    }

    if (!srcBuf) return false;

    auto rawMask = raster::SelectionEngine::generateWandMask(
        *srcBuf, seedX, seedY, tolerance, contiguous, expandPx, antiAliasing
    );

    if (rawMask.empty()) {
        return false;
    }

    auto selMode = static_cast<raster::SelectionMode>(mode);
    selectionMask.combine(rawMask, selMode);
    return selectionMask.hasSelection();
}

bool SelectionOrchestrator::selectRect(
    int x, int y, int w, int h, int mode, int featherPx, int cornerRadiusPx,
    int width, int height,
    raster::SelectionMask& selectionMask
) {
    if (width <= 0 || height <= 0) return false;

    auto rawMask = raster::SelectionEngine::generateRectMask(
        width, height, x, y, w, h, featherPx, cornerRadiusPx
    );

    if (rawMask.empty()) return false;

    auto selMode = static_cast<raster::SelectionMode>(mode);
    selectionMask.combine(rawMask, selMode);
    return selectionMask.hasSelection();
}

bool SelectionOrchestrator::selectEllipse(
    int cx, int cy, int rx, int ry, int mode, bool antiAliasing, int featherPx,
    int width, int height,
    raster::SelectionMask& selectionMask
) {
    if (width <= 0 || height <= 0) return false;

    auto rawMask = raster::SelectionEngine::generateEllipseMask(
        width, height, cx, cy, rx, ry, antiAliasing, featherPx
    );

    if (rawMask.empty()) return false;

    auto selMode = static_cast<raster::SelectionMode>(mode);
    selectionMask.combine(rawMask, selMode);
    return selectionMask.hasSelection();
}

bool SelectionOrchestrator::selectPolygon(
    const std::vector<int>& flatPoints, int mode, bool antiAliasing, int featherPx,
    int width, int height,
    raster::SelectionMask& selectionMask
) {
    if (width <= 0 || height <= 0 || flatPoints.size() < 6) return false;

    std::vector<std::pair<int, int>> points;
    points.reserve(flatPoints.size() / 2);
    for (size_t i = 0; i + 1 < flatPoints.size(); i += 2) {
        points.emplace_back(flatPoints[i], flatPoints[i + 1]);
    }

    auto rawMask = raster::SelectionEngine::generatePolygonMask(
        width, height, points, antiAliasing, featherPx
    );

    if (rawMask.empty()) return false;

    auto selMode = static_cast<raster::SelectionMode>(mode);
    selectionMask.combine(rawMask, selMode);
    return selectionMask.hasSelection();
}

bool SelectionOrchestrator::deleteSelectionOnActiveLayer(
    document::LayerStack& layerStack,
    const raster::SelectionMask& selectionMask,
    canvas::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const raster::ColorRGBA& bgColor
) {
    if (!selectionMask.hasSelection()) return false;
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) {
        return false;
    }

    auto bounds = selectionMask.getBounds();
    if (bounds.width <= 0 || bounds.height <= 0) return false;

    int activeIdx = layerStack.getActiveIndex();
    undoManager.beginStep("Delete Selection");

    auto& grid = activeLayer->getTileGrid();
    int minTx = static_cast<int>(bounds.getLeft()) / canvas::Tile::TILE_SIZE;
    int maxTx = static_cast<int>(bounds.getRight()) / canvas::Tile::TILE_SIZE;
    int minTy = static_cast<int>(bounds.getTop()) / canvas::Tile::TILE_SIZE;
    int maxTy = static_cast<int>(bounds.getBottom()) / canvas::Tile::TILE_SIZE;

    for (int ty = minTy; ty <= maxTy; ++ty) {
        for (int tx = minTx; tx <= maxTx; ++tx) {
            canvas::Tile* tile = grid.getTile(tx, ty);
            if (!tile) continue;

            const auto& bBuf = tile->getBuffer();
            undoManager.recordTileBefore(activeIdx, tx, ty, bBuf.getData(), bBuf.getSizeInBytes());

            auto& buf = tile->getBuffer();
            int tilePixX = tile->getPixelX();
            int tilePixY = tile->getPixelY();
            bool modified = false;

            for (int py = 0; py < canvas::Tile::TILE_SIZE; ++py) {
                int gy = tilePixY + py;
                for (int px = 0; px < canvas::Tile::TILE_SIZE; ++px) {
                    int gx = tilePixX + px;
                    uint8_t selVal = selectionMask.getValue(gx, gy);
                    if (selVal == 0) continue;

                    auto cur = buf.getPixel(px, py);
                    if (cur.a == 0) continue;

                    if (selVal == 255) {
                        cur.a = 0;
                    } else {
                        double factor = 1.0 - (selVal / 255.0);
                        cur.a = static_cast<uint8_t>(cur.a * factor);
                    }
                    buf.setPixel(px, py, cur);
                    modified = true;
                }
            }

            if (modified) {
                tile->setDirty(true);
            }
        }
    }

    undoManager.commitStep(layerStack);
    compositor.compositeRegion(layerStack.getAllLayersForComposition(), bounds, outputBuffer, bgColor);
    return true;
}

bool SelectionOrchestrator::fillSelectionOnActiveLayer(
    const raster::ColorRGBA& fillColor,
    document::LayerStack& layerStack,
    const raster::SelectionMask& selectionMask,
    canvas::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const raster::ColorRGBA& bgColor
) {
    if (!selectionMask.hasSelection()) return false;
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) {
        return false;
    }

    auto bounds = selectionMask.getBounds();
    if (bounds.width <= 0 || bounds.height <= 0) return false;

    int activeIdx = layerStack.getActiveIndex();
    undoManager.beginStep("Fill Selection");

    auto& grid = activeLayer->getTileGrid();
    int minTx = static_cast<int>(bounds.getLeft()) / canvas::Tile::TILE_SIZE;
    int maxTx = static_cast<int>(bounds.getRight()) / canvas::Tile::TILE_SIZE;
    int minTy = static_cast<int>(bounds.getTop()) / canvas::Tile::TILE_SIZE;
    int maxTy = static_cast<int>(bounds.getBottom()) / canvas::Tile::TILE_SIZE;

    for (int ty = minTy; ty <= maxTy; ++ty) {
        for (int tx = minTx; tx <= maxTx; ++tx) {
            canvas::Tile* tile = grid.getOrCreateTile(tx, ty);
            if (!tile) continue;

            const auto& bBuf = tile->getBuffer();
            undoManager.recordTileBefore(activeIdx, tx, ty, bBuf.getData(), bBuf.getSizeInBytes());

            auto& buf = tile->getBuffer();
            int tilePixX = tile->getPixelX();
            int tilePixY = tile->getPixelY();
            bool modified = false;

            for (int py = 0; py < canvas::Tile::TILE_SIZE; ++py) {
                int gy = tilePixY + py;
                for (int px = 0; px < canvas::Tile::TILE_SIZE; ++px) {
                    int gx = tilePixX + px;
                    uint8_t selVal = selectionMask.getValue(gx, gy);
                    if (selVal == 0) continue;

                    double srcA = (fillColor.a / 255.0) * (selVal / 255.0);
                    auto cur = buf.getPixel(px, py);

                    if (activeLayer->isAlphaLocked()) {
                        if (cur.a > 0) {
                            cur.r = static_cast<uint8_t>(cur.r * (1.0 - srcA) + fillColor.r * srcA);
                            cur.g = static_cast<uint8_t>(cur.g * (1.0 - srcA) + fillColor.g * srcA);
                            cur.b = static_cast<uint8_t>(cur.b * (1.0 - srcA) + fillColor.b * srcA);
                            buf.setPixel(px, py, cur);
                            modified = true;
                        }
                    } else {
                        double dstA = cur.a / 255.0;
                        double outA = srcA + dstA * (1.0 - srcA);
                        if (outA > 0) {
                            cur.r = static_cast<uint8_t>((fillColor.r * srcA + cur.r * dstA * (1.0 - srcA)) / outA);
                            cur.g = static_cast<uint8_t>((fillColor.g * srcA + cur.g * dstA * (1.0 - srcA)) / outA);
                            cur.b = static_cast<uint8_t>((fillColor.b * srcA + cur.b * dstA * (1.0 - srcA)) / outA);
                            cur.a = static_cast<uint8_t>(outA * 255.0);
                            buf.setPixel(px, py, cur);
                            modified = true;
                        }
                    }
                }
            }

            if (modified) {
                tile->setDirty(true);
            }
        }
    }

    undoManager.commitStep(layerStack);
    compositor.compositeRegion(layerStack.getAllLayersForComposition(), bounds, outputBuffer, bgColor);
    return true;
}

} // namespace aladyn::engine::boundary::internal
