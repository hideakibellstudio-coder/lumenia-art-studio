#include "StrokeOrchestrator.hpp"
#include "../../core/brush/DynamicMapper.hpp"
#include "../../core/raster/LargeBrushOptimizer.hpp"
#include <algorithm>
#include <cmath>
#include <chrono>
#include "StrokeLatencyPolicy.hpp"

namespace aladyn::engine::boundary::orchestrator {

using detail::useLatencyShortcut;

// endStrokeRaw vive em StrokeOrchestratorEnd.cpp (divisão de 2026-09-22: o arquivo
// tinha 484 linhas, acima do teto ARCcC de 450) e o desenho de cada segmento
// (renderSegment, renderSplineSegment) em StrokeOrchestratorSegment.cpp
// (2026-09-25: 447 linhas, na parede).

std::vector<double> StrokeOrchestrator::updateStrokeRaw(
    RawStrokeContext& ctx,
    double x, double y, double pressure, double timestamp,
    double tiltX, double tiltY, double twist
) {
    if (!ctx.isDrawing) return {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    ctx.lastRawPoint = {x, y};
    ctx.hasLastRawPoint = true;
    ctx.lastRawPressure = pressure;

    auto tKinematicsStart = std::chrono::high_resolution_clock::now();

    double t = timestamp;
    if (t <= 0.0) {
        auto now = std::chrono::high_resolution_clock::now();
        t = std::chrono::duration<double>(now.time_since_epoch()).count();
    }

    const double vel = ctx.velocityTracker.update({x, y}, t);
    const double normVel = ctx.velocityTracker.getNormalizedVelocity(1500.0);
    const bool shortcut = useLatencyShortcut(ctx);
    const utils::Point2D pos = shortcut ? utils::Point2D{x, y} : ctx.stabilizer.update({x, y}, pressure, normVel);
    const double effectivePressure = shortcut ? pressure : ctx.stabilizer.getStabilizedPressure();

    double altitude = 90.0;
    double azimuth = 0.0;
    if (std::abs(tiltX) >= 0.001 || std::abs(tiltY) >= 0.001) {
        constexpr double deg2rad = 3.14159265358979323846 / 180.0;
        constexpr double rad2deg = 180.0 / 3.14159265358979323846;
        const double tanX = std::tan(tiltX * deg2rad);
        const double tanY = std::tan(tiltY * deg2rad);
        const double tanTilt = std::sqrt(tanX * tanX + tanY * tanY);
        altitude = std::clamp(90.0 - std::atan(tanTilt) * rad2deg, 0.0, 90.0);
        double az = std::atan2(tanY, tanX) * rad2deg;
        if (az < 0.0) az += 360.0;
        azimuth = az;
    }

    double strokeAngle = 0.0;
    const double dx = pos.x - ctx.lastDab.position.x;
    const double dy = pos.y - ctx.lastDab.position.y;
    if (dx * dx + dy * dy > 0.01) {
        strokeAngle = std::atan2(dy, dx) * (180.0 / 3.14159265358979323846);
        if (strokeAngle < 0.0) strokeAngle += 360.0;
    }

    auto mapped = brush::DynamicMapper::map(
        ctx.brushProfile, pos, effectivePressure, normVel, strokeAngle, twist, altitude, azimuth
    );
    utils::Dab currentDab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, ctx.brushProfile.blendMode, mapped.color, mapped.aspectRatio);

    // Amostra 1 do movimento (P1): Reter para confirmar alinhamento direcional com P2
    if (ctx.splineCount <= 1) {
        ctx.splineP1 = currentDab;
        ctx.firstSample.rawPoint = {x, y};
        ctx.firstSample.pressure = pressure;
        ctx.firstSample.timestamp = t;
        ctx.firstSample.stabilizedPos = pos;
        ctx.firstSample.normVel = normVel;
        ctx.firstSample.vel = vel;
        ctx.firstSample.tiltX = tiltX;
        ctx.firstSample.tiltY = tiltY;
        ctx.firstSample.twist = twist;
        ctx.firstSample.altitude = altitude;
        ctx.firstSample.azimuth = azimuth;
        ctx.splineCount = 2;
        ctx.segmentsRenderedInStroke = 1;
        return { 0.0, 0.0, 0.0, 0.0, x, y, pressure, vel, ctx.lastDab.opacity };
    }

    auto tKinematicsEnd = std::chrono::high_resolution_clock::now();
    double timeKinematicsUs = std::chrono::duration<double, std::micro>(tKinematicsEnd - tKinematicsStart).count();

    utils::Rect2D dirty{0, 0, 0, 0};
    uint32_t dabsRendered = 0;
    auto tStart = std::chrono::high_resolution_clock::now();
    telemetry::StageMetrics totalStages{};

    utils::Rect2D dirtyCurrent{0, 0, 0, 0};
    uint32_t dabsCurrent = 0;
    telemetry::StageMetrics stagesCurrent{};

    // Amostra 2 do movimento (P2 com P0 e P1 em buffer):
    if (ctx.splineCount == 2) {
        ctx.splineP2 = currentDab;
        const utils::Point2D p0 = ctx.strokeStartPoint;
        const utils::Point2D p1 = ctx.splineP1.position;
        const utils::Point2D p2 = currentDab.position;

        const utils::Point2D v01 = p1 - p0;
        const utils::Point2D v12 = p2 - p1;
        const double len01 = v01.length();
        const double len12 = v12.length();

        // Correção A7: Restringe a correção de deflexão de impacto a deslizes minúsculos (<= 3px ou meio raio)
        const double maxSlipDist = std::min(3.0, ctx.lastDab.radius * 0.5);
        if (len01 > 0.5 && len01 <= maxSlipDist && len12 > 0.5) {
            const double dot = (v01.x * v12.x + v01.y * v12.y) / (len01 * len12);
            if (dot < 0.4) {
                const utils::Point2D u12 = v12 * (1.0 / len12);
                const utils::Point2D alignedP0 = p1 - (u12 * len01);
                ctx.strokeStartPoint = alignedP0;
                if (!shortcut) ctx.stabilizer.reanchorInitialPosition(alignedP0);

                auto mappedP0 = brush::DynamicMapper::map(ctx.brushProfile, alignedP0, ctx.lastDab.pressure, 0.0, 0.0);
                ctx.splineP0 = utils::Dab(mappedP0.position, mappedP0.radius, mappedP0.opacity, mappedP0.pressure, mappedP0.angle, ctx.brushProfile.blendMode, mappedP0.color, mappedP0.aspectRatio);
                ctx.lastDab = ctx.splineP0;
            }
        }

        // Renderiza segmento P0 -> P1 via Catmull-Rom centrípeta com currentDab (P2) como nó à frente
        utils::Dab dNeg1 = ctx.splineP0;
        dNeg1.position = ctx.splineP0.position * 2.0 - ctx.splineP1.position;
        renderSplineSegment(dNeg1, ctx.splineP0, ctx.splineP1, currentDab, ctx, &dirtyCurrent, &dabsCurrent, &stagesCurrent);

        // Renderiza segmento P1 -> P2 imediatamente via Catmull-Rom centrípeta com nó extrapolado
        utils::Dab dForward2 = currentDab;
        dForward2.position = currentDab.position * 2.0 - ctx.splineP1.position;
        utils::Rect2D dirtySeg2{0, 0, 0, 0};
        uint32_t dabsSeg2 = 0;
        telemetry::StageMetrics stagesSeg2{};
        renderSplineSegment(ctx.splineP0, ctx.splineP1, currentDab, dForward2, ctx, &dirtySeg2, &dabsSeg2, &stagesSeg2);

        if (dirtySeg2.width > 0 && dirtySeg2.height > 0) {
            dirtyCurrent = (dirtyCurrent.width > 0 && dirtyCurrent.height > 0) ? dirtyCurrent.united(dirtySeg2) : dirtySeg2;
        }
        dabsCurrent += dabsSeg2;
        stagesCurrent.timeInterpolationUs += stagesSeg2.timeInterpolationUs;
        stagesCurrent.timeRasterDabUs += stagesSeg2.timeRasterDabUs;
        stagesCurrent.timeUndoRecordUs += stagesSeg2.timeUndoRecordUs;
        stagesCurrent.timeCompositeUs += stagesSeg2.timeCompositeUs;
        stagesCurrent.tilesRecorded += stagesSeg2.tilesRecorded;
        stagesCurrent.tilesComposited += stagesSeg2.tilesComposited;

        ctx.splineP0 = ctx.splineP1;
        ctx.splineP1 = currentDab;
        ctx.lastDab = currentDab;
        ctx.splineCount = 3;
        ctx.pendingFirstSegment = false;
    } else {
        // Amostras subsequentes (P3, P4, ...): renderiza splineP1 -> currentDab com controle (splineP0, splineP1, currentDab, dForward)
        utils::Dab dForward = currentDab;
        dForward.position = currentDab.position * 2.0 - ctx.splineP1.position;
        renderSplineSegment(ctx.splineP0, ctx.splineP1, currentDab, dForward, ctx, &dirtyCurrent, &dabsCurrent, &stagesCurrent);

        ctx.splineP0 = ctx.splineP1;
        ctx.splineP1 = currentDab;
        ctx.lastDab = currentDab;
    }


    // Emissão temporal (Aerógrafo acumula tinta com a caneta parada - Correção B3 / Decisão D4)
    if (ctx.brushProfile.timeSpacingEnabled && ctx.brushProfile.dabsPerSecond > 0.0) {
        const double dt = (ctx.lastTimestamp > 0.0 && t > ctx.lastTimestamp) ? (t - ctx.lastTimestamp) : 0.0;
        ctx.timeCarryover += dt;
        const double interval = 1.0 / ctx.brushProfile.dabsPerSecond;
        const double distFromLast = pos.distanceTo(ctx.lastDab.position);
        // Caneta verdadeiramente imóvel: velocidade física residual (< 1.5 px/s) E sem avanço espacial
        const bool isStationary = (vel < 1.5 && normVel < 0.002) && (distFromLast < 0.5);
        if (isStationary) {
            const uint32_t maxStationaryBatch = raster::LargeBrushOptimizer::isLargeBrush(currentDab.radius) ? 2 : 8;
            uint32_t emittedInBatch = 0;
            while (ctx.timeCarryover >= interval && emittedInBatch < maxStationaryBatch) {
                ctx.timeCarryover -= interval;
                ++emittedInBatch;
                utils::Rect2D dirtyStationary{0, 0, 0, 0};
                uint32_t dabsStationary = 0;
                double stationaryCarryover = -1.0;
                renderSegment(
                    currentDab, currentDab, ctx.brushProfile, ctx.canvasTexture,
                    ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
                    ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
                    stationaryCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirtyStationary, &dabsStationary
                );
                if (dirtyStationary.width > 0 && dirtyStationary.height > 0) {
                    dirtyCurrent = (dirtyCurrent.width > 0 && dirtyCurrent.height > 0) ? dirtyCurrent.united(dirtyStationary) : dirtyStationary;
                }
                dabsCurrent += dabsStationary;
            }
            if (ctx.timeCarryover >= interval) {
                ctx.timeCarryover = std::fmod(ctx.timeCarryover, interval);
            }
        } else {
            ctx.timeCarryover = std::fmod(ctx.timeCarryover, interval);
        }
    }
    ctx.lastTimestamp = t;
    totalStages.timeInterpolationUs += stagesCurrent.timeInterpolationUs;
    totalStages.timeRasterDabUs += stagesCurrent.timeRasterDabUs;
    totalStages.timeUndoRecordUs += stagesCurrent.timeUndoRecordUs;
    totalStages.timeCompositeUs += stagesCurrent.timeCompositeUs;
    totalStages.tilesRecorded += stagesCurrent.tilesRecorded;
    totalStages.tilesComposited += stagesCurrent.tilesComposited;

    if (dirty.width > 0 && dirty.height > 0) {
        dirty = dirty.united(dirtyCurrent);
    } else {
        dirty = dirtyCurrent;
    }
    dabsRendered += dabsCurrent;
    ++ctx.segmentsRenderedInStroke;

    totalStages.dabsRendered = dabsRendered;
    totalStages.dirtyWidth = dirty.width;
    totalStages.dirtyHeight = dirty.height;
    totalStages.dirtyAreaPx = dirty.width * dirty.height;

    if (ctx.telemetryManager.isEnabled()) {
        auto tEnd = std::chrono::high_resolution_clock::now();
        double latUs = std::chrono::duration<double, std::micro>(tEnd - tStart).count() + timeKinematicsUs;
        double lag = pos.distanceTo(utils::Point2D{x, y});
        ctx.telemetryManager.onSegmentRenderedDetailed(latUs, timeKinematicsUs, totalStages, pressure, mapped.pressure, vel, lag);
    }

    ctx.lastDab = currentDab;
    return { dirty.x, dirty.y, dirty.width, dirty.height, x, y, pressure, vel, currentDab.opacity };
}

} // namespace aladyn::engine::boundary::orchestrator
