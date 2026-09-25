#ifndef ALADYN_ENGINE_WATERCOLOR_ENGINE_HPP
#define ALADYN_ENGINE_WATERCOLOR_ENGINE_HPP

#include "IBrushEngine.hpp"

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
        const canvas::PixelBuffer* compositeBuffer = nullptr,
        const raster::PixelContext& ctx = {}
    ) override;

    [[nodiscard]] brush::EngineType getType() const noexcept override {
        return brush::EngineType::Watercolor;
    }
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_WATERCOLOR_ENGINE_HPP
