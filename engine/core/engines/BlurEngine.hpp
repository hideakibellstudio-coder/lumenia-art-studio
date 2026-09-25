#ifndef ALADYN_ENGINE_BLUR_ENGINE_HPP
#define ALADYN_ENGINE_BLUR_ENGINE_HPP

#include "IBrushEngine.hpp"

namespace aladyn::engine::document { class Layer; }

namespace aladyn::engine::engines {

// ─── MINI-MOTOR DE BLUR / DESFOQUE (BlurEngine) ────────────────────────────
//
// Física: Suavização local por amostragem de vizinhança (kernel de desfoque)
// lendo do buffer composto (compositeBuffer) e escrevendo no tileGrid da camada.
//
// Parâmetros exclusivos usados:
//   profile.blurParams.blurRadius   (1 a 5 pixels de raio de vizinhança)
//   profile.blurParams.blurStrength (intensidade da mesclagem 0.0 a 1.0)
//
// Parâmetros comuns usados:
//   brushSize, minSizePercent, opacity, hardness, spacingFactor.
// ───────────────────────────────────────────────────────────────────────────
class BlurEngine final : public IBrushEngine {
public:
    BlurEngine() = default;

    void renderDab(
        const utils::Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
        const canvas::PixelBuffer* compositeBuffer = nullptr,
        const raster::PixelContext& ctx = {}
    ) override;

    [[nodiscard]] brush::EngineType getType() const noexcept override {
        return brush::EngineType::Blur;
    }

    // Blur lê do compositeBuffer e escreve direto na camada ativa — sem scratch.
    [[nodiscard]] bool usesScratchLayer() const noexcept override { return false; }
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_BLUR_ENGINE_HPP
