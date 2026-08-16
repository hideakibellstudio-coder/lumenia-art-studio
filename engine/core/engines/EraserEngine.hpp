#ifndef ALADYN_ENGINE_ERASER_ENGINE_HPP
#define ALADYN_ENGINE_ERASER_ENGINE_HPP

#include "IBrushEngine.hpp"

namespace aladyn::engine::document { class Layer; }

namespace aladyn::engine::engines {

// ─── MINI-MOTOR DE BORRACHA (EraserEngine) ────────────────────────────────
//
// Física: Redução do canal alpha dos pixels na área do dab, proporcional
// à pressão e à opacidade. O DabBlendMode::Erase é forçado internamente —
// o combobox de blend mode fica desabilitado na UI para este motor.
//
// Parâmetros exclusivos: NENHUM — borracha só precisa de primitivas comuns.
//
// Parâmetros comuns usados:
//   brushSize, minSizePercent, opacity, hardness, spacingFactor,
//   pressureSizeCurve, tip.angle, tip.aspectRatio, shapeTexture.
//
// Parâmetros NÃO usados:
//   brushHeightTexture, canvasHeightTexture, brushGrain*, blendMode,
//   scatterCount, velocitySizeEnabled.
// ───────────────────────────────────────────────────────────────────────────
class EraserEngine final : public IBrushEngine {
public:
    EraserEngine() = default;

    void renderDab(
        const raster::Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
        const canvas::PixelBuffer* compositeBuffer = nullptr,
        const raster::PixelContext& ctx = {}
    ) override;

    [[nodiscard]] brush::EngineType getType() const noexcept override {
        return brush::EngineType::Eraser;
    }
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_ERASER_ENGINE_HPP
