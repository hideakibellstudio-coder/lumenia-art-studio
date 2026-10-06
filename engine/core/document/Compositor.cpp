#include "Compositor.hpp"
#include "FilterLayer.hpp"
#include "CompositeRegionSupport.hpp"
#include "LayerCompositePass.hpp"
#include "RegionBuffer.hpp"
#include "blending/BlendEquations.hpp"
#include "filters/FilterApplier.hpp"
#include <algorithm>
#include <cmath>
#include <optional>
#include <stdexcept>

namespace aladyn::engine::document {

Compositor::Compositor(int width, int height, canvas::PixelFormat format)
    : m_width(width), m_height(height), m_format(format), m_projection(width, height) {}

namespace {

// Os pixels que a região toca, como retângulo inteiro (para a projeção, que é por tile).
// Coordenadas absurdas (retângulo pedido de fora) são cortadas antes da conversão para int.
int clampedPixel(double value) {
    constexpr double kLimit = 1.0e9;
    return static_cast<int>(std::clamp(value, -kLimit, kLimit));
}

projection::PixelRect pixelRectOf(const utils::Rect2D& region) {
    return projection::PixelRect{
        clampedPixel(std::floor(region.getLeft())), clampedPixel(std::floor(region.getTop())),
        clampedPixel(std::ceil(region.getRight())), clampedPixel(std::ceil(region.getBottom()))};
}

utils::Rect2D regionOf(const projection::PixelRect& rect) {
    return utils::Rect2D{static_cast<double>(rect.x0), static_cast<double>(rect.y0), static_cast<double>(rect.x1 - rect.x0),
                         static_cast<double>(rect.y1 - rect.y0)};
}

// Recusa, antes de escrever em qualquer buffer, o que o compositor não sabe ler: uma camada (ou o overlay do traço)
// de formato diferente do documento seria lida como lixo, e o buffer de saída que recebe a tela é sempre de 8 bits.
void requireFormats(
    canvas::PixelFormat format,
    const std::vector<const Layer*>& layers,
    const canvas::PixelBuffer& outputBuffer,
    const internal::ScratchOverlay* scratch
) {
    if (outputBuffer.getFormat() != canvas::PixelFormat::RGBA8)
        throw std::logic_error("compositor: the output buffer is not RGBA8");
    for (const Layer* layer : layers) {
        if (layer && layer->getTileGrid().getFormat() != format)
            throw std::logic_error("compositor: layer pixel format differs from the document's");
    }
    if (scratch != nullptr && scratch->grid.getFormat() != format)
        throw std::logic_error("compositor: stroke overlay pixel format differs from the document's");
}

// Compõe as camadas, de baixo para cima, em `target` (cujo pixel é `Pixel`) dentro de `bounds`.
template <typename Pixel>
void composeLayers(
    canvas::PixelBuffer& target,
    const internal::RegionBounds& bounds,
    const std::vector<const Layer*>& layers,
    const internal::ScratchOverlay* scratch,
    bool linearGamma,
    bool deepColor
) {
    internal::LayerCompositePass<Pixel> pass(target, bounds, linearGamma, deepColor);
    for (const Layer* layer : layers) pass.add(layer, scratch);
    pass.finish();
}

} // namespace

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
    requireFormats(m_format, layers, outputBuffer, scratch);

    // Os tiles velhos que a região toca são refeitos inteiros e ficam frescos: com um pedaço velho para trás
    // um `ensureFresh` posterior (sem o overlay do traço) apagaria a tinta que o traço já pôs ali.
    const utils::Rect2D covered = m_projection.anyStale()
        ? regionOf(m_projection.expandToStale(pixelRectOf(region)))
        : region;
    const auto bgReach = internal::computeBackgroundAndReach(layers, bgColor);
    const int reach = bgReach.totalReach;

    // Um filtro de area espalha uma mudanca por `reach` pixels em volta: essa e' a area que muda (`inner`).
    // Para calcula-la certo o filtro precisa dos vizinhos de cada pixel dela, mais `reach` para fora (`bounds`).
    // Os pixels dessa ultima faixa saem errados do filtro (faltam vizinhos) e nao podem ficar no buffer de saida:
    // a faixa e' devolvida como estava (ate 2026-10-01 ela era escrita, e a tela mostrava uma composicao
    // diferente da inteira ate a proxima recomposicao total).
    const auto bounds = internal::computeRegionBounds(
        covered, 2 * reach, bgReach.maxBlockSize, m_width, m_height, policy.snapToBlockSize);
    if (bounds.empty) return;
    const auto inner = reach > 0
        ? internal::computeRegionBounds(covered, reach, bgReach.maxBlockSize, m_width, m_height, policy.snapToBlockSize)
        : bounds;
    if (inner.empty) return;
    // Num documento de 16 bits as camadas se compõem no buffer interno de 16 bits e só a área pedida (`inner`) é
    // estreitada para o buffer de saída; num de 8 bits o destino é o próprio buffer de saída.
    const bool wide = m_format == canvas::PixelFormat::RGBA16;
    if (wide && !m_composite16) {
        m_composite16 = std::make_unique<canvas::PixelBuffer>(m_width, m_height, canvas::PixelFormat::RGBA16, utils::ColorRGBA{0, 0, 0, 0});
    }
    canvas::PixelBuffer& target = wide ? *m_composite16 : outputBuffer;

    std::optional<internal::RegionMargin> margin;
    if (reach > 0) margin.emplace(target, bounds, inner);
    m_damage.add(inner.minX, inner.minY, inner.maxX + 1, inner.maxY + 1);

    internal::fillBackground(target, bounds, bgReach.bgFill, m_width, m_height, policy.parallelRowThreshold);

    if (wide) {
        composeLayers<utils::ColorRGBA16>(target, bounds, layers, scratch, m_linearGamma, m_deepColor);
    } else {
        composeLayers<utils::ColorRGBA>(target, bounds, layers, scratch, m_linearGamma, m_deepColor);
    }
    if (margin) margin->restore();
    if (wide) internal::narrowRegion(target, outputBuffer, inner);
    m_projection.markFresh(projection::PixelRect{inner.minX, inner.minY, inner.maxX + 1, inner.maxY + 1});
}

void Compositor::invalidate(const std::vector<const Layer*>& layers, const utils::Rect2D& region) {
    if (layers.empty()) return;
    // A mesma área que `compositeRegion(layers, region)` escreveria: a região mais o alcance dos filtros.
    const auto bgReach = internal::computeBackgroundAndReach(layers, utils::ColorRGBA{0, 0, 0, 0});
    const auto inner = internal::computeRegionBounds(
        region, bgReach.totalReach, bgReach.maxBlockSize, m_width, m_height, /*snapToBlockSize=*/true);
    if (inner.empty) return;
    m_projection.markStale(projection::PixelRect{inner.minX, inner.minY, inner.maxX + 1, inner.maxY + 1});
}

void Compositor::ensureFresh(
    const std::vector<const Layer*>& layers,
    const utils::Rect2D& region,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor
) {
    if (!m_projection.anyStale()) return;
    for (const projection::PixelRect& box : m_projection.staleRects(pixelRectOf(region))) {
        compositeRegion(layers, regionOf(box), outputBuffer, bgColor);
        m_projection.markFresh(box);  // sem camadas ou sem área a compor não há o que escrever: fica como está
    }
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
