#pragma once

#include "StrokeOrchestrator.hpp"

namespace aladyn::engine::boundary::internal {

// Amostra de telemetria devolvida por updateStroke. Espelha
// boundary::TelemetryData, mas vive aqui para que este orquestrador nao
// precise incluir PaintEngineFacade.hpp -- o facade converte numa linha.
struct StrokeTelemetrySample {
    double pressure{0.0};
    double velocity{0.0};
    double outputFlow{0.0};
};

// Sessao de traco no caminho PointerEvent (begin/update/end) e o snapshot de
// telemetria associado.
//
// Extraido de PaintEngineFacade.cpp (Achado #6). Reusa o RawStrokeContext que
// o StrokeOrchestrator ja definia para o fast-path nativo: os dois caminhos
// sempre precisaram exatamente do mesmo estado, mas so o fast-path tinha o
// contrato escrito -- o caminho PointerEvent mexia nos membros do facade
// diretamente. Agora os dois passam pelo mesmo agregado.
//
// Vive num arquivo proprio em vez de dentro de StrokeOrchestrator.cpp porque
// aquele arquivo ja esta em excecao declarada de LOC (484 linhas); somar a
// sessao de traco la dentro empurraria para ~580.
class StrokeSessionOrchestrator {
public:
    static void beginStroke(RawStrokeContext& ctx, const stroke::PointerEvent& event);
    static StrokeTelemetrySample updateStroke(RawStrokeContext& ctx, const stroke::PointerEvent& event);

    // Devolve false quando nao havia traco em andamento (nada foi feito e o
    // documento nao deve ser marcado como alterado).
    static bool endStroke(RawStrokeContext& ctx);

    static void renderSegment(RawStrokeContext& ctx, const raster::Dab& startDab, const raster::Dab& endDab);

    static telemetry::RealTimeStrokeMetrics telemetrySnapshot(
        const document::LayerStack& stack,
        const canvas::TileUndoManager& undoManager,
        const telemetry::EngineTelemetryManager& telemetryManager
    );
};

} // namespace aladyn::engine::boundary::internal
