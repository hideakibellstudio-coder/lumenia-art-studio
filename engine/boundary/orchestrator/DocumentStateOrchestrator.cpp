#include "DocumentStateOrchestrator.hpp"
#include "../../core/canvas/CanvasLimits.hpp"

#include <utility>

namespace aladyn::engine::boundary::orchestrator {

void DocumentStateOrchestrator::resizeCanvas(const EngineStateContext& ctx, int width, int height) {
    // Refuse before touching anything: a canvas outside the limit leaves the document as it was.
    canvas::checkedCanvasDimension(width);
    canvas::checkedCanvasDimension(height);
    ctx.width = width;
    ctx.height = height;
    ctx.doc.layerStack.resize(width, height);
    // Snapshots antigos tem dimensoes incompativeis com a nova grade.
    ctx.undoManager.clear();
    ctx.doc.compositor = document::Compositor(width, height);
    ctx.doc.compositor.setLinearGamma(ctx.doc.linearGamma);
    ctx.doc.compositor.setDeepColor(ctx.doc.deepColor);
    ctx.doc.outputBuffer.resize(width, height, ctx.doc.bgColor);
    ctx.displayBuffer.resize(width, height, ctx.doc.bgColor);
    ctx.selectionMask.resize(width, height);
    ctx.doc.compositeAll();
    ctx.doc.touch();
}

void DocumentStateOrchestrator::clearCanvas(const DocumentContext& doc) {
    auto* active = doc.layerStack.getActiveLayer();
    if (active && !active->isLocked() && !active->isGroup() && !active->isFilter()) {
        active->getTileGrid().clearTiles();
        doc.compositeAll();
        doc.touch();
    }
}

void DocumentStateOrchestrator::syncHistoryGeometry(const EngineStateContext& ctx) {
    const int width = ctx.doc.layerStack.getWidth(), height = ctx.doc.layerStack.getHeight();
    if (width == ctx.width && height == ctx.height) return;
    canvas::PixelBuffer output(width, height, ctx.doc.bgColor);
    canvas::PixelBuffer display(width, height, ctx.doc.bgColor);
    document::Compositor compositor(width, height);
    compositor.setLinearGamma(ctx.doc.linearGamma);
    compositor.setDeepColor(ctx.doc.deepColor);
    ctx.doc.outputBuffer = std::move(output);
    ctx.displayBuffer = std::move(display);
    ctx.doc.compositor = std::move(compositor);
    ctx.width = width;
    ctx.height = height;
    ctx.doc.mipmapPyramid.markDirty();
}

bool DocumentStateOrchestrator::cancelLayerTransaction(const EngineStateContext& ctx) {
    if (!ctx.undoManager.cancelStructure(ctx.doc.layerStack, ctx.selectionMask)) return false;
    syncHistoryGeometry(ctx);
    ctx.doc.compositeAll();
    ctx.doc.touch();
    return true;
}

bool DocumentStateOrchestrator::applyPreparedGeometry(
    const EngineStateContext& ctx,
    const document::LayerStack& preparedStack,
    const selection::SelectionMask& preparedSelection
) {
    if (!ctx.undoManager.recordingStructure()) return false;
    // Mantem este facade (estado de pincel, guias e todo o historico anterior).
    // So adota a pilha de camadas validada e a selecao que vieram prontas.
    auto selection = preparedSelection;
    ctx.doc.layerStack.restore(preparedStack);
    ctx.selectionMask = std::move(selection);
    syncHistoryGeometry(ctx);
    ctx.doc.compositeAll();
    ctx.doc.touch();
    return true;
}

bool DocumentStateOrchestrator::undo(const EngineStateContext& ctx) {
    const bool ok = ctx.undoManager.undo(ctx.doc.layerStack, ctx.selectionMask);
    if (ok) {
        syncHistoryGeometry(ctx);
        ctx.doc.touch();
        if (auto* layer = ctx.doc.layerStack.getActiveLayer()) {
            layer->getTileGrid().pruneEmptyTiles();
        }
        ctx.doc.compositeAll();
    }
    return ok;
}

bool DocumentStateOrchestrator::redo(const EngineStateContext& ctx) {
    const bool ok = ctx.undoManager.redo(ctx.doc.layerStack, ctx.selectionMask);
    if (ok) {
        syncHistoryGeometry(ctx);
        ctx.doc.touch();
        if (auto* layer = ctx.doc.layerStack.getActiveLayer()) {
            layer->getTileGrid().pruneEmptyTiles();
        }
        ctx.doc.compositeAll();
    }
    return ok;
}

} // namespace aladyn::engine::boundary::orchestrator
