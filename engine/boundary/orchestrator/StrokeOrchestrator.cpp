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
    double x, double y, double rawPressure, double timestamp,
    double tiltX, double tiltY, double twist
) {
    if (!ctx.isDrawing) return {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    // Curva global de entrada: tudo daqui para frente (estabilizador, curvas do pincel) lê a pressão calibrada.
    const double pressure = ctx.pressureCalibration.apply(rawPressure);
    // The same sample again (the canvas repeats a mouse held still so the stabilizer keeps
    // settling, 2026-10-09): it moves the stabilizer but must not stamp the same spot again.
    const bool repeatedSample = ctx.hasLastRawPoint && ctx.lastRawPoint == utils::Point2D{x, y}
        && ctx.lastRawPressure == pressure && !ctx.brushProfile.timeSpacingEnabled;
    ctx.lastRawPoint = {x, y};
    ctx.hasLastRawPoint = true;
    ctx.lastRawPressure = pressure;

    auto tKinematicsStart = std::chrono::high_resolution_clock::now();

    double t = timestamp;
    if (t <= 0.0 || (ctx.lastTimestamp > 0.0 && t < ctx.lastTimestamp - 1.0)) {
        t = (ctx.lastTimestamp > 0.0)
            ? (ctx.lastTimestamp + stroke::DynamicStabilizer::kNominalEventSeconds)
            : std::chrono::duration<double>(std::chrono::high_resolution_clock::now().time_since_epoch()).count();
    }

    const double vel = ctx.velocityTracker.update({x, y}, t);
    const double normVel = ctx.velocityTracker.getNormalizedVelocity(1500.0);
    const bool shortcut = useLatencyShortcut(ctx);
    const utils::Point2D pos = shortcut ? utils::Point2D{x, y} : ctx.stabilizer.updateAt({x, y}, pressure, normVel, t);
    const double effectivePressure = shortcut ? pressure : ctx.stabilizer.getStabilizedPressure();
    if (repeatedSample && ctx.splineCount >= 3 && pos.distanceTo(ctx.lastDab.position) < 0.35) {
        ctx.lastTimestamp = t;
        return {0.0, 0.0, 0.0, 0.0, x, y, pressure, vel, ctx.lastDab.opacity};
    }

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

    ctx.lastPose = {altitude, azimuth, twist};
    auto mapped = brush::DynamicMapper::map(
        ctx.brushProfile, pos, effectivePressure, normVel, twist, altitude, azimuth
    );
    utils::Dab currentDab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, ctx.brushProfile.blendMode, mapped.color, mapped.aspectRatio);

    auto tKinematicsEnd = std::chrono::high_resolution_clock::now();
    double timeKinematicsUs = std::chrono::duration<double, std::micro>(tKinematicsEnd - tKinematicsStart).count();

    utils::Rect2D dirty{0, 0, 0, 0};
    uint32_t dabsRendered = 0;
    auto tStart = std::chrono::high_resolution_clock::now();
    telemetry::StageMetrics totalStages{};

    utils::Rect2D dirtyCurrent{0, 0, 0, 0};
    uint32_t dabsCurrent = 0;
    telemetry::StageMetrics stagesCurrent{};

    // Interpolação linear de alta fidelidade entre dabs consecutivos.
    // Elimina arestas poligonais, overshoots e o ziguezague agressivo em curvas gerado pelo
    // 4º nó extrapolado (2*P2 - P1), e elimina o gancho inicial provocado pelo desalinhamento artificial de P0.
    renderSegment(
        ctx.lastDab, currentDab, ctx.brushProfile, ctx.canvasTexture,
        ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
        ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
        ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirtyCurrent, &dabsCurrent,
        &stagesCurrent, true, &ctx.strokeMix
    );
    ctx.splineP0 = ctx.lastDab;
    ctx.splineP1 = currentDab;
    ctx.splineCount = 3;
    ctx.pendingFirstSegment = false;


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
                    stationaryCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirtyStationary, &dabsStationary,
                    nullptr, true, &ctx.strokeMix
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
