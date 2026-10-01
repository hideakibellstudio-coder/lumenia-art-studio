#include "Compositor.hpp"
#include "FilterLayer.hpp"
#include "CompositeRegionSupport.hpp"
#include "blending/BlendEquations.hpp"
#include "filters/FilterApplier.hpp"

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

// compositeRegion/compositeRegionWithScratch delegam o calculo de limites de
// regiao e o par blendGroupToDestination/composeTileGrid para
// internal::CompositeRegionSupport (ver esse arquivo) — as duas sobrecargas
// duplicavam esse bloco byte a byte (Achado "Compositor.cpp estourou o teto
// de LOC" do panorama de camadas de 2026-09-19). `snapToBlockSize` e
// `parallelRowThreshold` preservam as duas divergencias de comportamento que
// ja existiam entre as sobrecargas antes desta extracao.
void Compositor::compositeRegion(
    const std::vector<const Layer*>& layers,
    const utils::Rect2D& region,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor
) {
    if (layers.empty()) return;

    const auto bgReach = internal::computeBackgroundAndReach(layers, bgColor);
    const auto bounds = internal::computeRegionBounds(
        region, bgReach.totalReach, bgReach.maxBlockSize, m_width, m_height, /*snapToBlockSize=*/true);
    if (bounds.empty) return;
    m_damage.add(bounds.minX, bounds.minY, bounds.maxX + 1, bounds.maxY + 1);

    internal::fillBackground(outputBuffer, bounds, bgReach.bgFill, m_width, m_height, /*parallelRowThreshold=*/32);

    internal::GroupBlender blender(outputBuffer, bounds, m_linearGamma, m_deepColor);
    const Layer* activeGroup = nullptr;

    for (const Layer* layerPtr : layers) {
        if (!layerPtr || !layerPtr->isVisible() || layerPtr->getEffectiveOpacity() <= 0.0) {
            continue;
        }

        const Layer* isoGroup = internal::getIsolatedGroupAncestor(layerPtr);
        if (isoGroup != activeGroup) {
            if (activeGroup != nullptr) {
                blender.blendGroupToDestination(activeGroup);
            }
            if (isoGroup != nullptr) {
                blender.beginGroup();
            }
            activeGroup = isoGroup;
        }

        if (layerPtr->isFilter()) {
            const FilterLayer* filterLayer = dynamic_cast<const FilterLayer*>(layerPtr);
            if (filterLayer) {
                if (activeGroup != nullptr) {
                    blender.applyFilterToGroup(*filterLayer);
                } else {
                    applyFilterToBuffer(*filterLayer, outputBuffer, bounds.minX, bounds.maxX, bounds.minY, bounds.maxY);
                }
            }
            continue;
        }

        const Layer& layer = *layerPtr;
        const double layerOpacity = activeGroup ? internal::getRelativeOpacity(&layer, activeGroup) : layer.getEffectiveOpacity();
        const LayerBlendMode blendMode = layer.getBlendMode();
        const Layer* clipBaseLayer = internal::resolveClipBase(layer);

        blender.composeTileGrid(layer.getTileGrid(), layerOpacity, blendMode, clipBaseLayer, activeGroup != nullptr);
    }

    if (activeGroup != nullptr) {
        blender.blendGroupToDestination(activeGroup);
    }
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
    if (layers.empty()) return;

    const auto bgReach = internal::computeBackgroundAndReach(layers, bgColor);
    const auto bounds = internal::computeRegionBounds(
        region, bgReach.totalReach, bgReach.maxBlockSize, m_width, m_height, /*snapToBlockSize=*/false);
    if (bounds.empty) return;
    m_damage.add(bounds.minX, bounds.minY, bounds.maxX + 1, bounds.maxY + 1);

    internal::fillBackground(outputBuffer, bounds, bgReach.bgFill, m_width, m_height, /*parallelRowThreshold=*/64);

    internal::GroupBlender blender(outputBuffer, bounds, m_linearGamma, m_deepColor);
    const Layer* activeGroup = nullptr;

    for (const Layer* layerPtr : layers) {
        if (!layerPtr || !layerPtr->isVisible() || layerPtr->getEffectiveOpacity() <= 0.0) {
            continue;
        }

        const Layer* isoGroup = internal::getIsolatedGroupAncestor(layerPtr);
        if (isoGroup != activeGroup) {
            if (activeGroup != nullptr) {
                blender.blendGroupToDestination(activeGroup);
            }
            if (isoGroup != nullptr) {
                blender.beginGroup();
            }
            activeGroup = isoGroup;
        }

        if (layerPtr->isFilter()) {
            const FilterLayer* filterLayer = dynamic_cast<const FilterLayer*>(layerPtr);
            if (filterLayer) {
                if (activeGroup != nullptr) {
                    blender.applyFilterToGroup(*filterLayer);
                } else {
                    applyFilterToBuffer(*filterLayer, outputBuffer, bounds.minX, bounds.maxX, bounds.minY, bounds.maxY);
                }
            }
            continue;
        }

        const Layer& layer = *layerPtr;
        const double layerOpacity = activeGroup ? internal::getRelativeOpacity(&layer, activeGroup) : layer.getEffectiveOpacity();
        const LayerBlendMode blendMode = layer.getBlendMode();
        const Layer* clipBaseLayer = internal::resolveClipBase(layer);

        blender.composeTileGrid(layer.getTileGrid(), layerOpacity, blendMode, clipBaseLayer, activeGroup != nullptr);

        if (layerPtr == activeLayerTarget && scratchOpacity > 0.0) {
            blender.composeTileGrid(scratchGrid, scratchOpacity, scratchBlendMode, clipBaseLayer, activeGroup != nullptr);
        }
    }

    if (activeGroup != nullptr) {
        blender.blendGroupToDestination(activeGroup);
    }
}

} // namespace aladyn::engine::document
