#include "StrokeSessionOrchestrator.hpp"

#include "../../../core/brush/DynamicMapper.hpp"
#include <cmath>

namespace aladyn::engine::boundary::internal {

namespace {
    // Metricas de memoria/tiles compartilhadas por endStroke e telemetrySnapshot.
    struct MemorySample {
        uint32_t activeTiles{0};
        double   tileMemMB{0.0};
        double   undoMemMB{0.0};
        uint32_t undoSteps{0};
    };

    MemorySample sampleMemory(const document::LayerStack& stack, const canvas::TileUndoManager& undoManager) {
        MemorySample s{};
        if (const auto* layer = stack.getActiveLayer()) {
            s.activeTiles = static_cast<uint32_t>(layer->getTileGrid().getActiveTilesCount());
        }
        s.tileMemMB = (s.activeTiles * canvas::Tile::TILE_SIZE * canvas::Tile::TILE_SIZE * 4) / (1024.0 * 1024.0);
        s.undoMemMB = undoManager.getMemoryUsageBytes() / (1024.0 * 1024.0);
        s.undoSteps = static_cast<uint32_t>(undoManager.getUndoCount());
        return s;
    }
}

void StrokeSessionOrchestrator::beginStroke(RawStrokeContext& ctx, const stroke::PointerEvent& event) {
    ctx.isDrawing = true;
    ctx.segmentsRenderedInStroke = 0;
    ctx.pendingFirstSegment = false;
    ctx.strokeStartPoint = event.position;
    ctx.lastRawPressure = event.pressure;
    ctx.distanceCarryover = 0.0;
    ctx.stabilizer.reset(event.position);
    ctx.velocityTracker.reset(event.position, event.timestamp);
    ctx.undoManager.beginStep("Stroke");
    if (ctx.activeEngine) ctx.activeEngine->onBeginStroke();
    auto mapped = brush::DynamicMapper::map(
        ctx.brushProfile, event.position, event.pressure, 0.0, 0.0,
        event.twist, event.altitude, event.azimuth
    );
    ctx.lastDab = raster::Dab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, ctx.brushProfile.blendMode, mapped.color, mapped.aspectRatio);
    ctx.telemetryManager.onBeginStroke(event.pressure, static_cast<int>(ctx.brushProfile.engineType));
}

StrokeTelemetrySample StrokeSessionOrchestrator::updateStroke(RawStrokeContext& ctx, const stroke::PointerEvent& event) {
    if (!ctx.isDrawing) return {0.0, 0.0, 0.0};
    ++ctx.segmentsRenderedInStroke;
    ctx.lastRawPressure = event.pressure;
    const double currentVelocity = ctx.velocityTracker.update(event.position, event.timestamp);
    const double normVel = ctx.velocityTracker.getNormalizedVelocity(1500.0);
    // Mesmo criterio do StrokeOrchestrator: o atalho de baixa latencia so vale
    // quando nao ha estabilizacao pedida. `lowLatency` sozinho desviava o
    // estabilizador, e como low_latency=True e' o padrao do backend o slider de
    // suavizacao nao tinha efeito nenhum neste caminho tambem.
    const bool atalho = ctx.lowLatency && ctx.stabilizer.getStabilizationPercentage() <= 0.5;
    const math::Point2D pos = atalho ? event.position : ctx.stabilizer.update(event.position, normVel);

    double strokeAngle = 0.0;
    const double dx = pos.x - ctx.lastDab.position.x;
    const double dy = pos.y - ctx.lastDab.position.y;
    if (dx * dx + dy * dy > 0.01) {
        strokeAngle = std::atan2(dy, dx) * (180.0 / 3.14159265358979323846);
        if (strokeAngle < 0.0) strokeAngle += 360.0;
    }

    auto mapped = brush::DynamicMapper::map(
        ctx.brushProfile, pos, event.pressure, normVel, strokeAngle,
        event.twist, event.altitude, event.azimuth
    );
    raster::Dab currentDab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, ctx.brushProfile.blendMode, mapped.color, mapped.aspectRatio);
    renderSegment(ctx, ctx.lastDab, currentDab);
    ctx.lastDab = currentDab;
    return { event.pressure, currentVelocity, currentDab.opacity };
}

bool StrokeSessionOrchestrator::endStroke(RawStrokeContext& ctx) {
    if (!ctx.isDrawing) return false;
    if (ctx.segmentsRenderedInStroke == 0) {
        math::Rect2D dirty{0, 0, 0, 0};
        uint32_t dabsRendered = 0;
        StrokeOrchestrator::renderSegment(
            ctx.lastDab, ctx.lastDab, ctx.brushProfile, ctx.canvasTexture,
            ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
            ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
            ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirty, &dabsRendered
        );
        ctx.segmentsRenderedInStroke = 1;
    }
    if (ctx.activeEngine) ctx.activeEngine->onEndStroke();
    ctx.undoManager.commitStep(ctx.layerStack);
    ctx.isDrawing = false;
    ctx.distanceCarryover = 0.0;

    if (ctx.activeEngine && ctx.activeEngine->getType() == brush::EngineType::Eraser) {
        if (auto* layer = ctx.layerStack.getActiveLayer()) {
            layer->getTileGrid().pruneEmptyTiles();
        }
    }

    if (ctx.telemetryManager.isEnabled()) {
        const MemorySample s = sampleMemory(ctx.layerStack, ctx.undoManager);
        ctx.telemetryManager.onEndStroke(0, s.activeTiles, s.tileMemMB, s.undoMemMB, s.undoSteps);
    }
    return true;
}

void StrokeSessionOrchestrator::renderSegment(RawStrokeContext& ctx, const raster::Dab& startDab, const raster::Dab& endDab) {
    StrokeOrchestrator::renderSegment(
        startDab, endDab, ctx.brushProfile, ctx.canvasTexture,
        ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
        ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
        ctx.distanceCarryover,
        ctx.symmetryConfig, &ctx.strokeStartPoint
    );
}

telemetry::RealTimeStrokeMetrics StrokeSessionOrchestrator::telemetrySnapshot(
    const document::LayerStack& stack,
    const canvas::TileUndoManager& undoManager,
    const telemetry::EngineTelemetryManager& telemetryManager
) {
    const MemorySample s = sampleMemory(stack, undoManager);
    return telemetryManager.getSnapshot(s.activeTiles, s.tileMemMB, s.undoMemMB, s.undoSteps);
}

} // namespace aladyn::engine::boundary::internal
