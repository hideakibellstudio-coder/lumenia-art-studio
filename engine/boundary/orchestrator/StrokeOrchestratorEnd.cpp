// StrokeOrchestrator::endStrokeRaw -- separado de StrokeOrchestrator.cpp em
// 2026-09-22 (teto ARCcC de 450 linhas). Corpo movido sem alteração.
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


        if (ctx.hasLastRawPoint && ctx.segmentsRenderedInStroke > 0) {
            const utils::Point2D stabPos = shortcut ? ctx.lastRawPoint : ctx.stabilizer.getStabilizedPosition();
            const utils::Point2D v = shortcut ? (ctx.lastRawPoint - ctx.lastDab.position) : ctx.stabilizer.getLastMovementDelta();
            const double speed = v.length();
            const utils::Point2D toRaw = ctx.lastRawPoint - stabPos;
            const double distToRaw = toRaw.length();

            // 1. Catch-up para alcançar a posição real de soltura quando o estabilizador ficou para trás
            if (!shortcut && distToRaw > 1.0) {
                auto mappedCatchup = brush::DynamicMapper::map(ctx.brushProfile, ctx.lastRawPoint, ctx.lastRawPressure, 0.0, 0.0);
                utils::Dab catchupDab(mappedCatchup.position, mappedCatchup.radius, mappedCatchup.opacity, mappedCatchup.pressure, mappedCatchup.angle, ctx.brushProfile.blendMode, mappedCatchup.color, mappedCatchup.aspectRatio);
                utils::Rect2D dirty{0, 0, 0, 0};
                uint32_t dabsRendered = 0;
                renderSegment(
                    ctx.lastDab, catchupDab, ctx.brushProfile, ctx.canvasTexture,
                    ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
                    ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
                    ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirty, &dabsRendered,
                    &stagesCatchup
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

                auto mapped = brush::DynamicMapper::map(ctx.brushProfile, targetPt, 0.0, 0.0, 0.0);
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
