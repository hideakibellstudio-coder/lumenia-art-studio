// Desenho de um segmento do traço: interpolação dos carimbos, registro no
// histórico, rasterização e composição da região suja. Separado de
// StrokeOrchestrator.cpp em 2026-09-25 (447 linhas, na parede dos 450): lá
// fica a entrada da caneta (updateStrokeRaw), aqui o que ela manda desenhar.
#include "StrokeOrchestrator.hpp"
#include "../../core/raster/DabInterpolator.hpp"
#include "../../core/raster/DabRenderer.hpp"
#include "../../core/raster/PixelContext.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <random>

namespace aladyn::engine::boundary::orchestrator {

static void renderDabsPipeline(
    const std::vector<utils::Dab>& interpolatedDabs,
    const brush::BrushProfile& brushProfile,
    const canvas::CanvasTexture& canvasTexture,
    engines::IBrushEngine* activeEngine,
    document::LayerStack& layerStack,
    const selection::SelectionMask& selectionMask,
    history::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor,
    const math::SymmetryConfig& symmetryConfig,
    const utils::Point2D* strokeStart,
    utils::Rect2D* outDirtyBounds,
    uint32_t* outDabsRendered,
    telemetry::StageMetrics* outStages,
    bool performComposite,
    double timeInterpolationUs,
    raster::StrokeOpacityMix* strokeMix
) {
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) {
        if (outStages) *outStages = telemetry::StageMetrics{};
        return;
    }

    // Clipping Mask é 100% não-destrutivo: a grade de tiles armazena o traço completo.
    // O recorte é aplicado dinamicamente pelo Compositor durante a renderização.
    const raster::PixelContext pCtx{ activeLayer->isMaskEditTarget() ? false : activeLayer->isAlphaLocked(), nullptr, &selectionMask, nullptr };
    auto& grid = activeLayer->getTargetGrid();
    const int activeIdx = layerStack.getActiveIndex();

    static thread_local std::mt19937 rng(777);
    std::uniform_real_distribution<double> distScatter(-1.0, 1.0);

    double boundMinX = 1e9, boundMaxX = -1e9;
    double boundMinY = 1e9, boundMaxY = -1e9;
    // A área suja cobre tudo o que o motor toca; a aquarela molhada passa do raio do dab (1,4x).
    const double reachScale = activeEngine ? std::max(1.0, activeEngine->reachScale(brushProfile)) : 1.0;

    std::vector<utils::Dab> finalDabs;
    finalDabs.reserve(interpolatedDabs.size() * (symmetryConfig.mode == math::SymmetryMode::None ? 1 : 8));

    for (const auto& dab : interpolatedDabs) {
        const int scatter = (brushProfile.scatterCount > 1) ? brushProfile.scatterCount : 1;

        for (int s = 0; s < scatter; ++s) {
            utils::Dab renderDab = dab;
            if (scatter > 1) {
                renderDab.position.x += distScatter(rng) * dab.radius * 0.8;
                renderDab.position.y += distScatter(rng) * dab.radius * 0.8;
            }

            if (symmetryConfig.mode != math::SymmetryMode::None) {
                std::vector<utils::Dab> symDabs;
                math::SymmetryEngine::apply(symmetryConfig, renderDab, strokeStart, symDabs);
                for (const auto& sd : symDabs) {
                    finalDabs.push_back(sd);
                    const double dabPad = sd.radius * reachScale + 2.5;
                    boundMinX = std::min(boundMinX, sd.position.x - dabPad);
                    boundMaxX = std::max(boundMaxX, sd.position.x + dabPad);
                    boundMinY = std::min(boundMinY, sd.position.y - dabPad);
                    boundMaxY = std::max(boundMaxY, sd.position.y + dabPad);
                }
            } else {
                finalDabs.push_back(renderDab);
                const double dabPad = renderDab.radius * reachScale + 2.5;
                boundMinX = std::min(boundMinX, renderDab.position.x - dabPad);
                boundMaxX = std::max(boundMaxX, renderDab.position.x + dabPad);
                boundMinY = std::min(boundMinY, renderDab.position.y - dabPad);
                boundMaxY = std::max(boundMaxY, renderDab.position.y + dabPad);
            }
        }
    }

    if (finalDabs.empty()) {
        if (outDabsRendered) *outDabsRendered = 0;
        if (outStages) {
            *outStages = telemetry::StageMetrics{};
            outStages->timeInterpolationUs = timeInterpolationUs;
        }
        return;
    }
    if (outDabsRendered) *outDabsRendered = static_cast<uint32_t>(finalDabs.size());

    const int startTileX = static_cast<int>(std::floor(boundMinX / canvas::Tile::TILE_SIZE));
    const int endTileX   = static_cast<int>(std::floor(boundMaxX / canvas::Tile::TILE_SIZE));
    const int startTileY = static_cast<int>(std::floor(boundMinY / canvas::Tile::TILE_SIZE));
    const int endTileY   = static_cast<int>(std::floor(boundMaxY / canvas::Tile::TILE_SIZE));

    const uint8_t* emptyTileData = canvas::zeroTileData();
    const size_t emptyTileBytes = canvas::Tile::bytesFor(grid.getFormat());

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
                undoManager.recordTileBefore(activeIdx, tx, ty, emptyTileData, emptyTileBytes);
            }
        }
    }
    auto tUndo1 = std::chrono::high_resolution_clock::now();

    // Opacidade < 100%: o motor pinta na cópia de trabalho e a camada recebe a mistura base <-> trabalho
    // (o teto do traço). A cópia só vale para a camada em que o traço começou.
    const bool capped = strokeMix && strokeMix->active() && strokeMix->layerIndex() == activeIdx;
    canvas::TileGrid& target = capped ? strokeMix->work() : grid;

    auto tRaster0 = std::chrono::high_resolution_clock::now();
    for (const auto& rDab : finalDabs) {
        if (activeEngine) {
            activeEngine->renderDab(rDab, brushProfile, canvasTexture, target, pCtx);
        } else {
            raster::DabRenderer::renderDab(rDab, brushProfile, canvasTexture, target, pCtx);
        }
    }
    if (capped) strokeMix->mergeInto(grid, startTileX, startTileY, endTileX, endTileY);
    auto tRaster1 = std::chrono::high_resolution_clock::now();

    const utils::Rect2D dirtyBounds{
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
        outStages->timeInterpolationUs = timeInterpolationUs;
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

void StrokeOrchestrator::renderSegment(
    const utils::Dab& startDab,
    const utils::Dab& endDab,
    const brush::BrushProfile& brushProfile,
    const canvas::CanvasTexture& canvasTexture,
    engines::IBrushEngine* activeEngine,
    document::LayerStack& layerStack,
    const selection::SelectionMask& selectionMask,
    history::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor,
    double& distanceCarryover,
    const math::SymmetryConfig& symmetryConfig,
    const utils::Point2D* strokeStart,
    utils::Rect2D* outDirtyBounds,
    uint32_t* outDabsRendered,
    telemetry::StageMetrics* outStages,
    bool performComposite,
    raster::StrokeOpacityMix* strokeMix
) {
    auto tInterp0 = std::chrono::high_resolution_clock::now();
    const auto interpolatedDabs = raster::DabInterpolator::interpolate(
        startDab, endDab, brushProfile.spacingFactor, distanceCarryover, &brushProfile
    );
    auto tInterp1 = std::chrono::high_resolution_clock::now();
    const double timeInterpUs = std::chrono::duration<double, std::micro>(tInterp1 - tInterp0).count();

    renderDabsPipeline(
        interpolatedDabs, brushProfile, canvasTexture, activeEngine, layerStack,
        selectionMask, undoManager, compositor, outputBuffer, bgColor,
        symmetryConfig, strokeStart, outDirtyBounds, outDabsRendered, outStages,
        performComposite, timeInterpUs, strokeMix
    );
}

void StrokeOrchestrator::renderSplineSegment(
    const utils::Dab& p0,
    const utils::Dab& p1,
    const utils::Dab& p2,
    const utils::Dab& p3,
    RawStrokeContext& ctx,
    utils::Rect2D* outDirtyBounds,
    uint32_t* outDabsRendered,
    telemetry::StageMetrics* outStages,
    bool performComposite
) {
    auto tInterp0 = std::chrono::high_resolution_clock::now();
    const auto interpolatedDabs = raster::DabInterpolator::interpolateSpline(
        p0, p1, p2, p3, ctx.brushProfile.spacingFactor, ctx.distanceCarryover, &ctx.brushProfile
    );
    auto tInterp1 = std::chrono::high_resolution_clock::now();
    const double timeInterpUs = std::chrono::duration<double, std::micro>(tInterp1 - tInterp0).count();

    renderDabsPipeline(
        interpolatedDabs, ctx.brushProfile, ctx.canvasTexture, ctx.activeEngine, ctx.layerStack,
        ctx.selectionMask, ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
        ctx.symmetryConfig, &ctx.strokeStartPoint, outDirtyBounds, outDabsRendered, outStages,
        performComposite, timeInterpUs, &ctx.strokeMix
    );
}

} // namespace aladyn::engine::boundary::orchestrator
