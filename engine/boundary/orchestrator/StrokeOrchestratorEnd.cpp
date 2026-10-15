// StrokeOrchestrator::endStrokeRaw -- separado de StrokeOrchestrator.cpp em
// 2026-09-22 (teto ARCcC de 450 linhas). Desde 2026-10-09 o fim com estabilização
// drena o estabilizador (renderReleaseTail) em vez do salto reto e da cauda extrapolada.
#include "StrokeOrchestrator.hpp"
#include "../../core/raster/DabInterpolator.hpp"
#include "../../core/raster/DabRenderer.hpp"
#include "../../core/raster/PixelContext.hpp"
#include "../../core/brush/DynamicMapper.hpp"
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>
#include "StrokeLatencyPolicy.hpp"

namespace aladyn::engine::boundary::orchestrator {

using detail::useLatencyShortcut;

namespace {

void uniteDirty(utils::Rect2D& total, const utils::Rect2D& dirty) {
    if (dirty.width > 0 && dirty.height > 0) {
        total = (total.width > 0) ? total.united(dirty) : dirty;
    }
}

// Pen-up with stabilization (2026-10-09). The stabilized line is still behind the pen
// (tens of px with a mouse); until now a straight segment jumped to the release point
// and a 20 px taper was extrapolated past it in the stale direction of the lagging point:
// the "whip" that kept circles from closing. Here the stabilizer drains (the pen rests
// on the release point while its window runs out), the line follows the path through
// spline segments, and the taper thins the last `strokeTaperLength` px of that tail
// without going one pixel beyond where the pen lifted.
void renderReleaseTail(RawStrokeContext& ctx, bool splineReady, utils::Rect2D& totalDirty,
                       telemetry::StageMetrics& stages) {
    const auto nodes = ctx.stabilizer.drain(ctx.lastRawPoint, ctx.lastRawPressure);
    double tailLength = 0.0;
    utils::Point2D previous = ctx.lastDab.position;
    for (const auto& node : nodes) {
        tailLength += previous.distanceTo(node.position);
        previous = node.position;
    }
    if (tailLength < 0.05) return;  // the line was already on the release point

    const brush::BrushProfile& profile = ctx.brushProfile;
    const double taperLength = std::min(tailLength, profile.strokeTaperLength > 0.0 ? profile.strokeTaperLength : 20.0);
    const bool taper = profile.strokeTaperEnabled && taperLength > 0.5;
    const double normVel = ctx.velocityTracker.getNormalizedVelocity(1500.0);
    double walked = 0.0;
    previous = ctx.lastDab.position;
    for (const auto& node : nodes) {
        walked += previous.distanceTo(node.position);
        previous = node.position;
        auto mapped = brush::DynamicMapper::map(profile, node.position, node.pressure, normVel,
                                                ctx.lastPose.twist, ctx.lastPose.altitude, ctx.lastPose.azimuth);
        if (taper) {
            const double left = std::clamp((tailLength - walked) / taperLength, 0.0, 1.0);
            mapped.radius *= 0.05 + 0.95 * left;
            mapped.opacity *= left;
        }
        utils::Dab dab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle,
                       profile.blendMode, mapped.color, mapped.aspectRatio);
        utils::Rect2D dirty{0, 0, 0, 0};
        uint32_t dabs = 0;
        StrokeOrchestrator::renderSegment(
            ctx.lastDab, dab, profile, ctx.canvasTexture, ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
            ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
            ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirty, &dabs, &stages, true,
            &ctx.strokeMix);
        uniteDirty(totalDirty, dirty);
        ctx.lastDab = dab;
    }
}

} // namespace

std::vector<double> StrokeOrchestrator::endStrokeRaw(
    RawStrokeContext& ctx,
    std::function<void(const stroke::PointerEvent&)> endStrokeCallback,
    double endX, double endY
) {
    utils::Rect2D totalCatchupDirty{0, 0, 0, 0};
    telemetry::StageMetrics stagesCatchup{};
    const bool shortcut = useLatencyShortcut(ctx);

    if (ctx.isDrawing) {
        // Correção C4: Repassa a posição de soltura da caneta se fornecida
        if (endX > -1e8 && endY > -1e8) {
            ctx.lastRawPoint = {endX, endY};
            ctx.hasLastRawPoint = true;
        }
        const bool splineReady = ctx.splineCount >= 3;
        const bool stabilized = !shortcut && ctx.stabilizer.isActive();

        ctx.splineCount = 0;
        ctx.pendingFirstSegment = false;

        if (ctx.segmentsRenderedInStroke == 0) {
            // Toque isolado (click / tap): carimba o ponto inicial do traço
            utils::Rect2D dirty{0, 0, 0, 0};
            uint32_t dabsRendered = 0;
            renderSegment(
                ctx.lastDab, ctx.lastDab, ctx.brushProfile, ctx.canvasTexture,
                ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
                ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
                ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirty, &dabsRendered,
                &stagesCatchup, true, &ctx.strokeMix
            );
            uniteDirty(totalCatchupDirty, dirty);
        } else if (stabilized && ctx.hasLastRawPoint) {
            renderReleaseTail(ctx, splineReady, totalCatchupDirty, stagesCatchup);
        } else if (ctx.hasLastRawPoint) {
            // Sem estabilização (ou baixa latência): o traço já acompanha a caneta.
            const utils::Point2D stabPos = shortcut ? ctx.lastRawPoint : ctx.stabilizer.getStabilizedPosition();
            const utils::Point2D toRaw = ctx.lastRawPoint - stabPos;
            const double distToRaw = toRaw.length();

            // Catch-up seguro para alcançar a posição real de soltura se o ponteiro ficou levemente atrasado
            if (!shortcut && distToRaw > 1.0) {
                auto mappedCatchup = brush::DynamicMapper::map(ctx.brushProfile, ctx.lastRawPoint, ctx.lastRawPressure, 0.0, ctx.lastPose.twist, ctx.lastPose.altitude, ctx.lastPose.azimuth);
                utils::Dab catchupDab(mappedCatchup.position, mappedCatchup.radius, mappedCatchup.opacity, mappedCatchup.pressure, mappedCatchup.angle, ctx.brushProfile.blendMode, mappedCatchup.color, mappedCatchup.aspectRatio);
                utils::Rect2D dirty{0, 0, 0, 0};
                uint32_t dabsRendered = 0;
                renderSegment(
                    ctx.lastDab, catchupDab, ctx.brushProfile, ctx.canvasTexture,
                    ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
                    ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
                    ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirty, &dabsRendered,
                    &stagesCatchup, true, &ctx.strokeMix
                );
                uniteDirty(totalCatchupDirty, dirty);
                ctx.lastDab = catchupDab;
            }
        }
    }

    auto now = std::chrono::high_resolution_clock::now();
    double t = std::chrono::duration<double>(now.time_since_epoch()).count();
    if (endStrokeCallback) {
        const utils::Point2D releasePos = shortcut ? ctx.lastRawPoint : ctx.stabilizer.getStabilizedPosition();
        endStrokeCallback({stroke::PointerEventType::Release, releasePos, 0.0, t});
    }
    ctx.hasLastRawPoint = false;
    ctx.pendingFirstSegment = false;

    if (totalCatchupDirty.width > 0 && totalCatchupDirty.height > 0) {
        return { totalCatchupDirty.x, totalCatchupDirty.y, totalCatchupDirty.width, totalCatchupDirty.height };
    }
    return { 0.0, 0.0, 0.0, 0.0 };
}

} // namespace aladyn::engine::boundary::orchestrator
