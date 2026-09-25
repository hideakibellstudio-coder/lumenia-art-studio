#pragma once

#include "DocumentContext.hpp"
#include "LayerDirtyRegion.hpp"
#include "../../core/document/FilterLayer.hpp"
#include <string>
#include <vector>

namespace aladyn::engine::boundary::orchestrator {

// Orquestrador das mutacoes da pilha de camadas.
//
// Contrato: cada metodo aplica a mutacao, recompoe o que precisa ser recomposto
// e marca o documento como alterado (ctx.touch()) exatamente nos mesmos casos em
// que o PaintEngineFacade marcava antes -- isto e, so em sucesso para as
// operacoes estruturais, e incondicionalmente para os setters de propriedade
// (que era o comportamento historico do facade).
//
// O calculo de regiao suja usado pelos setters puramente visuais vive em
// LayerDirtyRegion (ver Achado #1 da auditoria de camadas).
class LayerStackOrchestrator {
public:
    // ─── Operacoes estruturais ────────────────────────────────────────────
    static int addLayer(const DocumentContext& ctx, const std::string& name, int insertIndex = -1) {
        const int idx = ctx.layerStack.addLayer(name, insertIndex);
        ctx.compositeAll();
        if (idx >= 0) ctx.touch();
        return idx;
    }

    static int addGroup(const DocumentContext& ctx, const std::string& name, int insertIndex = -1) {
        const int idx = ctx.layerStack.addGroup(name, insertIndex);
        ctx.compositeAll();
        if (idx >= 0) ctx.touch();
        return idx;
    }

    static int addFilterLayer(const DocumentContext& ctx, const std::string& name, int filterTypeId, int insertIndex = -1) {
        const int idx = ctx.layerStack.addFilterLayer(name, static_cast<document::FilterType>(filterTypeId), insertIndex);
        ctx.compositeAll();
        if (idx >= 0) ctx.touch();
        return idx;
    }

    static bool removeLayer(const DocumentContext& ctx, int index) {
        const bool ok = ctx.layerStack.removeLayer(index);
        if (ok) { ctx.compositeAll(); ctx.touch(); }
        return ok;
    }

    static int duplicateLayer(const DocumentContext& ctx, int index) {
        const int idx = ctx.layerStack.duplicateLayer(index);
        if (idx >= 0) { ctx.compositeAll(); ctx.touch(); }
        return idx;
    }

    static bool reorderLayer(const DocumentContext& ctx, int fromIdx, int toIdx) {
        const bool ok = ctx.layerStack.reorderLayer(fromIdx, toIdx);
        if (ok) { ctx.compositeAll(); ctx.touch(); }
        return ok;
    }

    static bool reorderLayers(const DocumentContext& ctx, const std::vector<int>& newOrder) {
        const bool ok = ctx.layerStack.reorderLayers(newOrder);
        if (ok) { ctx.compositeAll(); ctx.touch(); }
        return ok;
    }

    static bool setLayerParents(const DocumentContext& ctx, const std::vector<int>& parents) {
        const bool ok = ctx.layerStack.setLayerParents(parents);
        if (ok) { ctx.compositeAll(); ctx.touch(); }
        return ok;
    }

    static bool flattenGroup(const DocumentContext& ctx, int index) {
        const bool ok = ctx.layerStack.flattenGroup(index, ctx.linearGamma, ctx.deepColor);
        if (ok) { ctx.compositeAll(); ctx.touch(); }
        return ok;
    }

    static bool mergeLayerDown(const DocumentContext& ctx, int index) {
        const bool ok = ctx.layerStack.mergeLayerDown(index, ctx.linearGamma, ctx.deepColor);
        if (ok) { ctx.compositeAll(); ctx.touch(); }
        return ok;
    }

    static bool setGroupPassThrough(const DocumentContext& ctx, int index, bool passThrough) {
        const bool ok = ctx.layerStack.setGroupPassThrough(index, passThrough);
        if (ok) { ctx.compositeAll(); ctx.touch(); }
        return ok;
    }

    // ─── Setters puramente visuais (composicao por regiao suja) ───────────
    static void setLayerOpacity(const DocumentContext& ctx, int index, double opacity) {
        if (auto* l = ctx.layerStack.getDrawingLayer(index)) {
            l->setOpacity(opacity);
            ctx.compositeRegion(LayerDirtyRegion::computeLayerVisualDirtyRegion(ctx.layerStack, index));
        }
        ctx.touch();
    }

    static void setLayerBlendMode(const DocumentContext& ctx, int index, int blendModeId) {
        if (auto* l = ctx.layerStack.getDrawingLayer(index)) {
            l->setBlendMode(static_cast<document::LayerBlendMode>(blendModeId));
            ctx.compositeRegion(LayerDirtyRegion::computeLayerVisualDirtyRegion(ctx.layerStack, index));
        }
        ctx.touch();
    }

    static void setLayerVisibility(const DocumentContext& ctx, int index, bool visible) {
        if (auto* l = ctx.layerStack.getDrawingLayer(index)) {
            l->setVisible(visible);
            ctx.compositeRegion(LayerDirtyRegion::computeLayerVisualDirtyRegion(ctx.layerStack, index));
        }
        ctx.touch();
    }

    static void setLayerClippingMask(const DocumentContext& ctx, int index, bool clipped) {
        if (auto* l = ctx.layerStack.getDrawingLayer(index)) {
            l->setClippingMask(clipped);
            ctx.compositeRegion(LayerDirtyRegion::computeLayerVisualDirtyRegion(ctx.layerStack, index));
        }
        ctx.touch();
    }

    // ─── Propriedades sem efeito visual (nao recompoem) ───────────────────
    static void setLayerLock(const DocumentContext& ctx, int index, bool locked) {
        if (auto* l = ctx.layerStack.getDrawingLayer(index)) { l->setLocked(locked); ctx.touch(); }
    }

    static void setLayerAlphaLock(const DocumentContext& ctx, int index, bool locked) {
        if (auto* l = ctx.layerStack.getDrawingLayer(index)) { l->setAlphaLocked(locked); ctx.touch(); }
    }

    static void clearLayer(const DocumentContext& ctx, int index) {
        if (auto* l = ctx.layerStack.getDrawingLayer(index)) {
            l->getTileGrid().clearTiles();
            ctx.compositeAll();
        }
        ctx.touch();
    }

    // ─── Camadas de filtro ────────────────────────────────────────────────
    static void setFilterParams(const DocumentContext& ctx, int index, const std::vector<float>& params) {
        auto* l = ctx.layerStack.getDrawingLayer(index);
        if (auto* fl = dynamic_cast<document::FilterLayer*>(l)) {
            for (size_t i = 0; i < params.size(); ++i) fl->setParam(i, params[i]);
            ctx.compositeAll();
            ctx.touch();
        }
    }

    static std::vector<float> getFilterParams(const document::LayerStack& stack, int index) {
        const auto* l = stack.getDrawingLayer(index);
        if (const auto* fl = dynamic_cast<const document::FilterLayer*>(l)) {
            std::vector<float> p;
            for (size_t i = 0; i < 4; ++i) p.push_back(fl->getParam(i, 0.0f));
            return p;
        }
        return {};
    }

    static int getFilterType(const document::LayerStack& stack, int index) {
        const auto* l = stack.getDrawingLayer(index);
        if (const auto* fl = dynamic_cast<const document::FilterLayer*>(l)) return static_cast<int>(fl->getFilterType());
        return 0;
    }
};

} // namespace aladyn::engine::boundary::orchestrator
