#pragma once

#include "DocumentContext.hpp"
#include "../../../core/canvas/TileUndoManager.hpp"
#include "../../../core/raster/SelectionMask.hpp"

namespace aladyn::engine::boundary::internal {

// Contexto das operacoes que mexem na geometria do documento inteiro ou no
// historico: alem do que DocumentContext ja carrega, elas precisam do buffer
// de display, da mascara de selecao, do gerenciador de undo e das dimensoes
// correntes do facade (que estas operacoes podem alterar).
struct EngineStateContext {
    DocumentContext          doc;
    canvas::PixelBuffer&     displayBuffer;
    raster::SelectionMask&   selectionMask;
    canvas::TileUndoManager& undoManager;
    int&                     width;
    int&                     height;
};

// Orquestrador de estado do documento: redimensionamento de canvas, limpeza,
// transacoes de camada e undo/redo.
//
// Extraido de PaintEngineFacade.cpp (Achado #6). O que unifica estes metodos e'
// que todos podem trocar a geometria por baixo do facade -- e por isso todos
// passam por syncHistoryGeometry(), que e' o unico ponto autorizado a
// reconstruir buffers e compositor quando a pilha restaurada tem dimensoes
// diferentes das atuais.
class DocumentStateOrchestrator {
public:
    static void resizeCanvas(const EngineStateContext& ctx, int width, int height);
    static void clearCanvas(const DocumentContext& doc);

    // Reconstroi buffers/compositor quando a pilha de camadas passou a ter
    // dimensoes diferentes das do facade (restauracao de historico). No-op
    // quando as dimensoes ja batem.
    static void syncHistoryGeometry(const EngineStateContext& ctx);

    static bool cancelLayerTransaction(const EngineStateContext& ctx);
    static bool applyPreparedGeometry(
        const EngineStateContext& ctx,
        const document::LayerStack& preparedStack,
        const raster::SelectionMask& preparedSelection
    );
    static bool undo(const EngineStateContext& ctx);
    static bool redo(const EngineStateContext& ctx);
};

} // namespace aladyn::engine::boundary::internal
