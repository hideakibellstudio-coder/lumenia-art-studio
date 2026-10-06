#ifndef ALADYN_ENGINE_WATERCOLOR_ENGINE_HPP
#define ALADYN_ENGINE_WATERCOLOR_ENGINE_HPP

#include "IBrushEngine.hpp"
#include "../raster/StrokeInkLedger.hpp"

namespace aladyn::engine::document { class Layer; }

namespace aladyn::engine::engines {

// ─── MINI-MOTOR DE AQUARELA REALISTA (WatercolorEngine) ────────────────────
//
// Física: Fluidodinâmica de pigmento suspenso em água sobre meio poroso.
//
// Parâmetros exclusivos usados:
//   profile.watercolorParams.waterLevel       (nível de umidade depositado 0-1)
//   profile.watercolorParams.pigmentBleed     (taxa de difusão Wet-on-Wet para vizinhos úmidos 0-1)
//   profile.watercolorParams.fringeIntensity  (Coffee Ring Effect: anel de borda escura de secagem 0-1)
//   profile.watercolorParams.granulation      (deposição de pigmento nos vales da textura do papel 0-1)
// ───────────────────────────────────────────────────────────────────────────
class WatercolorEngine final : public IBrushEngine {
public:
    WatercolorEngine() = default;

    void renderDab(
        const utils::Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
        const raster::PixelContext& ctx = {}
    ) override;

    [[nodiscard]] brush::EngineType getType() const noexcept override {
        return brush::EngineType::Watercolor;
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

#endif // ALADYN_ENGINE_WATERCOLOR_ENGINE_HPP
