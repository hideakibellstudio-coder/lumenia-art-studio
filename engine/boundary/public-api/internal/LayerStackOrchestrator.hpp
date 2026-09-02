#pragma once

#include "../../../core/document/LayerStack.hpp"
#include "../../../core/document/Compositor.hpp"
#include "../../../core/canvas/PixelBuffer.hpp"
#include <string>
#include <vector>

namespace aladyn::engine::boundary::internal {

class LayerStackOrchestrator {
public:
    static int addLayer(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, const std::string& name, int insertIndex = -1) {
        int idx = stack.addLayer(name, insertIndex);
        comp.composite(stack.getAllLayersForComposition(), out, bg);
        return idx;
    }

    static int addGroup(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, const std::string& name, int insertIndex = -1) {
        int idx = stack.addGroup(name, insertIndex);
        comp.composite(stack.getAllLayersForComposition(), out, bg);
        return idx;
    }

    static int addFilterLayer(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, const std::string& name, int filterTypeId, int insertIndex = -1) {
        int idx = stack.addFilterLayer(name, static_cast<document::FilterType>(filterTypeId), insertIndex);
        comp.composite(stack.getAllLayersForComposition(), out, bg);
        return idx;
    }

    static bool removeLayer(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, int index) {
        bool ok = stack.removeLayer(index);
        if (ok) comp.composite(stack.getAllLayersForComposition(), out, bg);
        return ok;
    }

    static int duplicateLayer(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, int index) {
        int idx = stack.duplicateLayer(index);
        if (idx >= 0) comp.composite(stack.getAllLayersForComposition(), out, bg);
        return idx;
    }

    static bool reorderLayer(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, int fromIdx, int toIdx) {
        bool ok = stack.reorderLayer(fromIdx, toIdx);
        if (ok) comp.composite(stack.getAllLayersForComposition(), out, bg);
        return ok;
    }

    static bool reorderLayers(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, const std::vector<int>& newOrder) {
        bool ok = stack.reorderLayers(newOrder);
        if (ok) comp.composite(stack.getAllLayersForComposition(), out, bg);
        return ok;
    }

    static bool setLayerParents(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, const std::vector<int>& parents) {
        bool ok = stack.setLayerParents(parents);
        if (ok) comp.composite(stack.getAllLayersForComposition(), out, bg);
        return ok;
    }

    static bool flattenGroup(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, int index) {
        bool ok = stack.flattenGroup(index);
        if (ok) comp.composite(stack.getAllLayersForComposition(), out, bg);
        return ok;
    }

    static bool mergeLayerDown(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, int index) {
        bool ok = stack.mergeLayerDown(index);
        if (ok) comp.composite(stack.getAllLayersForComposition(), out, bg);
        return ok;
    }

    static void setLayerOpacity(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, int index, double opacity) {
        if (auto* l = stack.getDrawingLayer(index)) {
            l->setOpacity(opacity);
            comp.composite(stack.getAllLayersForComposition(), out, bg);
        }
    }

    static void setLayerBlendMode(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, int index, int blendModeId) {
        if (auto* l = stack.getDrawingLayer(index)) {
            l->setBlendMode(static_cast<document::LayerBlendMode>(blendModeId));
            comp.composite(stack.getAllLayersForComposition(), out, bg);
        }
    }

    static void setLayerVisibility(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, int index, bool visible) {
        if (auto* l = stack.getDrawingLayer(index)) {
            l->setVisible(visible);
            comp.composite(stack.getAllLayersForComposition(), out, bg);
        }
    }

    static void setLayerClippingMask(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, int index, bool clipped) {
        if (auto* l = stack.getDrawingLayer(index)) {
            l->setClippingMask(clipped);
            comp.composite(stack.getAllLayersForComposition(), out, bg);
        }
    }

    static void clearLayer(document::LayerStack& stack, document::Compositor& comp, canvas::PixelBuffer& out, const raster::ColorRGBA& bg, int index) {
        if (auto* l = stack.getDrawingLayer(index)) {
            l->getTileGrid().clearTiles();
            comp.composite(stack.getAllLayersForComposition(), out, bg);
        }
    }
};

} // namespace aladyn::engine::boundary::internal
