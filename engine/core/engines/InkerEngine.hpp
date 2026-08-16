#ifndef ALADYN_ENGINE_INKER_ENGINE_HPP
#define ALADYN_ENGINE_INKER_ENGINE_HPP

#include "IBrushEngine.hpp"

namespace aladyn::engine::document { class Layer; }

namespace aladyn::engine::engines {

// ─── MINI-MOTOR DE CANETA / NANQUIM / G-PEN (InkerEngine) ──────────────────
//
// Física: Fluxo contínuo de nanquim fluido sobre papel liso.
// O InkerEngine NÃO usa textura (nem brushHeightTexture nem canvasHeightTexture)
// e NÃO aplica equação 3D Contact. O traço é 100% opaco, com borda
// anti-aliased limpa e afunilamento perfeito tipo agulha.
//
// Parâmetros exclusivos usados:
//   profile.inkerParams.inkFlowRate       (taxa de vazão, 0=seco, 1=cheio)
//   profile.inkerParams.taperSmoothing    (suavização do afunilamento)
//
// Parâmetros comuns usados:
//   brushSize, minSizePercent, opacity, hardness, spacingFactor,
//   pressureSizeCurve, tip.angle, tip.aspectRatio, tip.followStroke.
//
// Parâmetros NÃO usados (ignorados pelo motor):
//   brushHeightTexture, canvasHeightTexture, brushGrain*, scatterCount,
//   velocitySizeEnabled, jitters.
// ───────────────────────────────────────────────────────────────────────────
class InkerEngine final : public IBrushEngine {
public:
    InkerEngine() = default;

    void renderDab(
        const raster::Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
        const canvas::PixelBuffer* compositeBuffer = nullptr,
        const raster::PixelContext& ctx = {}
    ) override;

    [[nodiscard]] brush::EngineType getType() const noexcept override {
        return brush::EngineType::Inker;
    }
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_INKER_ENGINE_HPP
