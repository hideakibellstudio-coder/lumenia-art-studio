#ifndef ALADYN_ENGINE_SMUDGE_ENGINE_HPP
#define ALADYN_ENGINE_SMUDGE_ENGINE_HPP

#include "IBrushEngine.hpp"
#include "../canvas/GridSnapshot.hpp"
#include "../../utils/Point2D.hpp"

namespace aladyn::engine::document { class Layer; }

namespace aladyn::engine::engines {

// ─── MINI-MOTOR DE SMUDGE / ARRASTO (SmudgeEngine) ──────────────────────────
//
// Física: Coleta a cor existente sob o primeiro dab do traço e a arrasta
// pela tela, misturando gradualmente com as cores do caminho.
//
// Parâmetros exclusivos usados:
//   profile.smudgeParams.colorPickup    (quantidade de cor coletada da tela)
//   profile.smudgeParams.mixRatio       (mistura entre cor mantida vs cor de destino)
//   profile.smudgeParams.smudgeStretch  (fator de retenção/alongamento do arrasto)
//
// Parâmetros comuns usados:
//   brushSize, minSizePercent, opacity, hardness, spacingFactor, tip.
// ───────────────────────────────────────────────────────────────────────────
class SmudgeEngine final : public IBrushEngine {
public:
    SmudgeEngine() = default;

    void renderDab(
        const utils::Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
        const raster::PixelContext& ctx = {}
    ) override;

    [[nodiscard]] brush::EngineType getType() const noexcept override {
        return brush::EngineType::Smudge;
    }

    // Smudge precisa ler/escrever direto na camada ativa para arrastar tinta — sem scratch.
    [[nodiscard]] bool usesScratchLayer() const noexcept override { return false; }

    void onBeginStroke() noexcept override {
        m_hasCarriedColor = false;
        m_lastPosition    = {0.0, 0.0};
    }

private:
    // Coleta da tela a cor sob o dab e a mistura à que o pincel já carrega; sem cor sob ele, a carregada esmaece.
    void carryColor(const utils::ColorRGBA& sampled, double pickup, double stretch) noexcept;

    bool              m_hasCarriedColor{false};
    utils::ColorRGBA m_carriedColor{0, 0, 0, 0};
    utils::Point2D     m_lastPosition{0.0, 0.0};
    canvas::GridSnapshot m_trailSource; // a grade antes do dab: o rastro lê dela, não da grade viva
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_SMUDGE_ENGINE_HPP
