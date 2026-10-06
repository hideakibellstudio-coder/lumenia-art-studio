#ifndef ALADYN_ENGINE_SMUDGE_ENGINE_HPP
#define ALADYN_ENGINE_SMUDGE_ENGINE_HPP

#include "IBrushEngine.hpp"
#include "SmearPatch.hpp"
#include "../../utils/Point2D.hpp"

namespace aladyn::engine::document { class Layer; }

namespace aladyn::engine::engines {

// ─── MINI-MOTOR DE SMUDGE / ARRASTO (SmudgeEngine) ──────────────────────────
//
// Física: o pincel carrega um pedaço da imagem (`SmearPatch`, do tamanho do dab) e o arrasta pela tela:
// a cada carimbo o que está sob o pincel vira o carregado, na força do carimbo, e o carregado se mistura
// aos poucos ao que o pincel pisa. Linha fina arrastada continua linha, com a forma que tinha.
//
// Parâmetros exclusivos usados:
//   profile.smudgeParams.colorPickup    (quanto o pincel se limpa pisando: menos coleta, arrasto mais longo)
//   profile.smudgeParams.mixRatio       (a força: quanto do carregado substitui o que está sob o pincel)
//   profile.smudgeParams.smudgeStretch  (alonga o arrasto: o pincel demora mais a se limpar)
//
// Parâmetros comuns usados:
//   brushSize, minSizePercent, opacity/flow, hardness, spacingFactor, tip.
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
        m_patch.reset();
        m_hasStarted = false;
    }

private:
    SmearPatch     m_patch;
    bool           m_hasStarted{false};
    utils::Point2D m_lastPosition{0.0, 0.0};
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_SMUDGE_ENGINE_HPP
