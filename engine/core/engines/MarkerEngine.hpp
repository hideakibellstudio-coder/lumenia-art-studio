#ifndef ALADYN_ENGINE_MARKER_ENGINE_HPP
#define ALADYN_ENGINE_MARKER_ENGINE_HPP

#include "IBrushEngine.hpp"

namespace aladyn::engine::document { class Layer; }

namespace aladyn::engine::engines {

// ─── MINI-MOTOR DE MARCADOR / FELTRO DE ÁLCOOL (MarkerEngine) ──────────────
//
// Física: Tinta à base de álcool que se funde com passadas anteriores (Multiply)
// e acumula pigmento nas bordas por evaporação rápida do solvente.
//
// Parâmetros exclusivos usados:
//   profile.markerParams.solventWetness  (umidade do solvente / fusão)
//   profile.markerParams.edgeDarkening   (escurecimento da borda do dab)
//
// Parâmetros comuns usados:
//   brushSize, minSizePercent, opacity, hardness, spacingFactor,
//   pressureSizeCurve, tip (angle, aspectRatio, followStroke).
// ───────────────────────────────────────────────────────────────────────────
class MarkerEngine final : public IBrushEngine {
public:
    MarkerEngine() = default;

    void renderDab(
        const raster::Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
        const canvas::PixelBuffer* compositeBuffer = nullptr,
        const raster::PixelContext& ctx = {}
    ) override;

    [[nodiscard]] brush::EngineType getType() const noexcept override {
        return brush::EngineType::Marker;
    }
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_MARKER_ENGINE_HPP
