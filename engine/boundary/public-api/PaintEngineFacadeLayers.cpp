#include "PaintEngineFacade.hpp"
#include "../orchestrator/DocumentContext.hpp"
#include "../orchestrator/LayerStackOrchestrator.hpp"

namespace aladyn::engine::boundary {

// ─── GERENCIAMENTO DE CAMADAS ─────────────────────────────────────────────

int PaintEngineFacade::addLayer(const std::string& name, int insertIndex) { return orchestrator::LayerStackOrchestrator::addLayer(docContext(), name, insertIndex); }
int PaintEngineFacade::addGroup(const std::string& name, int insertIndex) { return orchestrator::LayerStackOrchestrator::addGroup(docContext(), name, insertIndex); }
int PaintEngineFacade::addFilterLayer(const std::string& name, int filterTypeId, int insertIndex) { return orchestrator::LayerStackOrchestrator::addFilterLayer(docContext(), name, filterTypeId, insertIndex); }
bool PaintEngineFacade::removeLayer(int index) { return orchestrator::LayerStackOrchestrator::removeLayer(docContext(), index); }
int PaintEngineFacade::duplicateLayer(int index) { return orchestrator::LayerStackOrchestrator::duplicateLayer(docContext(), index); }
bool PaintEngineFacade::reorderLayer(int fromIndex, int toIndex) { return orchestrator::LayerStackOrchestrator::reorderLayer(docContext(), fromIndex, toIndex); }
bool PaintEngineFacade::reorderLayers(const std::vector<int>& newOrder) { return orchestrator::LayerStackOrchestrator::reorderLayers(docContext(), newOrder); }
bool PaintEngineFacade::setLayerParents(const std::vector<int>& parentIndices) { return orchestrator::LayerStackOrchestrator::setLayerParents(docContext(), parentIndices); }
bool PaintEngineFacade::flattenGroup(int index) { return orchestrator::LayerStackOrchestrator::flattenGroup(docContext(), index); }
bool PaintEngineFacade::mergeLayerDown(int index) { return orchestrator::LayerStackOrchestrator::mergeLayerDown(docContext(), index); }
bool PaintEngineFacade::setGroupPassThrough(int index, bool passThrough) { return orchestrator::LayerStackOrchestrator::setGroupPassThrough(docContext(), index, passThrough); }
void PaintEngineFacade::clearLayer(int index) { orchestrator::LayerStackOrchestrator::clearLayer(docContext(), index); }

void PaintEngineFacade::setLayerName(int index, const std::string& name) {
    if (auto* l = m_layerStack.getDrawingLayer(index)) { l->setName(name); touchDocument(); }
}

std::string PaintEngineFacade::getLayerName(int index) const {
    const auto* l = m_layerStack.getDrawingLayer(index); return l ? l->getName() : std::string{};
}

void PaintEngineFacade::setLayerOpacity(int index, double opacity) { orchestrator::LayerStackOrchestrator::setLayerOpacity(docContext(), index, opacity); }
void PaintEngineFacade::setLayerBlendMode(int index, int blendModeId) { orchestrator::LayerStackOrchestrator::setLayerBlendMode(docContext(), index, blendModeId); }
void PaintEngineFacade::setLayerVisibility(int index, bool visible) { orchestrator::LayerStackOrchestrator::setLayerVisibility(docContext(), index, visible); }
void PaintEngineFacade::setLayerClippingMask(int index, bool clipped) { orchestrator::LayerStackOrchestrator::setLayerClippingMask(docContext(), index, clipped); }

bool PaintEngineFacade::isLayerClippingMask(int index) const noexcept {
    const auto* l = m_layerStack.getDrawingLayer(index); return l ? l->isClippingMask() : false;
}

void PaintEngineFacade::setLayerLock(int index, bool locked) { orchestrator::LayerStackOrchestrator::setLayerLock(docContext(), index, locked); }
void PaintEngineFacade::setLayerAlphaLock(int index, bool locked) { orchestrator::LayerStackOrchestrator::setLayerAlphaLock(docContext(), index, locked); }

bool PaintEngineFacade::isLayerAlphaLocked(int index) const noexcept {
    const auto* l = m_layerStack.getDrawingLayer(index); return l ? l->isAlphaLocked() : false;
}

void PaintEngineFacade::setFilterParams(int index, const std::vector<float>& params) { orchestrator::LayerStackOrchestrator::setFilterParams(docContext(), index, params); }
std::vector<float> PaintEngineFacade::getFilterParams(int index) const { return orchestrator::LayerStackOrchestrator::getFilterParams(m_layerStack, index); }
int PaintEngineFacade::getFilterType(int index) const { return orchestrator::LayerStackOrchestrator::getFilterType(m_layerStack, index); }

// ─── MÁSCARA DE CAMADA (S9) ──────────────────────────────────────────────

bool PaintEngineFacade::addLayerMask(int index) { return orchestrator::LayerStackOrchestrator::addLayerMask(docContext(), index); }
bool PaintEngineFacade::removeLayerMask(int index) { return orchestrator::LayerStackOrchestrator::removeLayerMask(docContext(), index); }
bool PaintEngineFacade::hasLayerMask(int index) const noexcept { return orchestrator::LayerStackOrchestrator::hasLayerMask(m_layerStack, index); }
void PaintEngineFacade::setLayerMaskEnabled(int index, bool enabled) { orchestrator::LayerStackOrchestrator::setLayerMaskEnabled(docContext(), index, enabled); }
bool PaintEngineFacade::isLayerMaskEnabled(int index) const noexcept { return orchestrator::LayerStackOrchestrator::isLayerMaskEnabled(m_layerStack, index); }
void PaintEngineFacade::setLayerMaskEditTarget(int index, bool targetMask) { orchestrator::LayerStackOrchestrator::setLayerMaskEditTarget(docContext(), index, targetMask); }
bool PaintEngineFacade::isLayerMaskEditTarget(int index) const noexcept { return orchestrator::LayerStackOrchestrator::isLayerMaskEditTarget(m_layerStack, index); }

} // namespace aladyn::engine::boundary
