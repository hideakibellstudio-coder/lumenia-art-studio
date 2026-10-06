#include "BufferPasteOrchestrator.hpp"
#include "PixelFormatGuard.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::boundary::orchestrator {

namespace {
// Round to the nearest byte. A plain cast truncates, and `14 * 0.89 / 0.89`
// is 13.999... in double: blue 14 under alpha 227 came back as 13, so opening a
// saved document did not reproduce the pixels that were saved.
uint8_t toByte(double value) {
    return static_cast<uint8_t>(std::clamp(std::lround(value), 0L, 255L));
}
uint16_t toWord(double value) {
    return static_cast<uint16_t>(std::clamp(std::lround(value), 0L, 65535L));
}

inline int divFloor(int a, int b) noexcept {
    int res = a / b;
    int rem = a % b;
    if (rem != 0 && ((a < 0) ^ (b < 0))) {
        --res;
    }
    return res;
}
} // namespace

bool BufferPasteOrchestrator::paste(
    int x, int y, int width, int height,
    const uint8_t* buffer,
    int /*blendModeId*/, double opacity,
    int canvasWidth, int canvasHeight,
    document::LayerStack& layerStack,
    const selection::SelectionMask& selectionMask,
    history::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor
) {
    if (!buffer || width <= 0 || height <= 0) return false;
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) {
        return false;
    }

    int dstX0 = x;
    int dstY0 = y;
    int dstX1 = x + width;
    int dstY1 = y + height;

    constexpr int kMinCoord = -32768 * canvas::Tile::TILE_SIZE;
    constexpr int kMaxCoord =  32767 * canvas::Tile::TILE_SIZE;
    if (dstX1 < kMinCoord || dstX0 > kMaxCoord || dstY1 < kMinCoord || dstY0 > kMaxCoord) {
        return false;
    }

    int activeIdx = layerStack.getActiveIndex();
    undoManager.beginStep("Paste Buffer");
    auto& grid = activeLayer->getTargetGrid();
    const bool is16 = (grid.getFormat() == canvas::PixelFormat::RGBA16);

    int minTx = divFloor(dstX0, canvas::Tile::TILE_SIZE);
    int maxTx = divFloor(dstX1 - 1, canvas::Tile::TILE_SIZE);
    int minTy = divFloor(dstY0, canvas::Tile::TILE_SIZE);
    int maxTy = divFloor(dstY1 - 1, canvas::Tile::TILE_SIZE);

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

                    if (is16) {
                        uint16_t srcR16 = canvas::widenChannel(srcR);
                        uint16_t srcG16 = canvas::widenChannel(srcG);
                        uint16_t srcB16 = canvas::widenChannel(srcB);
                        auto cur = buf.getPixel16(px, py);

                        if (activeLayer->isAlphaLocked()) {
                            if (cur.a > 0) {
                                cur.r = toWord(cur.r * (1.0 - srcA) + srcR16 * srcA);
                                cur.g = toWord(cur.g * (1.0 - srcA) + srcG16 * srcA);
                                cur.b = toWord(cur.b * (1.0 - srcA) + srcB16 * srcA);
                                buf.setPixel16(px, py, cur);
                                modified = true;
                            }
                        } else {
                            double dstA = cur.a / 65535.0;
                            double outA = srcA + dstA * (1.0 - srcA);
                            if (outA > 0) {
                                if (cur.a == 0) {
                                    cur.r = srcR16;
                                    cur.g = srcG16;
                                    cur.b = srcB16;
                                } else {
                                    cur.r = toWord((srcR16 * srcA + cur.r * dstA * (1.0 - srcA)) / outA);
                                    cur.g = toWord((srcG16 * srcA + cur.g * dstA * (1.0 - srcA)) / outA);
                                    cur.b = toWord((srcB16 * srcA + cur.b * dstA * (1.0 - srcA)) / outA);
                                }
                                cur.a = toWord(outA * 65535.0);
                                buf.setPixel16(px, py, cur);
                                modified = true;
                            }
                        }
                    } else {
                        auto cur = buf.getPixel(px, py);

                        if (activeLayer->isAlphaLocked()) {
                            if (cur.a > 0) {
                                cur.r = toByte(cur.r * (1.0 - srcA) + srcR * srcA);
                                cur.g = toByte(cur.g * (1.0 - srcA) + srcG * srcA);
                                cur.b = toByte(cur.b * (1.0 - srcA) + srcB * srcA);
                                buf.setPixel(px, py, cur);
                                modified = true;
                            }
                        } else {
                            double dstA = cur.a / 255.0;
                            double outA = srcA + dstA * (1.0 - srcA);
                            if (outA > 0) {
                                if (cur.a == 0) {
                                    cur.r = srcR;
                                    cur.g = srcG;
                                    cur.b = srcB;
                                } else {
                                    cur.r = toByte((srcR * srcA + cur.r * dstA * (1.0 - srcA)) / outA);
                                    cur.g = toByte((srcG * srcA + cur.g * dstA * (1.0 - srcA)) / outA);
                                    cur.b = toByte((srcB * srcA + cur.b * dstA * (1.0 - srcA)) / outA);
                                }
                                cur.a = toByte(outA * 255.0);
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
    utils::Rect2D dirtyRect{
        static_cast<double>(dstX0),
        static_cast<double>(dstY0),
        static_cast<double>(dstX1 - dstX0),
        static_cast<double>(dstY1 - dstY0)
    };
    compositor.compositeRegion(layerStack.getAllLayersForComposition(), dirtyRect, outputBuffer, bgColor);
    return true;
}

} // namespace aladyn::engine::boundary::orchestrator
