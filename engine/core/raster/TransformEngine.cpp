#include "TransformEngine.hpp"
#include "transform/TransformSamplers.hpp"
#include <cmath>
#include <algorithm>
#include <cstring>

namespace aladyn::engine::raster {

static constexpr double PI = 3.14159265358979323846;

// ─── AMOSTAGEM & INTERPOLAÇÃO ───────────────────────────────────────────────

ColorRGBA TransformEngine::sampleNearest(const canvas::PixelBuffer& src, double u, double v) noexcept {
    return transform::sampleNearest(src, u, v);
}

ColorRGBA TransformEngine::sampleBilinear(const canvas::PixelBuffer& src, double u, double v) noexcept {
    return transform::sampleBilinear(src, u, v);
}

ColorRGBA TransformEngine::sampleBicubic(const canvas::PixelBuffer& src, double u, double v) noexcept {
    return transform::sampleBicubic(src, u, v);
}

// ─── EXECUÇÃO DO TRANSFORM ENGINE ──────────────────────────────────────────

bool TransformEngine::beginTransform(
    document::Layer* activeLayer,
    const SelectionMask* selectionMask,
    int canvasWidth,
    int canvasHeight,
    canvas::TileUndoManager& undoManager,
    int activeLayerIndex
) {
    if (!activeLayer || activeLayer->isFilter() || activeLayer->isGroup()) return false;
    if (!activeLayer->isVisible() || activeLayer->isLocked()) return false;

    reset();

    int minX = canvasWidth, maxX = 0, minY = canvasHeight, maxY = 0;
    bool hasContent = false;

    if (selectionMask && selectionMask->hasSelection()) {
        m_state.isFromSelection = true;
        auto bounds = selectionMask->getBounds();
        minX = static_cast<int>(bounds.x);
        minY = static_cast<int>(bounds.y);
        maxX = static_cast<int>(bounds.x + bounds.width - 1);
        maxY = static_cast<int>(bounds.y + bounds.height - 1);
        hasContent = (bounds.width > 0 && bounds.height > 0);
    } else {
        // Encontra o bounding box dos pixels desenhados na camada ativa
        const auto& grid = activeLayer->getTileGrid();
        for (int ty = 0; ty < grid.getTilesCountY(); ++ty) {
            for (int tx = 0; tx < grid.getTilesCountX(); ++tx) {
                const auto* tile = const_cast<canvas::TileGrid&>(grid).getTile(tx, ty);
                if (tile) {
                    const auto& buf = tile->getBuffer();
                    int tpx = tile->getPixelX();
                    int tpy = tile->getPixelY();

                    for (int ly = 0; ly < canvas::Tile::TILE_SIZE && tpy + ly < canvasHeight; ++ly) {
                        for (int lx = 0; lx < canvas::Tile::TILE_SIZE && tpx + lx < canvasWidth; ++lx) {
                            if (buf.getPixel(lx, ly).a > 0) {
                                int gx = tpx + lx;
                                int gy = tpy + ly;
                                if (gx < minX) minX = gx;
                                if (gx > maxX) maxX = gx;
                                if (gy < minY) minY = gy;
                                if (gy > maxY) maxY = gy;
                                hasContent = true;
                            }
                        }
                    }
                }
            }
        }
    }

    if (!hasContent || minX > maxX || minY > maxY) {
        return false;
    }

    const int bw = maxX - minX + 1;
    const int bh = maxY - minY + 1;

    m_state.sourceBounds = math::Rect2D{
        static_cast<double>(minX),
        static_cast<double>(minY),
        static_cast<double>(bw),
        static_cast<double>(bh)
    };
    m_state.pivotX = minX + bw / 2.0;
    m_state.pivotY = minY + bh / 2.0;
    m_state.currentDx = 0.0;
    m_state.currentDy = 0.0;
    m_state.currentScaleX = 1.0;
    m_state.currentScaleY = 1.0;
    m_state.currentRotationDeg = 0.0;
    m_state.flipH = false;
    m_state.flipV = false;

    m_sourceBuffer = std::make_unique<canvas::PixelBuffer>(bw, bh, ColorRGBA{0, 0, 0, 0});

    // Copia os pixels da camada ativa para o sourceBuffer
    auto& grid = activeLayer->getTileGrid();
    for (int y = 0; y < bh; ++y) {
        int gy = minY + y;
        for (int x = 0; x < bw; ++x) {
            int gx = minX + x;
            int tx = gx / canvas::Tile::TILE_SIZE;
            int ty = gy / canvas::Tile::TILE_SIZE;
            auto* tile = grid.getTile(tx, ty);
            if (tile) {
                int lx = gx % canvas::Tile::TILE_SIZE;
                int ly = gy % canvas::Tile::TILE_SIZE;
                auto col = tile->getBuffer().getPixel(lx, ly);

                if (m_state.isFromSelection && selectionMask) {
                    uint8_t sVal = selectionMask->getValue(gx, gy);
                    if (sVal == 0) {
                        col = {0, 0, 0, 0};
                    } else if (sVal < 255) {
                        col.a = static_cast<uint8_t>((static_cast<int>(col.a) * sVal) / 255);
                    }
                }
                m_sourceBuffer->setPixel(x, y, col);
            }
        }
    }

    // Inicia passo no UndoManager e limpa a área de origem da camada ativa
    const int startTileX = minX / canvas::Tile::TILE_SIZE;
    const int endTileX   = maxX / canvas::Tile::TILE_SIZE;
    const int startTileY = minY / canvas::Tile::TILE_SIZE;
    const int endTileY   = maxY / canvas::Tile::TILE_SIZE;

    undoManager.beginStep("Transform");

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

    // Apaga os pixels de origem da camada ativa
    for (int y = 0; y < bh; ++y) {
        int gy = minY + y;
        for (int x = 0; x < bw; ++x) {
            int gx = minX + x;
            int tx = gx / canvas::Tile::TILE_SIZE;
            int ty = gy / canvas::Tile::TILE_SIZE;
            auto* tile = grid.getTile(tx, ty);
            if (tile) {
                int lx = gx % canvas::Tile::TILE_SIZE;
                int ly = gy % canvas::Tile::TILE_SIZE;
                if (m_state.isFromSelection && selectionMask) {
                    uint8_t sVal = selectionMask->getValue(gx, gy);
                    if (sVal > 0) {
                        auto cur = tile->getBuffer().getPixel(lx, ly);
                        if (sVal == 255) {
                            cur.a = 0;
                        } else {
                            cur.a = static_cast<uint8_t>(std::clamp((static_cast<int>(cur.a) * (255 - sVal)) / 255, 0, 255));
                        }
                        tile->getBuffer().setPixel(lx, ly, cur);
                        tile->setDirty(true);
                    }
                } else {
                    tile->getBuffer().setPixel(lx, ly, {0, 0, 0, 0});
                    tile->setDirty(true);
                }
            }
        }
    }

    m_state.active = true;
    return true;
}

math::Rect2D TransformEngine::calculateDestBounds(
    double dx, double dy,
    double scaleX, double scaleY,
    double rotationDeg,
    double pivotX, double pivotY,
    bool flipH, bool flipV
) const noexcept {
    if (!m_state.active || !m_sourceBuffer) return {0, 0, 0, 0};

    const double bx0 = m_state.sourceBounds.x;
    const double by0 = m_state.sourceBounds.y;
    const double bw = m_state.sourceBounds.width;
    const double bh = m_state.sourceBounds.height;

    const double sx = (flipH ? -scaleX : scaleX);
    const double sy = (flipV ? -scaleY : scaleY);
    const double rad = rotationDeg * (PI / 180.0);
    const double cosR = std::cos(rad);
    const double sinR = std::sin(rad);

    double cornersX[4] = {bx0, bx0 + bw, bx0 + bw, bx0};
    double cornersY[4] = {by0, by0, by0 + bh, by0 + bh};

    double minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;

    for (int i = 0; i < 4; ++i) {
        // Translação para pivô
        double px = (cornersX[i] - pivotX) * sx;
        double py = (cornersY[i] - pivotY) * sy;

        // Rotação
        double rx = px * cosR - py * sinR;
        double ry = px * sinR + py * cosR;

        // Destino
        double destX = rx + pivotX + dx;
        double destY = ry + pivotY + dy;

        if (destX < minX) minX = destX;
        if (destX > maxX) maxX = destX;
        if (destY < minY) minY = destY;
        if (destY > maxY) maxY = destY;
    }

    return math::Rect2D{
        std::floor(minX) - 2.0,
        std::floor(minY) - 2.0,
        std::ceil(maxX - minX) + 4.0,
        std::ceil(maxY - minY) + 4.0
    };
}

bool TransformEngine::commitTransform(
    document::Layer* activeLayer,
    double dx, double dy,
    double scaleX, double scaleY,
    double rotationDeg,
    double pivotX, double pivotY,
    bool flipH, bool flipV,
    int interpMode,
    int canvasWidth,
    int canvasHeight,
    canvas::TileUndoManager& undoManager,
    int activeLayerIndex,
    math::Rect2D& outDirtyBounds
) {
    if (!m_state.active || !m_sourceBuffer || !activeLayer) {
        reset();
        return false;
    }

    auto destBounds = calculateDestBounds(dx, dy, scaleX, scaleY, rotationDeg, pivotX, pivotY, flipH, flipV);

    int minDx = std::clamp(static_cast<int>(destBounds.x), 0, canvasWidth - 1);
    int minDy = std::clamp(static_cast<int>(destBounds.y), 0, canvasHeight - 1);
    int maxDx = std::clamp(static_cast<int>(destBounds.x + destBounds.width), 0, canvasWidth - 1);
    int maxDy = std::clamp(static_cast<int>(destBounds.y + destBounds.height), 0, canvasHeight - 1);

    if (minDx > maxDx || minDy > maxDy) {
        reset();
        return false;
    }

    const double sx = (flipH ? -scaleX : scaleX);
    const double sy = (flipV ? -scaleY : scaleY);
    if (std::abs(sx) < 0.0001 || std::abs(sy) < 0.0001) {
        reset();
        return false;
    }

    const double rad = rotationDeg * (PI / 180.0);
    const double cosR = std::cos(rad);
    const double sinR = std::sin(rad);

    auto& grid = activeLayer->getTileGrid();

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

    const double srcX0 = m_state.sourceBounds.x;
    const double srcY0 = m_state.sourceBounds.y;
    const int srcW = m_sourceBuffer->getWidth();
    const int srcH = m_sourceBuffer->getHeight();

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

                    // Vetor do pivô transformado
                    double dpx = destX - (pivotX + dx);
                    double dpy = destY - (pivotY + dy);

                    // Rotação inversa (-rad)
                    double rx = dpx * cosR + dpy * sinR;
                    double ry = -dpx * sinR + dpy * cosR;

                    // Escala inversa
                    double ux = rx / sx;
                    double uy = ry / sy;

                    // Coordenada original no sourceBuffer
                    double u = pivotX + ux - srcX0;
                    double v = pivotY + uy - srcY0;

                    if (u >= -0.5 && u <= srcW + 0.5 && v >= -0.5 && v <= srcH + 0.5) {
                        ColorRGBA sampled;
                        if (interpMode == static_cast<int>(InterpolationMode::Nearest)) {
                            sampled = sampleNearest(*m_sourceBuffer, u, v);
                        } else if (interpMode == static_cast<int>(InterpolationMode::Bilinear)) {
                            sampled = sampleBilinear(*m_sourceBuffer, u, v);
                        } else {
                            sampled = sampleBicubic(*m_sourceBuffer, u, v);
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

    outDirtyBounds = math::Rect2D{
        std::min(m_state.sourceBounds.x, destBounds.x),
        std::min(m_state.sourceBounds.y, destBounds.y),
        std::max(m_state.sourceBounds.x + m_state.sourceBounds.width, destBounds.x + destBounds.width) - std::min(m_state.sourceBounds.x, destBounds.x),
        std::max(m_state.sourceBounds.y + m_state.sourceBounds.height, destBounds.y + destBounds.height) - std::min(m_state.sourceBounds.y, destBounds.y)
    };

    reset();
    return true;
}

bool TransformEngine::cancelTransform(
    document::Layer* activeLayer,
    int canvasWidth,
    int canvasHeight,
    canvas::TileUndoManager& undoManager,
    int activeLayerIndex,
    math::Rect2D& outDirtyBounds
) {
    if (!m_state.active || !m_sourceBuffer || !activeLayer) {
        reset();
        return false;
    }

    // Restaura os pixels originais no TileGrid
    const int minX = static_cast<int>(m_state.sourceBounds.x);
    const int minY = static_cast<int>(m_state.sourceBounds.y);
    const int bw = m_sourceBuffer->getWidth();
    const int bh = m_sourceBuffer->getHeight();

    auto& grid = activeLayer->getTileGrid();

    for (int y = 0; y < bh; ++y) {
        int gy = minY + y;
        for (int x = 0; x < bw; ++x) {
            int gx = minX + x;
            int tx = gx / canvas::Tile::TILE_SIZE;
            int ty = gy / canvas::Tile::TILE_SIZE;
            auto* tile = grid.getOrCreateTile(tx, ty);
            int lx = gx % canvas::Tile::TILE_SIZE;
            int ly = gy % canvas::Tile::TILE_SIZE;
            auto col = m_sourceBuffer->getPixel(x, y);
            if (col.a > 0) {
                tile->getBuffer().setPixel(lx, ly, col);
                tile->setDirty(true);
            }
        }
    }

    outDirtyBounds = m_state.sourceBounds;
    reset();
    return true;
}

bool TransformEngine::flipLayer(
    document::Layer* activeLayer,
    bool horizontal,
    int canvasWidth,
    int canvasHeight,
    canvas::TileUndoManager& undoManager,
    int activeLayerIndex,
    math::Rect2D& outDirtyBounds
) {
    if (!beginTransform(activeLayer, nullptr, canvasWidth, canvasHeight, undoManager, activeLayerIndex)) {
        return false;
    }
    return commitTransform(
        activeLayer,
        0.0, 0.0, 1.0, 1.0, 0.0,
        m_state.pivotX, m_state.pivotY,
        horizontal, !horizontal,
        static_cast<int>(InterpolationMode::Bicubic),
        canvasWidth, canvasHeight,
        undoManager, activeLayerIndex,
        outDirtyBounds
    );
}

bool TransformEngine::rotateLayer90(
    document::Layer* activeLayer,
    bool clockwise,
    int canvasWidth,
    int canvasHeight,
    canvas::TileUndoManager& undoManager,
    int activeLayerIndex,
    math::Rect2D& outDirtyBounds
) {
    if (!beginTransform(activeLayer, nullptr, canvasWidth, canvasHeight, undoManager, activeLayerIndex)) {
        return false;
    }
    double angle = clockwise ? 90.0 : -90.0;
    return commitTransform(
        activeLayer,
        0.0, 0.0, 1.0, 1.0, angle,
        m_state.pivotX, m_state.pivotY,
        false, false,
        static_cast<int>(InterpolationMode::Bicubic),
        canvasWidth, canvasHeight,
        undoManager, activeLayerIndex,
        outDirtyBounds
    );
}

void TransformEngine::reset() noexcept {
    m_state = TransformState{};
    m_sourceBuffer.reset();
}

} // namespace aladyn::engine::raster
