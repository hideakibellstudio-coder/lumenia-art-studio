// TransformEngine::commitTransform / cancelTransform -- separados de
// TransformEngine.cpp em 2026-09-22 (teto ARCcC de 450 linhas). Corpos movidos
// sem alteração. Em 2026-09-23 o laço de amostragem/composição foi para
// transform/InverseMappedComposite.hpp (compartilhado com Distorcer).
#include "TransformEngine.hpp"
#include "transform/InverseMappedComposite.hpp"
#include <cmath>
#include <algorithm>
#include <cstring>

namespace aladyn::engine::raster {

static constexpr double PI = 3.14159265358979323846;

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

    const double srcX0 = m_state.sourceBounds.x;
    const double srcY0 = m_state.sourceBounds.y;
    const int srcW = m_sourceBuffer->getWidth();
    const int srcH = m_sourceBuffer->getHeight();

    transform::compositeInverseMapped(
        activeLayer->getTileGrid(), *m_sourceBuffer, minDx, minDy, maxDx, maxDy,
        interpMode, undoManager, activeLayerIndex,
        [&](int destX, int destY, double& u, double& v) {
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
            u = pivotX + ux - srcX0;
            v = pivotY + uy - srcY0;
            return u >= -0.5 && u <= srcW + 0.5 && v >= -0.5 && v <= srcH + 0.5;
        });

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

} // namespace aladyn::engine::raster
