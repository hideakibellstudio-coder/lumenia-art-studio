#include "ViewportTransform.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::math {

namespace {
constexpr double PI = 3.14159265358979323846;
inline double degToRad(double deg) noexcept {
    return deg * (PI / 180.0);
}
} // namespace

ViewportTransform::ViewportTransform(
    double viewportWidth,
    double viewportHeight,
    double canvasWidth,
    double canvasHeight
) noexcept
    : m_viewportWidth(viewportWidth),
      m_viewportHeight(viewportHeight),
      m_canvasWidth(canvasWidth),
      m_canvasHeight(canvasHeight) {
    updateMatrices();
}

void ViewportTransform::setViewportSize(double w, double h) noexcept {
    m_viewportWidth = std::max(1.0, w);
    m_viewportHeight = std::max(1.0, h);
    updateMatrices();
}

void ViewportTransform::setCanvasSize(double w, double h) noexcept {
    m_canvasWidth = std::max(1.0, w);
    m_canvasHeight = std::max(1.0, h);
    updateMatrices();
}

void ViewportTransform::setCamera(
    double panX, double panY, double zoom, double rotationDeg, bool flipH, bool flipV
) noexcept {
    m_panX = panX;
    m_panY = panY;
    m_zoom = std::max(0.001, zoom);
    m_rotationDeg = rotationDeg;
    m_flipH = flipH;
    m_flipV = flipV;
    updateMatrices();
}

void ViewportTransform::updateMatrices() noexcept {
    const double rad = degToRad(m_rotationDeg);
    const double c = std::cos(rad);
    const double s = std::sin(rad);

    const double sx = m_flipH ? -m_zoom : m_zoom;
    const double sy = m_flipV ? -m_zoom : m_zoom;

    m_m00 = c * sx;
    m_m01 = -s * sy;
    m_m10 = s * sx;
    m_m11 = c * sy;

    const double halfCw = m_canvasWidth * 0.5;
    const double halfCh = m_canvasHeight * 0.5;
    const double halfVw = m_viewportWidth * 0.5;
    const double halfVh = m_viewportHeight * 0.5;

    m_tx = (halfVw + m_panX) - (m_m00 * halfCw + m_m01 * halfCh);
    m_ty = (halfVh + m_panY) - (m_m10 * halfCw + m_m11 * halfCh);

    const double det = m_m00 * m_m11 - m_m01 * m_m10;
    if (std::abs(det) > 1e-12) {
        const double invDet = 1.0 / det;
        m_inv00 =  m_m11 * invDet;
        m_inv01 = -m_m01 * invDet;
        m_inv10 = -m_m10 * invDet;
        m_inv11 =  m_m00 * invDet;

        m_invTx = -(m_inv00 * m_tx + m_inv01 * m_ty);
        m_invTy = -(m_inv10 * m_tx + m_inv11 * m_ty);
    }
}

utils::Point2D ViewportTransform::canvasToScreen(double cx, double cy) const noexcept {
    return utils::Point2D{
        m_m00 * cx + m_m01 * cy + m_tx,
        m_m10 * cx + m_m11 * cy + m_ty
    };
}

utils::Point2D ViewportTransform::screenToCanvas(double sx, double sy) const noexcept {
    return utils::Point2D{
        m_inv00 * sx + m_inv01 * sy + m_invTx,
        m_inv10 * sx + m_inv11 * sy + m_invTy
    };
}

utils::Rect2D ViewportTransform::getVisibleCanvasBounds() const noexcept {
    const utils::Point2D c0 = screenToCanvas(0.0, 0.0);
    const utils::Point2D c1 = screenToCanvas(m_viewportWidth, 0.0);
    const utils::Point2D c2 = screenToCanvas(m_viewportWidth, m_viewportHeight);
    const utils::Point2D c3 = screenToCanvas(0.0, m_viewportHeight);

    const double minX = std::max(0.0, std::min({c0.x, c1.x, c2.x, c3.x}));
    const double minY = std::max(0.0, std::min({c0.y, c1.y, c2.y, c3.y}));
    const double maxX = std::min(m_canvasWidth,  std::max({c0.x, c1.x, c2.x, c3.x}));
    const double maxY = std::min(m_canvasHeight, std::max({c0.y, c1.y, c2.y, c3.y}));

    return utils::Rect2D{minX, minY, std::max(0.0, maxX - minX), std::max(0.0, maxY - minY)};
}

std::tuple<int, int, int, int> ViewportTransform::getVisibleTileRange(
    int tileSize,
    int maxTilesX,
    int maxTilesY
) const noexcept {
    if (tileSize <= 0 || maxTilesX <= 0 || maxTilesY <= 0) {
        return {0, 0, 0, 0};
    }

    const utils::Rect2D bounds = getVisibleCanvasBounds();
    int minTx = static_cast<int>(std::floor(bounds.x / tileSize));
    int minTy = static_cast<int>(std::floor(bounds.y / tileSize));
    int maxTx = static_cast<int>(std::floor((bounds.x + bounds.width) / tileSize));
    int maxTy = static_cast<int>(std::floor((bounds.y + bounds.height) / tileSize));

    minTx = std::clamp(minTx, 0, maxTilesX - 1);
    minTy = std::clamp(minTy, 0, maxTilesY - 1);
    maxTx = std::clamp(maxTx, 0, maxTilesX - 1);
    maxTy = std::clamp(maxTy, 0, maxTilesY - 1);

    return {minTx, minTy, maxTx, maxTy};
}

bool ViewportTransform::isTileVisible(int tx, int ty, int tileSize) const noexcept {
    const double tileMinX = tx * tileSize;
    const double tileMinY = ty * tileSize;
    const double tileMaxX = tileMinX + tileSize;
    const double tileMaxY = tileMinY + tileSize;

    const utils::Rect2D bounds = getVisibleCanvasBounds();
    const double visMinX = bounds.x;
    const double visMinY = bounds.y;
    const double visMaxX = bounds.x + bounds.width;
    const double visMaxY = bounds.y + bounds.height;

    return !(tileMaxX < visMinX || tileMinX > visMaxX || tileMaxY < visMinY || tileMinY > visMaxY);
}

} // namespace aladyn::engine::math
