#include "CompositeRegionSupport.hpp"
#include "../blending/BlendEquations.hpp"
#include "../blending/FilterApplier.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>

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
    const raster::ColorRGBA& bgColor
) {
    BackgroundAndReach result;

    bool hasBackground = false;
    for (const Layer* l : layers) {
        if (l && l->isBackground() && l->isVisible()) {
            hasBackground = true;
            break;
        }
    }
    result.bgFill = hasBackground ? bgColor : raster::ColorRGBA{0, 0, 0, 0};

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
    const math::Rect2D& region,
    int totalReach,
    int maxBlockSize,
    int canvasWidth,
    int canvasHeight,
    bool snapToBlockSize
) {
    math::Rect2D effRegion = region;
    if (totalReach > 0) {
        effRegion = math::Rect2D{
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

void fillBackground(
    canvas::PixelBuffer& outputBuffer,
    const RegionBounds& bounds,
    const raster::ColorRGBA& bgFill,
    int canvasWidth,
    int canvasHeight,
    int parallelRowThreshold
) {
    const uint32_t bg32 = (static_cast<uint32_t>(bgFill.a) << 24) |
                          (static_cast<uint32_t>(bgFill.b) << 16) |
                          (static_cast<uint32_t>(bgFill.g) << 8)  |
                           static_cast<uint32_t>(bgFill.r);
    uint32_t* outData32 = reinterpret_cast<uint32_t*>(outputBuffer.getData());
    const int outStride = outputBuffer.getWidth();

    if (bounds.minX == 0 && bounds.maxX == canvasWidth - 1 &&
        bounds.minY == 0 && bounds.maxY == canvasHeight - 1 && bg32 == 0) {
        std::memset(outData32, 0, static_cast<size_t>(canvasWidth) * canvasHeight * 4);
        return;
    }

    #pragma omp parallel for schedule(static) if((bounds.maxY - bounds.minY) > parallelRowThreshold)
    for (int y = bounds.minY; y <= bounds.maxY; ++y) {
        std::fill_n(outData32 + (static_cast<size_t>(y) * outStride + bounds.minX), bounds.maxX - bounds.minX + 1, bg32);
    }
}

GroupBlender::GroupBlender(canvas::PixelBuffer& outputBuffer, const RegionBounds& bounds, bool linearGamma, bool deepColor)
    : m_outputBuffer(outputBuffer),
      m_bounds(bounds),
      m_linearGamma(linearGamma),
      m_deepColor(deepColor),
      m_outData32(reinterpret_cast<uint32_t*>(outputBuffer.getData())),
      m_outStride(outputBuffer.getWidth()) {}

void GroupBlender::beginGroup() {
    const size_t needed = static_cast<size_t>(m_bounds.regW) * m_bounds.regH;
    if (m_groupPixels.size() != needed) {
        m_groupPixels.assign(needed, 0);
    } else {
        std::fill(m_groupPixels.begin(), m_groupPixels.end(), 0);
    }
}

void GroupBlender::composeTileGrid(
    const canvas::TileGrid& grid,
    double opacity,
    LayerBlendMode mode,
    const Layer* clipBase,
    bool isToGroup
) {
    uint32_t* targetData = isToGroup ? m_groupPixels.data() : m_outData32;
    const int targetStride = isToGroup ? m_bounds.regW : m_outStride;
    const int targetOffsetX = isToGroup ? m_bounds.minX : 0;
    const int targetOffsetY = isToGroup ? m_bounds.minY : 0;

    const int maxTilesX = grid.getTilesCountX();
    const int maxTilesY = grid.getTilesCountY();
    const int cSTx = std::clamp(m_bounds.startTileX, 0, maxTilesX - 1);
    const int cETx = std::clamp(m_bounds.endTileX,   0, maxTilesX - 1);
    const int cSTy = std::clamp(m_bounds.startTileY, 0, maxTilesY - 1);
    const int cETy = std::clamp(m_bounds.endTileY,   0, maxTilesY - 1);

    #pragma omp parallel for schedule(static) if((cETy - cSTy) >= 2)
    for (int ty = cSTy; ty <= cETy; ++ty) {
        for (int tx = cSTx; tx <= cETx; ++tx) {
            const canvas::Tile* tile = const_cast<canvas::TileGrid&>(grid).getTile(tx, ty);
            if (!tile) continue;

            const canvas::PixelBuffer& tileBuf = tile->getBuffer();
            const int tilePixelX = tile->getPixelX();
            const int tilePixelY = tile->getPixelY();

            const int tileMinX = std::max(m_bounds.minX, tilePixelX);
            const int tileMaxX = std::min(m_bounds.maxX, tilePixelX + canvas::Tile::TILE_SIZE - 1);
            const int tileMinY = std::max(m_bounds.minY, tilePixelY);
            const int tileMaxY = std::min(m_bounds.maxY, tilePixelY + canvas::Tile::TILE_SIZE - 1);

            for (int globalY = tileMinY; globalY <= tileMaxY; ++globalY) {
                const int localY = globalY - tilePixelY;
                const raster::ColorRGBA* srcRow = reinterpret_cast<const raster::ColorRGBA*>(tileBuf.getData()) + (localY * canvas::Tile::TILE_SIZE);
                raster::ColorRGBA* dstRow = reinterpret_cast<raster::ColorRGBA*>(targetData) + static_cast<size_t>(globalY - targetOffsetY) * targetStride;

                for (int globalX = tileMinX; globalX <= tileMaxX; ++globalX) {
                    const int localX = globalX - tilePixelX;
                    const raster::ColorRGBA src = srcRow[localX];
                    if (src.a == 0) continue;

                    double curOpacity = opacity;
                    if (clipBase) {
                        const int bTx = globalX / canvas::Tile::TILE_SIZE;
                        const int bTy = globalY / canvas::Tile::TILE_SIZE;
                        const int bPx = globalX % canvas::Tile::TILE_SIZE;
                        const int bPy = globalY % canvas::Tile::TILE_SIZE;
                        const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(clipBase->getTileGrid()).getTile(bTx, bTy);
                        if (!bTile) continue;
                        const double baseA = (static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0) * clipBase->getEffectiveOpacity();
                        if (baseA <= 0.0) continue;
                        curOpacity *= baseA;
                    }

                    const int dstX = globalX - targetOffsetX;
                    dstRow[dstX] = blending::blendPixel(src, curOpacity, dstRow[dstX], mode, m_linearGamma, m_deepColor);
                }
            }
        }
    }
}

void GroupBlender::applyFilterToGroup(const FilterLayer& filter) {
    const int regW = m_bounds.regW;
    const int regH = m_bounds.regH;
    canvas::PixelBuffer groupPixelBuf(regW, regH, raster::ColorRGBA{0, 0, 0, 0});
    std::memcpy(groupPixelBuf.getData(), m_groupPixels.data(), static_cast<size_t>(regW) * regH * 4);
    blending::FilterApplier::apply(filter, groupPixelBuf, 0, regW - 1, 0, regH - 1);
    std::memcpy(m_groupPixels.data(), groupPixelBuf.getData(), static_cast<size_t>(regW) * regH * 4);
}

void GroupBlender::blendGroupToDestination(const Layer* group) {
    if (!group || m_groupPixels.empty()) return;
    const double gOpacity = group->getEffectiveOpacity();
    const LayerBlendMode gMode = group->getBlendMode();
    if (gOpacity <= 0.0) return;

    const int regW = m_bounds.regW;
    #pragma omp parallel for schedule(static) if((m_bounds.maxY - m_bounds.minY) > 64)
    for (int y = m_bounds.minY; y <= m_bounds.maxY; ++y) {
        const raster::ColorRGBA* srcRow = reinterpret_cast<const raster::ColorRGBA*>(m_groupPixels.data()) + static_cast<size_t>(y - m_bounds.minY) * regW;
        raster::ColorRGBA* dstRow = reinterpret_cast<raster::ColorRGBA*>(m_outData32) + static_cast<size_t>(y) * m_outStride;
        for (int x = m_bounds.minX; x <= m_bounds.maxX; ++x) {
            const raster::ColorRGBA src = srcRow[x - m_bounds.minX];
            if (src.a == 0) continue;
            dstRow[x] = blending::blendPixel(src, gOpacity, dstRow[x], gMode, m_linearGamma, m_deepColor);
        }
    }
}

} // namespace aladyn::engine::document::internal
