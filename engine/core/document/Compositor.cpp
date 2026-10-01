#include "Compositor.hpp"
#include "FilterLayer.hpp"
#include "CompositeRegionSupport.hpp"
#include "LayerCompositePass.hpp"
#include "blending/BlendEquations.hpp"
#include "filters/FilterApplier.hpp"
#include <optional>

namespace aladyn::engine::document {

Compositor::Compositor(int width, int height)
    : m_width(width), m_height(height) {}

utils::ColorRGBA Compositor::blendPixel(
    utils::ColorRGBA src,
    double layerOpacity,
    utils::ColorRGBA dst,
    LayerBlendMode mode
) {
    return blending::blendPixel(src, layerOpacity, dst, mode, true, false);
}

utils::ColorRGBA Compositor::blendPixel(
    utils::ColorRGBA src,
    double layerOpacity,
    utils::ColorRGBA dst,
    LayerBlendMode mode,
    bool linearGamma,
    bool deepColor
) {
    return blending::blendPixel(src, layerOpacity, dst, mode, linearGamma, deepColor);
}

void Compositor::applyFilterToBuffer(
    const FilterLayer& filter,
    canvas::PixelBuffer& buffer,
    int minX, int maxX, int minY, int maxY
) {
    filters::FilterApplier::apply(filter.settings(), buffer, minX, maxX, minY, maxY);
}

void Compositor::composite(
    const std::vector<const Layer*>& layers,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor
) {
    compositeRegion(
        layers,
        utils::Rect2D{0, 0, static_cast<double>(m_width), static_cast<double>(m_height)},
        outputBuffer,
        bgColor
    );
}

void Compositor::composite(
    const std::vector<std::unique_ptr<Layer>>& layers,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor
) {
    std::vector<const Layer*> rawPtrs;
    rawPtrs.reserve(layers.size());
    for (const auto& l : layers) {
        if (l) rawPtrs.push_back(l.get());
    }
    composite(rawPtrs, outputBuffer, bgColor);
}

// As duas sobrecargas de região compartilham `compositeLayers`; o que sempre as distinguiu
// (alinhar a região ao bloco de pixelize, o limiar de paralelização do fundo e o overlay do
// traço ativo) chega como `CompositePolicy` e `ScratchOverlay`. O alcance dos limites e o par
// grupo/tile moram em `internal::CompositeRegionSupport`, e o laço sobre as camadas em
// `internal::LayerCompositePass`.
void Compositor::compositeLayers(
    const std::vector<const Layer*>& layers,
    const utils::Rect2D& region,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor,
    const internal::CompositePolicy& policy,
    const internal::ScratchOverlay* scratch
) {
    if (layers.empty()) return;

    const auto bgReach = internal::computeBackgroundAndReach(layers, bgColor);
    const int reach = bgReach.totalReach;

    // Um filtro de area espalha uma mudanca por `reach` pixels em volta: essa e' a area que muda (`inner`).
    // Para calcula-la certo o filtro precisa dos vizinhos de cada pixel dela, mais `reach` para fora (`bounds`).
    // Os pixels dessa ultima faixa saem errados do filtro (faltam vizinhos) e nao podem ficar no buffer de saida:
    // a faixa e' devolvida como estava (ate 2026-10-01 ela era escrita, e a tela mostrava uma composicao
    // diferente da inteira ate a proxima recomposicao total).
    const auto bounds = internal::computeRegionBounds(
        region, 2 * reach, bgReach.maxBlockSize, m_width, m_height, policy.snapToBlockSize);
    if (bounds.empty) return;
    const auto inner = reach > 0
        ? internal::computeRegionBounds(region, reach, bgReach.maxBlockSize, m_width, m_height, policy.snapToBlockSize)
        : bounds;
    if (inner.empty) return;
    std::optional<internal::RegionMargin> margin;
    if (reach > 0) margin.emplace(outputBuffer, bounds, inner);
    m_damage.add(inner.minX, inner.minY, inner.maxX + 1, inner.maxY + 1);

    internal::fillBackground(outputBuffer, bounds, bgReach.bgFill, m_width, m_height, policy.parallelRowThreshold);

    internal::LayerCompositePass pass(outputBuffer, bounds, m_linearGamma, m_deepColor);
    for (const Layer* layer : layers) pass.add(layer, scratch);
    pass.finish();
    if (margin) margin->restore();
}

void Compositor::compositeRegion(
    const std::vector<const Layer*>& layers,
    const utils::Rect2D& region,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor
) {
    compositeLayers(layers, region, outputBuffer, bgColor, internal::CompositePolicy{/*snapToBlockSize=*/true, /*parallelRowThreshold=*/32}, nullptr);
}

void Compositor::compositeRegion(
    const std::vector<std::unique_ptr<Layer>>& layers,
    const utils::Rect2D& region,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor
) {
    std::vector<const Layer*> rawPtrs;
    rawPtrs.reserve(layers.size());
    for (const auto& l : layers) {
        if (l) rawPtrs.push_back(l.get());
    }
    compositeRegion(rawPtrs, region, outputBuffer, bgColor);
}

void Compositor::compositeRegionWithScratch(
    const std::vector<const Layer*>& layers,
    const utils::Rect2D& region,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor,
    const canvas::TileGrid& scratchGrid,
    const Layer* activeLayerTarget,
    LayerBlendMode scratchBlendMode,
    double scratchOpacity
) {
    const internal::ScratchOverlay scratch{scratchGrid, activeLayerTarget, scratchBlendMode, scratchOpacity};
    compositeLayers(layers, region, outputBuffer, bgColor, internal::CompositePolicy{/*snapToBlockSize=*/false, /*parallelRowThreshold=*/64}, &scratch);
}

} // namespace aladyn::engine::document
