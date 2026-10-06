#include "SelectionOrchestrator.hpp"
#include "LayerSampleSource.hpp"
#include "PixelFormatGuard.hpp"

namespace aladyn::engine::boundary::orchestrator {

bool SelectionOrchestrator::magicWandSelect(
    int seedX, int seedY, int tolerance, bool contiguous,
    int expandPx, bool antiAliasing, int mode, bool sampleAllLayers,
    int width, int height,
    const canvas::PixelBuffer& outputBuffer,
    const document::LayerStack& layerStack,
    selection::SelectionMask& selectionMask
) {
    if (seedX < 0 || seedX >= width || seedY < 0 || seedY >= height) {
        return false;
    }

    std::unique_ptr<canvas::PixelBuffer> activeLayerPixels;
    const canvas::PixelBuffer* srcBuf =
        LayerSampleSource::select(sampleAllLayers, outputBuffer, layerStack, activeLayerPixels);
    if (!srcBuf) return false;

    auto rawMask = selection::SelectionEngine::generateWandMask(
        *srcBuf, seedX, seedY, tolerance, contiguous, expandPx, antiAliasing
    );

    if (rawMask.empty()) {
        return false;
    }

    auto selMode = static_cast<selection::SelectionMode>(mode);
    selectionMask.combine(rawMask, selMode);
    return selectionMask.hasSelection();
}

bool SelectionOrchestrator::selectRect(
    int x, int y, int w, int h, int mode, int featherPx, int cornerRadiusPx,
    int width, int height,
    selection::SelectionMask& selectionMask
) {
    if (width <= 0 || height <= 0) return false;

    auto rawMask = selection::SelectionEngine::generateRectMask(
        width, height, x, y, w, h, featherPx, cornerRadiusPx
    );

    if (rawMask.empty()) return false;

    auto selMode = static_cast<selection::SelectionMode>(mode);
    selectionMask.combine(rawMask, selMode);
    return selectionMask.hasSelection();
}

bool SelectionOrchestrator::selectEllipse(
    int cx, int cy, int rx, int ry, int mode, bool antiAliasing, int featherPx,
    int width, int height,
    selection::SelectionMask& selectionMask
) {
    if (width <= 0 || height <= 0) return false;

    auto rawMask = selection::SelectionEngine::generateEllipseMask(
        width, height, cx, cy, rx, ry, antiAliasing, featherPx
    );

    if (rawMask.empty()) return false;

    auto selMode = static_cast<selection::SelectionMode>(mode);
    selectionMask.combine(rawMask, selMode);
    return selectionMask.hasSelection();
}

bool SelectionOrchestrator::selectPolygon(
    const std::vector<int>& flatPoints, int mode, bool antiAliasing, int featherPx,
    int width, int height,
    selection::SelectionMask& selectionMask
) {
    if (width <= 0 || height <= 0 || flatPoints.size() < 6) return false;

    std::vector<std::pair<int, int>> points;
    points.reserve(flatPoints.size() / 2);
    for (size_t i = 0; i + 1 < flatPoints.size(); i += 2) {
        points.emplace_back(flatPoints[i], flatPoints[i + 1]);
    }

    auto rawMask = selection::SelectionEngine::generatePolygonMask(
        width, height, points, antiAliasing, featherPx
    );

    if (rawMask.empty()) return false;

    auto selMode = static_cast<selection::SelectionMode>(mode);
    selectionMask.combine(rawMask, selMode);
    return selectionMask.hasSelection();
}

bool SelectionOrchestrator::deleteSelectionOnActiveLayer(
    document::LayerStack& layerStack,
    const selection::SelectionMask& selectionMask,
    history::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor
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
    const bool is16 = (grid.getFormat() == canvas::PixelFormat::RGBA16);
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

                    if (is16) {
                        auto cur = buf.getPixel16(px, py);
                        if (cur.a == 0) continue;
                        if (selVal == 255) {
                            cur.a = 0;
                        } else {
                            double factor = 1.0 - (selVal / 255.0);
                            cur.a = static_cast<uint16_t>(cur.a * factor);
                        }
                        buf.setPixel16(px, py, cur);
                        modified = true;
                    } else {
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
    const utils::ColorRGBA& fillColor,
    document::LayerStack& layerStack,
    const selection::SelectionMask& selectionMask,
    history::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor
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
    const bool is16 = (grid.getFormat() == canvas::PixelFormat::RGBA16);
    const utils::ColorRGBA16 fill16 = canvas::widen(fillColor);
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

                    if (is16) {
                        double srcA = (fill16.a / 65535.0) * (selVal / 255.0);
                        auto cur = buf.getPixel16(px, py);

                        if (activeLayer->isAlphaLocked()) {
                            if (cur.a > 0) {
                                cur.r = static_cast<uint16_t>(cur.r * (1.0 - srcA) + fill16.r * srcA);
                                cur.g = static_cast<uint16_t>(cur.g * (1.0 - srcA) + fill16.g * srcA);
                                cur.b = static_cast<uint16_t>(cur.b * (1.0 - srcA) + fill16.b * srcA);
                                buf.setPixel16(px, py, cur);
                                modified = true;
                            }
                        } else {
                            double dstA = cur.a / 65535.0;
                            double outA = srcA + dstA * (1.0 - srcA);
                            if (outA > 0.00001) {
                                cur.r = static_cast<uint16_t>((fill16.r * srcA + cur.r * dstA * (1.0 - srcA)) / outA);
                                cur.g = static_cast<uint16_t>((fill16.g * srcA + cur.g * dstA * (1.0 - srcA)) / outA);
                                cur.b = static_cast<uint16_t>((fill16.b * srcA + cur.b * dstA * (1.0 - srcA)) / outA);
                                cur.a = static_cast<uint16_t>(outA * 65535.0);
                                buf.setPixel16(px, py, cur);
                                modified = true;
                            }
                        }
                    } else {
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

} // namespace aladyn::engine::boundary::orchestrator
