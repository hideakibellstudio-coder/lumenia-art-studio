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

// commitTransform e cancelTransform vivem em TransformEngineCommit.cpp (divisão de
// 2026-09-22: o arquivo tinha 478 linhas, acima do teto ARCcC de 450).

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
