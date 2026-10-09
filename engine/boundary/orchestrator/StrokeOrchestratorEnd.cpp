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
        if (splineReady) {
            utils::Dab forward = dab;
            forward.position = dab.position * 2.0 - ctx.splineP1.position;
            StrokeOrchestrator::renderSplineSegment(ctx.splineP0, ctx.splineP1, dab, forward, ctx, &dirty, &dabs, &stages);
            ctx.splineP0 = ctx.splineP1;
            ctx.splineP1 = dab;
        } else {
            StrokeOrchestrator::renderSegment(
                ctx.lastDab, dab, profile, ctx.canvasTexture, ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
                ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
                ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirty, &dabs, &stages, true,
                &ctx.strokeMix);
        }
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
        // Read before the block below zeroes the spline state: the release tail continues the spline.
        const bool splineReady = ctx.splineCount >= 3;
        const bool stabilized = !shortcut && ctx.stabilizer.isActive();

        if (ctx.splineCount == 2) {
            // Apenas P0 e P1 foram capturados (1 único movimento): renderiza P0 -> P1 via Catmull-Rom centrípeta
            utils::Dab dNeg1 = ctx.splineP0;
            dNeg1.position = ctx.splineP0.position * 2.0 - ctx.splineP1.position;
            utils::Dab dPlus2 = ctx.splineP1;
            dPlus2.position = ctx.splineP1.position * 2.0 - ctx.splineP0.position;

            utils::Rect2D dirty1{0, 0, 0, 0};
            uint32_t dabs1 = 0;
            telemetry::StageMetrics stages1{};
            renderSplineSegment(dNeg1, ctx.splineP0, ctx.splineP1, dPlus2, ctx, &dirty1, &dabs1, &stages1);
            if (dirty1.width > 0 && dirty1.height > 0) {
                totalCatchupDirty = dirty1;
            }
            ctx.lastDab = ctx.splineP1;
            ctx.splineCount = 0;
            ctx.pendingFirstSegment = false;
        } else {
            // splineCount >= 3 ou 1: Todos os segmentos até o último ponto já foram renderizados durante updateStrokeRaw
            ctx.splineCount = 0;
            ctx.pendingFirstSegment = false;
        }


        if (stabilized && ctx.hasLastRawPoint && ctx.segmentsRenderedInStroke > 0) {
            renderReleaseTail(ctx, splineReady, totalCatchupDirty, stagesCatchup);
        } else if (ctx.hasLastRawPoint && ctx.segmentsRenderedInStroke > 0) {
            // Without stabilization (or below 0.5%) the line is already on the pen: unchanged since 2026-09-22.
            const utils::Point2D stabPos = shortcut ? ctx.lastRawPoint : ctx.stabilizer.getStabilizedPosition();
            const utils::Point2D v = shortcut ? (ctx.lastRawPoint - ctx.lastDab.position) : ctx.stabilizer.getLastMovementDelta();
            const double speed = v.length();
            const utils::Point2D toRaw = ctx.lastRawPoint - stabPos;
            const double distToRaw = toRaw.length();

            // 1. Catch-up para alcançar a posição real de soltura quando o estabilizador ficou para trás
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
                if (dirty.width > 0 && dirty.height > 0) {
                    totalCatchupDirty = (totalCatchupDirty.width > 0) ? totalCatchupDirty.united(dirty) : dirty;
                }
                ctx.lastDab = catchupDab;
            }

            // 2. Afunilamento final com comprimento fixo configurável (Decisão D3 / Correção B1)
            // Funciona tanto com estabilização quanto no atalho de baixa latência, desde que a caneta
            // estivesse em movimento no momento da soltura (speed > 0.1).
            if (ctx.brushProfile.strokeTaperEnabled && speed > 0.1) {
                const utils::Point2D dir = v * (1.0 / speed);
                const double taperLen = (ctx.brushProfile.strokeTaperLength > 0.0)
                    ? ctx.brushProfile.strokeTaperLength
                    : 20.0;
                const utils::Point2D targetPt = ctx.lastDab.position + (dir * taperLen);

                auto mapped = brush::DynamicMapper::map(ctx.brushProfile, targetPt, 0.0, 0.0, ctx.lastPose.twist, ctx.lastPose.altitude, ctx.lastPose.azimuth);
                mapped.radius *= 0.05;
                mapped.opacity = 0.0;
                utils::Dab currentDab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, ctx.brushProfile.blendMode, mapped.color, mapped.aspectRatio);
                utils::Rect2D dirty{0, 0, 0, 0};
                uint32_t dabsRendered = 0;
                renderSegment(
                    ctx.lastDab, currentDab, ctx.brushProfile, ctx.canvasTexture,
                    ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
                    ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
                    ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirty, &dabsRendered,
                    &stagesCatchup, true, &ctx.strokeMix
                );
                if (dirty.width > 0 && dirty.height > 0) {
                    totalCatchupDirty = (totalCatchupDirty.width > 0) ? totalCatchupDirty.united(dirty) : dirty;
                }
                ctx.lastDab = currentDab;
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
