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
    math::Rect2D* outDirtyBounds,
    uint32_t* outDabsRendered,
    telemetry::StageMetrics* outStages,
    bool performComposite
) {
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) {
        if (outStages) *outStages = telemetry::StageMetrics{};
        return;
    }

    // Clipping Mask é 100% não-destrutivo: a grade de tiles armazena o traço completo.
    // O recorte é aplicado dinamicamente pelo Compositor durante a renderização.
    const raster::PixelContext pCtx{ activeLayer->isAlphaLocked(), nullptr, &selectionMask, nullptr };

    auto tInterp0 = std::chrono::high_resolution_clock::now();
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
                    const double dabPad = sd.radius + 2.5;
                    boundMinX = std::min(boundMinX, sd.position.x - dabPad);
                    boundMaxX = std::max(boundMaxX, sd.position.x + dabPad);
                    boundMinY = std::min(boundMinY, sd.position.y - dabPad);
                    boundMaxY = std::max(boundMaxY, sd.position.y + dabPad);
                }
            } else {
                finalDabs.push_back(renderDab);
                const double dabPad = renderDab.radius + 2.5;
                boundMinX = std::min(boundMinX, renderDab.position.x - dabPad);
                boundMaxX = std::max(boundMaxX, renderDab.position.x + dabPad);
                boundMinY = std::min(boundMinY, renderDab.position.y - dabPad);
                boundMaxY = std::max(boundMaxY, renderDab.position.y + dabPad);
            }
        }
    }
    auto tInterp1 = std::chrono::high_resolution_clock::now();

    if (finalDabs.empty()) {
        if (outDabsRendered) *outDabsRendered = 0;
        if (outStages) {
            *outStages = telemetry::StageMetrics{};
            outStages->timeInterpolationUs = std::chrono::duration<double, std::micro>(tInterp1 - tInterp0).count();
        }
        return;
    }
    if (outDabsRendered) *outDabsRendered = static_cast<uint32_t>(finalDabs.size());

    const int startTileX = static_cast<int>(std::floor(boundMinX / canvas::Tile::TILE_SIZE));
    const int endTileX   = static_cast<int>(std::floor(boundMaxX / canvas::Tile::TILE_SIZE));
    const int startTileY = static_cast<int>(std::floor(boundMinY / canvas::Tile::TILE_SIZE));
    const int endTileY   = static_cast<int>(std::floor(boundMaxY / canvas::Tile::TILE_SIZE));

    static const uint8_t s_emptyTileData[canvas::Tile::TILE_SIZE * canvas::Tile::TILE_SIZE * sizeof(raster::ColorRGBA)] = {0};
    constexpr size_t s_emptyTileBytes = sizeof(s_emptyTileData);

    auto tUndo0 = std::chrono::high_resolution_clock::now();
    uint32_t tilesCount = 0;
    for (int ty = startTileY; ty <= endTileY; ++ty) {
        for (int tx = startTileX; tx <= endTileX; ++tx) {
            ++tilesCount;
            canvas::Tile* tile = grid.getTile(tx, ty);
            if (tile) {
                const auto& buf = tile->getBuffer();
                undoManager.recordTileBefore(activeIdx, tx, ty, buf.getData(), buf.getSizeInBytes());
            } else {
                undoManager.recordTileBefore(activeIdx, tx, ty, s_emptyTileData, s_emptyTileBytes);
            }
        }
    }
    auto tUndo1 = std::chrono::high_resolution_clock::now();

    auto tRaster0 = std::chrono::high_resolution_clock::now();
    for (const auto& rDab : finalDabs) {
        if (activeEngine) {
            activeEngine->renderDab(rDab, brushProfile, canvasTexture, grid, &outputBuffer, pCtx);
        } else {
            raster::DabRenderer::renderDab(rDab, brushProfile, canvasTexture, grid, pCtx);
        }
    }
    auto tRaster1 = std::chrono::high_resolution_clock::now();

    const math::Rect2D dirtyBounds{
        boundMinX, boundMinY,
        std::max(0.0, boundMaxX - boundMinX),
        std::max(0.0, boundMaxY - boundMinY)
    };

    double timeCompUs = 0.0;
    if (performComposite) {
        auto tComp0 = std::chrono::high_resolution_clock::now();
        compositor.compositeRegion(layerStack.getAllLayersForComposition(), dirtyBounds, outputBuffer, bgColor);
        auto tComp1 = std::chrono::high_resolution_clock::now();
        timeCompUs = std::chrono::duration<double, std::micro>(tComp1 - tComp0).count();
    }

    if (outDirtyBounds) {
        *outDirtyBounds = dirtyBounds;
    }

    if (outStages) {
        outStages->timeInterpolationUs = std::chrono::duration<double, std::micro>(tInterp1 - tInterp0).count();
        outStages->timeUndoRecordUs = std::chrono::duration<double, std::micro>(tUndo1 - tUndo0).count();
        outStages->timeRasterDabUs = std::chrono::duration<double, std::micro>(tRaster1 - tRaster0).count();
        outStages->timeCompositeUs = timeCompUs;
        outStages->dabsRendered = static_cast<uint32_t>(finalDabs.size());
        outStages->dirtyWidth = dirtyBounds.width;
        outStages->dirtyHeight = dirtyBounds.height;
        outStages->dirtyAreaPx = dirtyBounds.width * dirtyBounds.height;
        outStages->tilesRecorded = tilesCount;
        outStages->tilesComposited = performComposite ? tilesCount : 0;
    }
}

} // namespace aladyn::engine::boundary::internal
