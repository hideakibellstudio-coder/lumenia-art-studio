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
    //
    // A grade (`tileGrid`) é a fonte e o destino: nenhum motor lê a imagem composta
    // das camadas. Até 2026-10-01 o contrato prometia um `compositeBuffer` que o Blur e
    // o Smudge "leriam"; os oito motores o ignoravam, e a promessa enganava quem fosse
    // escrever o próximo. Um motor que precise ler a composição pede isso por um
    // contrato novo, junto da feature (ver docs/01-correcao-da-base/07-*.md, D14).
    virtual void renderDab(
        const utils::Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
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

    // Quantas vezes o raio do dab o motor realmente alcança (a mancha úmida da aquarela passa de 1). O
    // orquestrador usa isto para a área suja: desfazer, mistura de opacidade e recomposição precisam cobrir
    // todo pixel que o motor toca, não só o círculo do dab.
    [[nodiscard]] virtual double reachScale(const brush::BrushProfile& /*profile*/) const noexcept { return 1.0; }

    // Retorna true se este motor deve renderizar dabs no scratch layer temporário
    // (ao invés de direto na camada ativa). Blur e Smudge retornam false porque
    // precisam ler e escrever diretamente na camada.
    [[nodiscard]] virtual bool usesScratchLayer() const noexcept { return true; }
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_IBRUSH_ENGINE_HPP
