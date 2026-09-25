#ifndef ALADYN_ENGINE_STROKE_PREVIEW_RENDERER_HPP
#define ALADYN_ENGINE_STROKE_PREVIEW_RENDERER_HPP

#include "../../core/brush/BrushProfile.hpp"
#include <cstdint>
#include <vector>

namespace aladyn::engine::boundary::orchestrator {

// Renderiza, fora de qualquer documento, uma pincelada senoidal de demonstração
// com o motor de pincel REAL do perfil (a mesma cadeia DabInterpolator ->
// IBrushEngine/DabRenderer -> TileGrid do traço de verdade) e devolve RGBA8
// width*height*4. Usado pelo painel de pincel (StrokePreview).
//
// Histórico: introduzido em 44ddbeb (2026-08-18) como
// PaintEngineFacade::renderStrokePreview e perdido em silêncio na decomposição
// do facade de dd9765c (2026-08-25) -- a definição sumiu, o binding junto, e o
// painel caiu no desenho vetorial aproximado por 4 semanas porque o adaptador
// Python protegia a chamada com hasattr. Restaurado em 2026-09-22 como função
// livre, fora do facade (que está perto do teto de 450 linhas).
[[nodiscard]] std::vector<uint8_t> renderStrokePreview(
    const brush::BrushProfile& profile,
    int width,
    int height
);

// Máscara A8 (kRoundTipPreviewSize²) de uma ponta redonda com a dureza dada:
// a prévia da ponta quando o perfil não tem textura de forma. Até 2026-09-25
// este laço morava na ponte (bind_stroke.cpp), fora do motor.
inline constexpr int kRoundTipPreviewSize = 64;
[[nodiscard]] std::vector<uint8_t> renderRoundTipMask(double hardness);

} // namespace aladyn::engine::boundary::orchestrator

#endif // ALADYN_ENGINE_STROKE_PREVIEW_RENDERER_HPP
