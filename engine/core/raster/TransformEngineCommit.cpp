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
    history::TileUndoManager& undoManager,
    int activeLayerIndex,
    utils::Rect2D& outDirtyBounds
) {
    if (!m_state.active || !m_sourceBuffer || !activeLayer) {
        reset();
        return false;
    }

    auto destBounds = calculateDestBounds(dx, dy, scaleX, scaleY, rotationDeg, pivotX, pivotY, flipH, flipV);

    constexpr int kMinCoord = -32768 * canvas::Tile::TILE_SIZE;
    constexpr int kMaxCoord =  32767 * canvas::Tile::TILE_SIZE;
    int minDx = std::clamp(static_cast<int>(std::floor(destBounds.x)), kMinCoord, kMaxCoord);
    int minDy = std::clamp(static_cast<int>(std::floor(destBounds.y)), kMinCoord, kMaxCoord);
    int maxDx = std::clamp(static_cast<int>(std::ceil(destBounds.x + destBounds.width)), kMinCoord, kMaxCoord);
    int maxDy = std::clamp(static_cast<int>(std::ceil(destBounds.y + destBounds.height)), kMinCoord, kMaxCoord);

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

    outDirtyBounds = utils::Rect2D{
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
    utils::Rect2D& outDirtyBounds
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
    const bool is16 = (grid.getFormat() == canvas::PixelFormat::RGBA16);

    for (int y = 0; y < bh; ++y) {
        int gy = minY + y;
        int ty = divFloor(gy, canvas::Tile::TILE_SIZE);
        int ly = gy - ty * canvas::Tile::TILE_SIZE;
        for (int x = 0; x < bw; ++x) {
            int gx = minX + x;
            int tx = divFloor(gx, canvas::Tile::TILE_SIZE);
            int lx = gx - tx * canvas::Tile::TILE_SIZE;
            auto* tile = grid.getOrCreateTile(tx, ty);
            if (is16) {
                auto col = m_sourceBuffer->getPixel16(x, y);
                if (col.a > 0) {
                    tile->getBuffer().setPixel16(lx, ly, col);
                    tile->setDirty(true);
                }
            } else {
                auto col = m_sourceBuffer->getPixel(x, y);
                if (col.a > 0) {
                    tile->getBuffer().setPixel(lx, ly, col);
                    tile->setDirty(true);
                }
            }
        }
    }

    outDirtyBounds = m_state.sourceBounds;
    reset();
    return true;
}

} // namespace aladyn::engine::raster
