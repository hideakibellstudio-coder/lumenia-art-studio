#include "StrokeSessionOrchestrator.hpp"
#include "PixelFormatGuard.hpp"

#include "../../core/brush/DynamicMapper.hpp"
#include "../../core/document/blending/BlendKernel.hpp"
#include <cmath>

namespace aladyn::engine::boundary::orchestrator {

namespace {
    // Metricas de memoria/tiles compartilhadas por endStroke e telemetrySnapshot.
    struct MemorySample {
        uint32_t activeTiles{0};
        double   tileMemMB{0.0};
        double   undoMemMB{0.0};
        uint32_t undoSteps{0};
    };

    MemorySample sampleMemory(const document::LayerStack& stack, const history::TileUndoManager& undoManager) {
        MemorySample s{};
        if (const auto* layer = stack.getActiveLayer()) {
            s.activeTiles = static_cast<uint32_t>(layer->getTileGrid().getActiveTilesCount());
            const size_t bpp = canvas::bytesPerPixel(layer->getTileGrid().getFormat());
            s.tileMemMB = (s.activeTiles * canvas::Tile::TILE_SIZE * canvas::Tile::TILE_SIZE * bpp) / (1024.0 * 1024.0);
        }
        s.undoMemMB = undoManager.getMemoryUsageBytes() / (1024.0 * 1024.0);
        s.undoSteps = static_cast<uint32_t>(undoManager.getUndoCount());
        return s;
    }
}

// Opacidade < 100% = teto do traço: o traço pinta numa cópia de trabalho da camada ativa e a camada recebe a
// mistura (StrokeOpacityMix). Camada travada, grupo ou filtro não recebem traço, então não ganham cópia.
static void beginOpacityCap(RawStrokeContext& ctx) {
    ctx.strokeMix.end();
    if (!raster::StrokeOpacityMix::needed(ctx.brushProfile.opacity)) return;
    document::Layer* layer = ctx.layerStack.getActiveLayer();
    if (!layer || layer->isLocked() || layer->isGroup() || layer->isFilter()) return;
    ctx.strokeMix.begin(layer->getTileGrid(), ctx.brushProfile.opacity, ctx.layerStack.getActiveIndex());
}

void StrokeSessionOrchestrator::beginStroke(RawStrokeContext& ctx, const stroke::PointerEvent& rawEvent) {
    stroke::PointerEvent event = rawEvent;
    event.pressure = ctx.pressureCalibration.apply(rawEvent.pressure);
    ctx.isDrawing = true;
    ctx.segmentsRenderedInStroke = 0;
    ctx.pendingFirstSegment = false;
    ctx.strokeStartPoint = event.position;
    ctx.lastRawPressure = event.pressure;
    ctx.distanceCarryover = -1.0;
    ctx.stabilizer.reset(event.position, event.pressure, event.timestamp);
    ctx.velocityTracker.reset(event.position, event.timestamp);
    ctx.undoManager.beginStep("Stroke");
    beginOpacityCap(ctx);
    if (ctx.activeEngine) ctx.activeEngine->onBeginStroke();
    ctx.lastPose = {event.altitude, event.azimuth, event.twist};
    auto mapped = brush::DynamicMapper::map(
        ctx.brushProfile, event.position, event.pressure, 0.0,
        event.twist, event.altitude, event.azimuth
    );
    ctx.lastDab = utils::Dab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, ctx.brushProfile.blendMode, mapped.color, mapped.aspectRatio);
    ctx.splineP0 = ctx.lastDab;
    ctx.splineCount = 1;
    ctx.telemetryManager.onBeginStroke(event.pressure, static_cast<int>(ctx.brushProfile.engineType));
}


StrokeTelemetrySample StrokeSessionOrchestrator::updateStroke(RawStrokeContext& ctx, const stroke::PointerEvent& rawEvent) {
    if (!ctx.isDrawing) return {0.0, 0.0, 0.0};
    stroke::PointerEvent event = rawEvent;
    event.pressure = ctx.pressureCalibration.apply(rawEvent.pressure);
    ++ctx.segmentsRenderedInStroke;
    ctx.lastRawPressure = event.pressure;
    const double currentVelocity = ctx.velocityTracker.update(event.position, event.timestamp);
    const double normVel = ctx.velocityTracker.getNormalizedVelocity(1500.0);
    // Mesmo criterio do StrokeOrchestrator: o atalho de baixa latencia so vale
    // quando nao ha estabilizacao pedida. `lowLatency` sozinho desviava o
    // estabilizador, e como low_latency=True e' o padrao do backend o slider de
    // suavizacao nao tinha efeito nenhum neste caminho tambem.
    const bool shortcut = ctx.lowLatency && ctx.stabilizer.getStabilizationPercentage() <= 0.5;
    const utils::Point2D pos = shortcut ? event.position : ctx.stabilizer.updateAt(event.position, event.pressure, normVel, event.timestamp);
    const double effectivePressure = shortcut ? event.pressure : ctx.stabilizer.getStabilizedPressure();

    ctx.lastPose = {event.altitude, event.azimuth, event.twist};
    auto mapped = brush::DynamicMapper::map(
        ctx.brushProfile, pos, effectivePressure, normVel,
        event.twist, event.altitude, event.azimuth
    );
    utils::Dab currentDab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, ctx.brushProfile.blendMode, mapped.color, mapped.aspectRatio);
    renderSegment(ctx, ctx.lastDab, currentDab);
    ctx.lastDab = currentDab;
    return { event.pressure, currentVelocity, currentDab.opacity };
}

bool StrokeSessionOrchestrator::endStroke(RawStrokeContext& ctx) {
    if (!ctx.isDrawing) return false;
    if (ctx.segmentsRenderedInStroke == 0) {
        utils::Rect2D dirty{0, 0, 0, 0};
        uint32_t dabsRendered = 0;
        StrokeOrchestrator::renderSegment(
            ctx.lastDab, ctx.lastDab, ctx.brushProfile, ctx.canvasTexture,
            ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
            ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
            ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirty, &dabsRendered,
            nullptr, true, &ctx.strokeMix
        );
        ctx.segmentsRenderedInStroke = 1;
    }
    if (ctx.activeEngine) ctx.activeEngine->onEndStroke();
    ctx.strokeMix.end();
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

void StrokeSessionOrchestrator::renderSegment(RawStrokeContext& ctx, const utils::Dab& startDab, const utils::Dab& endDab) {
    StrokeOrchestrator::renderSegment(
        startDab, endDab, ctx.brushProfile, ctx.canvasTexture,
        ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
        ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
        ctx.distanceCarryover,
        ctx.symmetryConfig, &ctx.strokeStartPoint, nullptr, nullptr, nullptr, true, &ctx.strokeMix
    );
}

telemetry::RealTimeStrokeMetrics StrokeSessionOrchestrator::telemetrySnapshot(
    const document::LayerStack& stack,
    const history::TileUndoManager& undoManager,
    const telemetry::EngineTelemetryManager& telemetryManager
) {
    const MemorySample s = sampleMemory(stack, undoManager);
    telemetry::RealTimeStrokeMetrics metrics = telemetryManager.getSnapshot(s.activeTiles, s.tileMemMB, s.undoMemMB, s.undoSteps);
    // O nível que a mesclagem usa de verdade (BlendKernel escolhe pela CPU na hora de rodar), não o do build.
    metrics.simdActive = document::blending::BlendKernel::activeLevel() == document::blending::BlendSimdLevel::Avx2;
    return metrics;
}

} // namespace aladyn::engine::boundary::orchestrator
