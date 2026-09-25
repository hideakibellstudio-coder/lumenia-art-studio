#ifndef ALADYN_ENGINE_IBRUSH_ENGINE_HPP
#define ALADYN_ENGINE_IBRUSH_ENGINE_HPP

#include "../brush/BrushProfile.hpp"
#include "../canvas/CanvasTexture.hpp"
#include "../canvas/TileGrid.hpp"
#include "../canvas/PixelBuffer.hpp"
#include "../../utils/Dab.hpp"
#include "../raster/PixelContext.hpp"

namespace aladyn::engine::engines {

// ─── INTERFACE POLIMÓRFICA BASE PARA TODOS OS MINI-MOTORES ─────────────────
//
// Cada mini-motor herda IBrushEngine e implementa apenas a lógica de
// renderização de um único dab (renderDab). O Facade chama renderDab
// via virtual dispatch sem saber qual motor está ativo.
//
// Commons (DynamicMapper, DabInterpolator, VelocityTracker, etc.) permanecem
// no Facade e são compartilhados por todos os motores.
// ───────────────────────────────────────────────────────────────────────────
class IBrushEngine {
public:
    virtual ~IBrushEngine() = default;

    // Renderiza um único dab na grade de tiles da camada ativa.
    // compositeBuffer: buffer RGBA já composto de todas as camadas (nullable).
    //   - Motores de deposição (Pencil, Inker, Eraser, Marker) → ignoram, passam nullptr.
    //   - BlurEngine  → lê compositeBuffer, aplica kernel Gaussiano, escreve no tileGrid.
    //   - SmudgeEngine → lê compositeBuffer (coleta cor), deposita cor carregada no tileGrid.
    virtual void renderDab(
        const utils::Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
        const canvas::PixelBuffer* compositeBuffer = nullptr,
        const raster::PixelContext& ctx = {}
    ) = 0;

    // Retorna o tipo do motor para identificação pela UI e pelo Facade.
    [[nodiscard]] virtual brush::EngineType getType() const noexcept = 0;

    // Hook opcional chamado quando o motor é ativado (troca de motor).
    // Motores stateful (Smudge, Watercolor) podem resetar buffers internos aqui.
    virtual void onActivate(const brush::BrushProfile& /*profile*/) noexcept {}

    // Hook opcional chamado ao iniciar um novo traço.
    virtual void onBeginStroke() noexcept {}

    // Hook opcional chamado ao terminar um traço.
    virtual void onEndStroke() noexcept {}

    // Retorna true se este motor deve renderizar dabs no scratch layer temporário
    // (ao invés de direto na camada ativa). Blur e Smudge retornam false porque
    // precisam ler e escrever diretamente na camada/compositeBuffer.
    [[nodiscard]] virtual bool usesScratchLayer() const noexcept { return true; }
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_IBRUSH_ENGINE_HPP
