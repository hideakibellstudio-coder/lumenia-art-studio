#ifndef ALADYN_ENGINE_BLUR_ENGINE_HPP
#define ALADYN_ENGINE_BLUR_ENGINE_HPP

#include "BlurScratch.hpp"
#include "IBrushEngine.hpp"

namespace aladyn::engine::document { class Layer; }

namespace aladyn::engine::engines {

// ─── MINI-MOTOR DE BLUR / DESFOQUE (BlurEngine) ────────────────────────────
//
// Física: Suavização local por amostragem de vizinhança (kernel de desfoque)
// lendo a própria camada (uma cópia da área, antes de alterá-la) e escrevendo no tileGrid dela.
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
        const raster::PixelContext& ctx = {}
    ) override;

    [[nodiscard]] brush::EngineType getType() const noexcept override {
        return brush::EngineType::Blur;
    }

    // Blur lê uma cópia da área da camada ativa e escreve direto nela — sem scratch.
    [[nodiscard]] bool usesScratchLayer() const noexcept override { return false; }

private:
    BlurScratch m_scratch;  // a memória de trabalho do desfoque, guardada entre carimbos
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_BLUR_ENGINE_HPP
