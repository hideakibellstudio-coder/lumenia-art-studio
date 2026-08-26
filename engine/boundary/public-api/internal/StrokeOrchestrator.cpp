#include "StrokeOrchestrator.hpp"
#include "../../../core/raster/DabInterpolator.hpp"
#include "../../../core/raster/DabRenderer.hpp"
#include "../../../core/raster/PixelContext.hpp"
#include <algorithm>
#include <cmath>
#include <random>

namespace aladyn::engine::boundary::internal {

void StrokeOrchestrator::renderSegment(
    const raster::Dab& startDab,
    const raster::Dab& endDab,
    const brush::BrushProfile& brushProfile,
    const canvas::CanvasTexture& canvasTexture,
    engines::IBrushEngine* activeEngine,
    document::LayerStack& layerStack,
    const raster::SelectionMask& selectionMask,
    canvas::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const raster::ColorRGBA& bgColor,
    double& distanceCarryover,
    const math::SymmetryConfig& symmetryConfig,
    const math::Point2D* strokeStart,
    math::Rect2D* outDirtyBounds
) {
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) {
        return;
    }

    const double maxRadius = std::max(startDab.radius, endDab.radius);
    const double padding = maxRadius * 2.5 + 4.0;

    const document::Layer* clipBaseLayer = activeLayer->isClippingMask()
        ? layerStack.getClipBaseLayer(layerStack.getActiveIndex())
        : nullptr;

    const raster::PixelContext pCtx{ activeLayer->isAlphaLocked(), clipBaseLayer, &selectionMask, nullptr };

    const auto interpolatedDabs = raster::DabInterpolator::interpolate(
        startDab, endDab, brushProfile.spacingFactor, distanceCarryover
    );

    auto& grid = activeLayer->getTileGrid();
    const int activeIdx = layerStack.getActiveIndex();

    static thread_local std::mt19937 rng(777);
    std::uniform_real_distribution<double> distScatter(-1.0, 1.0);

    double boundMinX = 1e9, boundMaxX = -1e9;
    double boundMinY = 1e9, boundMaxY = -1e9;

    std::vector<raster::Dab> finalDabs;
    finalDabs.reserve(interpolatedDabs.size() * (symmetryConfig.mode == math::SymmetryMode::None ? 1 : 8));

    for (const auto& dab : interpolatedDabs) {
        const int scatter = (brushProfile.scatterCount > 1) ? brushProfile.scatterCount : 1;

        for (int s = 0; s < scatter; ++s) {
            raster::Dab renderDab = dab;
            if (scatter > 1) {
                renderDab.position.x += distScatter(rng) * dab.radius * 0.8;
                renderDab.position.y += distScatter(rng) * dab.radius * 0.8;
            }

            if (symmetryConfig.mode != math::SymmetryMode::None) {
                std::vector<raster::Dab> symDabs;
                math::SymmetryEngine::apply(symmetryConfig, renderDab, strokeStart, symDabs);
                for (const auto& sd : symDabs) {
                    finalDabs.push_back(sd);
                    boundMinX = std::min(boundMinX, sd.position.x - padding);
                    boundMaxX = std::max(boundMaxX, sd.position.x + padding);
                    boundMinY = std::min(boundMinY, sd.position.y - padding);
                    boundMaxY = std::max(boundMaxY, sd.position.y + padding);
                }
            } else {
                finalDabs.push_back(renderDab);
                boundMinX = std::min(boundMinX, renderDab.position.x - padding);
                boundMaxX = std::max(boundMaxX, renderDab.position.x + padding);
                boundMinY = std::min(boundMinY, renderDab.position.y - padding);
                boundMaxY = std::max(boundMaxY, renderDab.position.y + padding);
            }
        }
    }

    if (finalDabs.empty()) return;

    const int startTileX = static_cast<int>(std::floor(boundMinX / canvas::Tile::TILE_SIZE));
    const int endTileX   = static_cast<int>(std::floor(boundMaxX / canvas::Tile::TILE_SIZE));
    const int startTileY = static_cast<int>(std::floor(boundMinY / canvas::Tile::TILE_SIZE));
    const int endTileY   = static_cast<int>(std::floor(boundMaxY / canvas::Tile::TILE_SIZE));

    for (int ty = startTileY; ty <= endTileY; ++ty) {
        for (int tx = startTileX; tx <= endTileX; ++tx) {
            canvas::Tile* tile = grid.getTile(tx, ty);
            if (tile) {
                const auto& buf = tile->getBuffer();
                undoManager.recordTileBefore(activeIdx, tx, ty, buf.getData(), buf.getSizeInBytes());
            } else {
                canvas::PixelBuffer emptyBuf(canvas::Tile::TILE_SIZE, canvas::Tile::TILE_SIZE, {0, 0, 0, 0});
                undoManager.recordTileBefore(activeIdx, tx, ty, emptyBuf.getData(), emptyBuf.getSizeInBytes());
            }
        }
    }

    for (const auto& rDab : finalDabs) {
        if (activeEngine) {
            activeEngine->renderDab(rDab, brushProfile, canvasTexture, grid, &outputBuffer, pCtx);
        } else {
            raster::DabRenderer::renderDab(rDab, brushProfile, canvasTexture, grid, pCtx);
        }
    }

    const math::Rect2D dirtyBounds{
        boundMinX, boundMinY,
        std::max(0.0, boundMaxX - boundMinX),
        std::max(0.0, boundMaxY - boundMinY)
    };

    compositor.compositeRegion(layerStack.getAllLayersForComposition(), dirtyBounds, outputBuffer, bgColor);
    if (outDirtyBounds) {
        *outDirtyBounds = dirtyBounds;
    }
}

} // namespace aladyn::engine::boundary::internal
