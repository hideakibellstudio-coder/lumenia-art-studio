#include "CompositeRegionSupport.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::document::internal {

int filterSpatialReach(const FilterLayer& filter) {
    switch (filter.getFilterType()) {
        case FilterType::GaussianBlur: {
            return std::clamp(static_cast<int>(filter.getParam(0, 10.0f)), 1, 100);
        }
        case FilterType::SharpenVignette: {
            const float sharpen = std::clamp(filter.getParam(0, 25.0f) / 100.0f, 0.0f, 1.0f);
            return (sharpen > 0.001f) ? 1 : 0;
        }
        case FilterType::Pixelate: {
            return std::clamp(static_cast<int>(filter.getParam(0, 8.0f)), 2, 64);
        }
        default:
            return 0;
    }
}

const Layer* resolveClipBase(const Layer& layer) {
    return layer.isClippingMask() ? layer.getClipBase() : nullptr;
}

const Layer* getIsolatedGroupAncestor(const LayerNode* node) {
    const LayerNode* curr = node ? node->getParent() : nullptr;
    while (curr) {
        if (curr->isGroup() && curr->getBlendMode() != LayerBlendMode::PassThrough) {
            return dynamic_cast<const Layer*>(curr);
        }
        curr = curr->getParent();
    }
    return nullptr;
}

double getRelativeOpacity(const LayerNode* node, const LayerNode* isolatedAncestor) {
    if (!node || !node->isVisible()) return 0.0;
    double op = node->getOpacity();
    const LayerNode* curr = node->getParent();
    while (curr && curr != isolatedAncestor) {
        if (!curr->isVisible()) return 0.0;
        op *= curr->getOpacity();
        curr = curr->getParent();
    }
    return op;
}

BackgroundAndReach computeBackgroundAndReach(
    const std::vector<const Layer*>& layers,
    const utils::ColorRGBA& bgColor
) {
    BackgroundAndReach result;

    bool hasBackground = false;
    for (const Layer* l : layers) {
        if (l && l->isBackground() && l->isVisible()) {
            hasBackground = true;
            break;
        }
    }
    result.bgFill = hasBackground ? bgColor : utils::ColorRGBA{0, 0, 0, 0};

    for (const Layer* l : layers) {
        if (l && l->isFilter() && l->isVisible() && l->getEffectiveOpacity() > 0.0) {
            if (const auto* fl = dynamic_cast<const FilterLayer*>(l)) {
                const int reach = filterSpatialReach(*fl);
                result.totalReach += reach;
                if (fl->getFilterType() == FilterType::Pixelate) {
                    result.maxBlockSize = std::max(result.maxBlockSize, reach);
                }
            }
        }
    }

    return result;
}

RegionBounds computeRegionBounds(
    const utils::Rect2D& region,
    int totalReach,
    int maxBlockSize,
    int canvasWidth,
    int canvasHeight,
    bool snapToBlockSize
) {
    utils::Rect2D effRegion = region;
    if (totalReach > 0) {
        effRegion = utils::Rect2D{
            region.getLeft() - totalReach,
            region.getTop() - totalReach,
            region.width + 2.0 * totalReach,
            region.height + 2.0 * totalReach
        };
    }

    RegionBounds bounds;
    bounds.minX = std::max(0, static_cast<int>(std::floor(effRegion.getLeft())) - 2);
    bounds.maxX = std::min(canvasWidth - 1, static_cast<int>(std::ceil(effRegion.getRight())) + 2);
    bounds.minY = std::max(0, static_cast<int>(std::floor(effRegion.getTop())) - 2);
    bounds.maxY = std::min(canvasHeight - 1, static_cast<int>(std::ceil(effRegion.getBottom())) + 2);

    if (snapToBlockSize && maxBlockSize > 1) {
        bounds.minX = (bounds.minX / maxBlockSize) * maxBlockSize;
        bounds.minY = (bounds.minY / maxBlockSize) * maxBlockSize;
        bounds.maxX = std::min(canvasWidth - 1, ((bounds.maxX / maxBlockSize) + 1) * maxBlockSize - 1);
        bounds.maxY = std::min(canvasHeight - 1, ((bounds.maxY / maxBlockSize) + 1) * maxBlockSize - 1);
    }

    if (bounds.minX > bounds.maxX || bounds.minY > bounds.maxY) {
        bounds.empty = true;
        return bounds;
    }

    bounds.empty = false;
    bounds.regW = bounds.maxX - bounds.minX + 1;
    bounds.regH = bounds.maxY - bounds.minY + 1;
    bounds.startTileX = bounds.minX / canvas::Tile::TILE_SIZE;
    bounds.endTileX   = bounds.maxX / canvas::Tile::TILE_SIZE;
    bounds.startTileY = bounds.minY / canvas::Tile::TILE_SIZE;
    bounds.endTileY   = bounds.maxY / canvas::Tile::TILE_SIZE;
    return bounds;
}

} // namespace aladyn::engine::document::internal
