#include "LayerCompositePass.hpp"
#include "filters/FilterApplier.hpp"

namespace aladyn::engine::document::internal {

LayerCompositePass::LayerCompositePass(
    canvas::PixelBuffer& outputBuffer, const RegionBounds& bounds, bool linearGamma, bool deepColor
)
    : m_outputBuffer(outputBuffer), m_bounds(bounds), m_blender(outputBuffer, bounds, linearGamma, deepColor) {}

void LayerCompositePass::add(const Layer* layer, const ScratchOverlay* scratch) {
    if (!layer || !layer->isVisible() || layer->getEffectiveOpacity() <= 0.0) return;

    enterGroupOf(layer);
    if (layer->isFilter()) {
        if (const auto* filter = dynamic_cast<const FilterLayer*>(layer)) applyFilter(*filter);
        return;
    }
    composeLayer(*layer, scratch);
}

void LayerCompositePass::finish() {
    if (m_activeGroup != nullptr) m_blender.blendGroupToDestination(m_activeGroup);
}

// Ao mudar de grupo isolado, funde o anterior no destino e abre o novo.
void LayerCompositePass::enterGroupOf(const Layer* layer) {
    const Layer* isolatedGroup = getIsolatedGroupAncestor(layer);
    if (isolatedGroup == m_activeGroup) return;
    if (m_activeGroup != nullptr) m_blender.blendGroupToDestination(m_activeGroup);
    if (isolatedGroup != nullptr) m_blender.beginGroup();
    m_activeGroup = isolatedGroup;
}

void LayerCompositePass::applyFilter(const FilterLayer& filter) {
    if (m_activeGroup != nullptr) {
        m_blender.applyFilterToGroup(filter);
    } else {
        filters::FilterApplier::apply(filter.settings(), m_outputBuffer, m_bounds.minX, m_bounds.maxX, m_bounds.minY, m_bounds.maxY);
    }
}

void LayerCompositePass::composeLayer(const Layer& layer, const ScratchOverlay* scratch) {
    const bool toGroup = m_activeGroup != nullptr;
    const double opacity = toGroup ? getRelativeOpacity(&layer, m_activeGroup) : layer.getEffectiveOpacity();
    const Layer* clipBase = resolveClipBase(layer);

    m_blender.composeTileGrid(layer.getTileGrid(), opacity, layer.getBlendMode(), clipBase, toGroup);

    if (scratch != nullptr && &layer == scratch->target && scratch->opacity > 0.0) {
        m_blender.composeTileGrid(scratch->grid, scratch->opacity, scratch->mode, clipBase, toGroup);
    }
}

} // namespace aladyn::engine::document::internal
