#include "BufferPasteOrchestrator.hpp"
#include <algorithm>

namespace aladyn::engine::boundary::internal {

bool BufferPasteOrchestrator::paste(
    int x, int y, int width, int height,
    const uint8_t* buffer,
    int /*blendModeId*/, double opacity,
    int canvasWidth, int canvasHeight,
    document::LayerStack& layerStack,
    const raster::SelectionMask& selectionMask,
    canvas::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const raster::ColorRGBA& bgColor
) {
    if (!buffer || width <= 0 || height <= 0) return false;
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) {
        return false;
    }

    int dstX0 = std::max(0, x);
    int dstY0 = std::max(0, y);
    int dstX1 = std::min(canvasWidth, x + width);
    int dstY1 = std::min(canvasHeight, y + height);

    if (dstX0 >= dstX1 || dstY0 >= dstY1) {
        return false;
    }

    int activeIdx = layerStack.getActiveIndex();
    undoManager.beginStep("Paste Buffer");
    auto& grid = activeLayer->getTileGrid();

    int minTx = dstX0 / canvas::Tile::TILE_SIZE;
    int maxTx = (dstX1 - 1) / canvas::Tile::TILE_SIZE;
    int minTy = dstY0 / canvas::Tile::TILE_SIZE;
    int maxTy = (dstY1 - 1) / canvas::Tile::TILE_SIZE;

    double layerAlpha = std::clamp(opacity, 0.0, 1.0);

    for (int ty = minTy; ty <= maxTy; ++ty) {
        for (int tx = minTx; tx <= maxTx; ++tx) {
            canvas::Tile* tile = grid.getOrCreateTile(tx, ty);
            if (!tile) continue;

            const auto& bBuf = tile->getBuffer();
            undoManager.recordTileBefore(activeIdx, tx, ty, bBuf.getData(), bBuf.getSizeInBytes());

            auto& buf = tile->getBuffer();
            bool modified = false;
            int tilePixX = tile->getPixelX();
            int tilePixY = tile->getPixelY();

            for (int py = 0; py < canvas::Tile::TILE_SIZE; ++py) {
                int gy = tilePixY + py;
                if (gy < dstY0 || gy >= dstY1) continue;
                int bufY = gy - y;
                if (bufY < 0 || bufY >= height) continue;

                for (int px = 0; px < canvas::Tile::TILE_SIZE; ++px) {
                    int gx = tilePixX + px;
                    if (gx < dstX0 || gx >= dstX1) continue;
                    int bufX = gx - x;
                    if (bufX < 0 || bufX >= width) continue;

                    size_t bufOffset = static_cast<size_t>((bufY * width + bufX) * 4);
                    uint8_t srcR = buffer[bufOffset + 0];
                    uint8_t srcG = buffer[bufOffset + 1];
                    uint8_t srcB = buffer[bufOffset + 2];
                    uint8_t srcA_raw = buffer[bufOffset + 3];

                    if (srcA_raw == 0) continue;

                    double srcA = (srcA_raw / 255.0) * layerAlpha;
                    if (selectionMask.hasSelection()) {
                        uint8_t sVal = selectionMask.getValue(gx, gy);
                        if (sVal == 0) continue;
                        if (sVal < 255) {
                            srcA *= (static_cast<double>(sVal) / 255.0);
                        }
                    }

                    auto cur = buf.getPixel(px, py);

                    if (activeLayer->isAlphaLocked()) {
                        if (cur.a > 0) {
                            cur.r = static_cast<uint8_t>(cur.r * (1.0 - srcA) + srcR * srcA);
                            cur.g = static_cast<uint8_t>(cur.g * (1.0 - srcA) + srcG * srcA);
                            cur.b = static_cast<uint8_t>(cur.b * (1.0 - srcA) + srcB * srcA);
                            buf.setPixel(px, py, cur);
                            modified = true;
                        }
                    } else {
                        double dstA = cur.a / 255.0;
                        double outA = srcA + dstA * (1.0 - srcA);
                        if (outA > 0) {
                            cur.r = static_cast<uint8_t>((srcR * srcA + cur.r * dstA * (1.0 - srcA)) / outA);
                            cur.g = static_cast<uint8_t>((srcG * srcA + cur.g * dstA * (1.0 - srcA)) / outA);
                            cur.b = static_cast<uint8_t>((srcB * srcA + cur.b * dstA * (1.0 - srcA)) / outA);
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
    math::Rect2D dirtyRect{
        static_cast<double>(dstX0),
        static_cast<double>(dstY0),
        static_cast<double>(dstX1 - dstX0),
        static_cast<double>(dstY1 - dstY0)
    };
    compositor.compositeRegion(layerStack.getAllLayersForComposition(), dirtyRect, outputBuffer, bgColor);
    return true;
}

} // namespace aladyn::engine::boundary::internal
