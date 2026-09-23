// StrokeOrchestrator::endStrokeRaw -- separado de StrokeOrchestrator.cpp em
// 2026-09-22 (teto ARCcC de 450 linhas). Corpo movido sem alteração.
#include "StrokeOrchestrator.hpp"
#include "../../../core/raster/DabInterpolator.hpp"
#include "../../../core/raster/DabRenderer.hpp"
#include "../../../core/raster/PixelContext.hpp"
#include "../../../core/brush/DynamicMapper.hpp"
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>
#include "StrokeLatencyPolicy.hpp"

namespace aladyn::engine::boundary::internal {

using detail::usarAtalhoDeLatencia;

std::vector<double> StrokeOrchestrator::endStrokeRaw(
    RawStrokeContext& ctx,
    std::function<void(const stroke::PointerEvent&)> endStrokeCallback
) {
    math::Rect2D totalCatchupDirty{0, 0, 0, 0};
    telemetry::StageMetrics stagesCatchup{};
    const bool atalho = usarAtalhoDeLatencia(ctx);

    if (ctx.isDrawing) {
        if (ctx.pendingFirstSegment) {
            auto mapped1 = brush::DynamicMapper::map(
                ctx.brushProfile, ctx.firstSample.stabilizedPos, ctx.firstSample.pressure,
                ctx.firstSample.normVel, 0.0, ctx.firstSample.twist,
                ctx.firstSample.altitude, ctx.firstSample.azimuth
            );
            raster::Dab dab1(mapped1.position, mapped1.radius, mapped1.opacity, mapped1.pressure, mapped1.angle, ctx.brushProfile.blendMode, mapped1.color, mapped1.aspectRatio);
            math::Rect2D dirty1{0, 0, 0, 0};
            uint32_t dabs1 = 0;
            renderSegment(
                ctx.lastDab, dab1, ctx.brushProfile, ctx.canvasTexture,
                ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
                ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
                ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirty1, &dabs1
            );
            if (dirty1.width > 0 && dirty1.height > 0) {
                totalCatchupDirty = dirty1;
            }
            ctx.lastDab = dab1;
            ctx.pendingFirstSegment = false;
        }

        if (ctx.hasLastRawPoint && ctx.segmentsRenderedInStroke > 0) {
            const math::Point2D stabPos = atalho ? ctx.lastRawPoint : ctx.stabilizer.getStabilizedPosition();
            const math::Point2D v = atalho ? (ctx.lastRawPoint - ctx.lastDab.position) : ctx.stabilizer.getLastMovementDelta();
            const double speed = v.length();
            const math::Point2D toRaw = ctx.lastRawPoint - stabPos;
            const double distToRaw = toRaw.length();

            bool isCollinear = false;
            if (speed > 0.1 && distToRaw > 0.5) {
                const double dot = (v.x * toRaw.x + v.y * toRaw.y) / (speed * distToRaw);
                isCollinear = (dot > 0.4);
            }

            math::Point2D targetPt = stabPos;
            bool shouldRenderCatchup = false;
            double targetPressure = ctx.lastRawPressure;
            double targetRadiusMult = 1.0;
            double targetOpacityMult = 1.0;

            if (!atalho && isCollinear) {
                targetPt = ctx.lastRawPoint;
                shouldRenderCatchup = (distToRaw > 1.0);
                if (ctx.brushProfile.strokeTaperEnabled) {
                    targetPressure = 0.0;
                    targetRadiusMult = 0.1;
                    targetOpacityMult = 0.0;
                }
            } else if (!atalho && ctx.brushProfile.strokeTaperEnabled && speed >= 0.3) {
                // Desvio/gancho de levantamento da caneta detectado (pen-up hook off-axis).
                // Projeta estritamente ao longo da tangente física do traço
                const double taperDist = std::min(ctx.lastDab.radius * 1.5, 35.0);
                const math::Point2D tangent = v * (1.0 / speed);
                targetPt = stabPos + (tangent * taperDist);
                targetPressure = 0.0;
                targetRadiusMult = 0.1;
                targetOpacityMult = 0.0;
                shouldRenderCatchup = true;
            }

            if (shouldRenderCatchup) {
                auto mapped = brush::DynamicMapper::map(ctx.brushProfile, targetPt, targetPressure, 0.0, 0.0);
                mapped.radius *= targetRadiusMult;
                mapped.opacity *= targetOpacityMult;
                raster::Dab currentDab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, ctx.brushProfile.blendMode, mapped.color, mapped.aspectRatio);
                math::Rect2D dirty{0, 0, 0, 0};
                uint32_t dabsRendered = 0;
                renderSegment(
                    ctx.lastDab, currentDab, ctx.brushProfile, ctx.canvasTexture,
                    ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
                    ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
                    ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirty, &dabsRendered,
                    &stagesCatchup
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
        const math::Point2D releasePos = atalho ? ctx.lastRawPoint : ctx.stabilizer.getStabilizedPosition();
        endStrokeCallback({stroke::PointerEventType::Release, releasePos, 0.0, t});
    }
    ctx.hasLastRawPoint = false;
    ctx.pendingFirstSegment = false;

    if (totalCatchupDirty.width > 0 && totalCatchupDirty.height > 0) {
        return { totalCatchupDirty.x, totalCatchupDirty.y, totalCatchupDirty.width, totalCatchupDirty.height };
    }
    return { 0.0, 0.0, 0.0, 0.0 };
}

} // namespace aladyn::engine::boundary::internal
