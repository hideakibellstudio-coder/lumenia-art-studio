#ifndef ALADYN_ENGINE_STROKE_LATENCY_POLICY_HPP
#define ALADYN_ENGINE_STROKE_LATENCY_POLICY_HPP

#include "StrokeOrchestrator.hpp"

// Compartilhado por StrokeOrchestrator.cpp (updateStrokeRaw) e
// StrokeOrchestratorEnd.cpp (endStrokeRaw) desde a divisão de 2026-09-22.

namespace aladyn::engine::boundary::orchestrator::detail {


/// O atalho de baixa latência só vale quando não há estabilização pedida.
///
/// Antes, `ctx.lowLatency` sozinho desviava o estabilizador. Como
/// `low_latency=True` é o padrão do AladynBackend, o slider de suavização da
/// interface nascia inerte: o valor era gravado, persistido e lido de volta, e
/// o motor o ignorava — sem nenhum aviso.
///
/// `DynamicStabilizer::update` já devolve o ponto bruto quando a estabilização
/// é ~0, então nesse caso o atalho continua valendo e o comportamento não muda.
/// Quando o artista pede suavização, ele passa a recebê-la nos dois modos.
///
/// O atalho também desliga o catch-up e o afunilamento do pen-up, e isso é
/// deliberado: um traço estabilizado sem catch-up pára atrás de onde a caneta
/// levantou — o "efeito elástico" que a suavização existe para evitar.
[[nodiscard]] inline bool useLatencyShortcut(const RawStrokeContext& ctx) noexcept {
    return ctx.lowLatency && ctx.stabilizer.getStabilizationPercentage() <= 0.5;
}

} // namespace aladyn::engine::boundary::orchestrator::detail

#endif // ALADYN_ENGINE_STROKE_LATENCY_POLICY_HPP
