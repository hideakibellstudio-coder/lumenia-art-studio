// Transformar -> Distorcer: cada canto da caixa vai para onde o usuário
// arrastou (mapeamento projetivo). Criado em 2026-09-23; antes o modo
// "Distorcer" da UI fazia o mesmo que "Livre".
#include "TransformEngine.hpp"
#include "transform/Homography.hpp"
#include "transform/InverseMappedComposite.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::raster {

bool TransformEngine::commitTransformDistort(
    document::Layer* activeLayer,
    const std::array<double, 8>& corners,
    int interpMode,
    int canvasWidth,
    int canvasHeight,
    canvas::TileUndoManager& undoManager,
    int activeLayerIndex,
    math::Rect2D& outDirtyBounds
) {
    if (!m_state.active || !m_sourceBuffer || !activeLayer || !transform::isConvexQuad(corners)) {
        return false;
    }

    const int srcW = m_sourceBuffer->getWidth();
    const int srcH = m_sourceBuffer->getHeight();
    transform::Homography destToUnit;
    if (srcW <= 0 || srcH <= 0 || !transform::invert(transform::unitSquareToQuad(corners), destToUnit)) {
        return false;
    }

    double qMinX = corners[0], qMaxX = corners[0], qMinY = corners[1], qMaxY = corners[1];
    for (int i = 1; i < 4; ++i) {
        qMinX = std::min(qMinX, corners[2 * i]);
        qMaxX = std::max(qMaxX, corners[2 * i]);
        qMinY = std::min(qMinY, corners[2 * i + 1]);
        qMaxY = std::max(qMaxY, corners[2 * i + 1]);
    }
    const int minDx = std::clamp(static_cast<int>(std::floor(qMinX)), 0, canvasWidth - 1);
    const int minDy = std::clamp(static_cast<int>(std::floor(qMinY)), 0, canvasHeight - 1);
    const int maxDx = std::clamp(static_cast<int>(std::ceil(qMaxX)), 0, canvasWidth - 1);
    const int maxDy = std::clamp(static_cast<int>(std::ceil(qMaxY)), 0, canvasHeight - 1);
    if (qMaxX < 0.0 || qMaxY < 0.0 || qMinX > canvasWidth || qMinY > canvasHeight) {
        return false;  // quad inteiro fora da tela
    }

    // Mesma convenção do commit livre: o pixel de destino X corresponde a
    // u = X - origem no buffer-fonte quando o quad é a própria caixa.
    transform::compositeInverseMapped(
        activeLayer->getTileGrid(), *m_sourceBuffer, minDx, minDy, maxDx, maxDy,
        interpMode, undoManager, activeLayerIndex,
        [&](int destX, int destY, double& u, double& v) {
            double un = 0.0, vn = 0.0;
            if (!destToUnit.apply(destX, destY, un, vn)) return false;
            u = un * srcW;
            v = vn * srcH;
            return u >= -0.5 && u <= srcW + 0.5 && v >= -0.5 && v <= srcH + 0.5;
        });

    const auto& sb = m_state.sourceBounds;
    const double x0 = std::min(sb.x, qMinX), y0 = std::min(sb.y, qMinY);
    const double x1 = std::max(sb.x + sb.width, qMaxX), y1 = std::max(sb.y + sb.height, qMaxY);
    outDirtyBounds = math::Rect2D{x0, y0, x1 - x0, y1 - y0};

    reset();
    return true;
}

} // namespace aladyn::engine::raster
