#ifndef ALADYN_ENGINE_MARKER_ENGINE_HPP
#define ALADYN_ENGINE_MARKER_ENGINE_HPP

#include "IBrushEngine.hpp"
#include "../raster/StrokeInkLedger.hpp"

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
        const utils::Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
        const raster::PixelContext& ctx = {}
    ) override;

    [[nodiscard]] brush::EngineType getType() const noexcept override {
        return brush::EngineType::Marker;
    }

    [[nodiscard]] double reachScale(const brush::BrushProfile& profile) const noexcept override;

    // A memória do traço (base de cada pixel e cobertura) vale por um traço só.
    void onActivate(const brush::BrushProfile& /*profile*/) noexcept override { m_ledger.clear(); m_ledger16.clear(); }
    void onBeginStroke() noexcept override { m_ledger.clear(); m_ledger16.clear(); }
    void onEndStroke() noexcept override { m_ledger.clear(); m_ledger16.clear(); }

private:
    raster::StrokeInkLedger<utils::ColorRGBA> m_ledger;
    raster::StrokeInkLedger<utils::ColorRGBA16> m_ledger16;
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_MARKER_ENGINE_HPP
