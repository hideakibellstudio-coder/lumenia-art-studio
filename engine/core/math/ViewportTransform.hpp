#ifndef ALADYN_ENGINE_VIEWPORT_TRANSFORM_HPP
#define ALADYN_ENGINE_VIEWPORT_TRANSFORM_HPP

#include "../../utils/Point2D.hpp"
#include "../../utils/Rect2D.hpp"
#include <tuple>
#include <utility>

namespace aladyn::engine::math {

/**
 * @brief Transformador 2D analítico de coordenadas e Frustum Culler para Viewport de 120 FPS.
 */
class ViewportTransform {
public:
    ViewportTransform(
        double viewportWidth = 1920.0,
        double viewportHeight = 1080.0,
        double canvasWidth = 1920.0,
        double canvasHeight = 1080.0
    ) noexcept;

    void setViewportSize(double w, double h) noexcept;
    void setCanvasSize(double w, double h) noexcept;
    void setCamera(double panX, double panY, double zoom, double rotationDeg, bool flipH = false, bool flipV = false) noexcept;

    [[nodiscard]] utils::Point2D canvasToScreen(double cx, double cy) const noexcept;
    [[nodiscard]] utils::Point2D screenToCanvas(double sx, double sy) const noexcept;

    [[nodiscard]] utils::Rect2D getVisibleCanvasBounds() const noexcept;

    /**
     * @brief Retorna o intervalo retangular de tiles (minTx, minTy, maxTx, maxTy) visíveis no Viewport.
     */
    [[nodiscard]] std::tuple<int, int, int, int> getVisibleTileRange(
        int tileSize,
        int maxTilesX,
        int maxTilesY
    ) const noexcept;

    [[nodiscard]] bool isTileVisible(int tx, int ty, int tileSize) const noexcept;

    [[nodiscard]] double getZoom() const noexcept { return m_zoom; }
    [[nodiscard]] double getPanX() const noexcept { return m_panX; }
    [[nodiscard]] double getPanY() const noexcept { return m_panY; }
    [[nodiscard]] double getRotationDeg() const noexcept { return m_rotationDeg; }

private:
    void updateMatrices() noexcept;

    double m_viewportWidth{1920.0};
    double m_viewportHeight{1080.0};
    double m_canvasWidth{1920.0};
    double m_canvasHeight{1080.0};

    double m_panX{0.0};
    double m_panY{0.0};
    double m_zoom{1.0};
    double m_rotationDeg{0.0};
    bool   m_flipH{false};
    bool   m_flipV{false};

    // Matriz afim direta: screen = M * canvas + V
    // [m00 m01 | tx]
    // [m10 m11 | ty]
    double m_m00{1.0}, m_m01{0.0}, m_tx{0.0};
    double m_m10{0.0}, m_m11{1.0}, m_ty{0.0};

    // Matriz inversa: canvas = InvM * screen + InvV
    double m_inv00{1.0}, m_inv01{0.0}, m_invTx{0.0};
    double m_inv10{0.0}, m_inv11{1.0}, m_invTy{0.0};
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_VIEWPORT_TRANSFORM_HPP
