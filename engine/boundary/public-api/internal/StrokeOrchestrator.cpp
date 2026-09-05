#include "StrokeOrchestrator.hpp"
#include "../../../core/raster/DabInterpolator.hpp"
#include "../../../core/raster/DabRenderer.hpp"
#include "../../../core/raster/PixelContext.hpp"
#include "../../../core/brush/DynamicMapper.hpp"
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>

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
    const math::Point2D pos = ctx.stabilizer.update({x, y}, normVel);

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

    // Amostra 1 do movimento (P1): Reter para confirmar alinhamento direcional com P2
    if (ctx.segmentsRenderedInStroke == 0 && !ctx.pendingFirstSegment) {
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
        ctx.pendingFirstSegment = true;
        ctx.segmentsRenderedInStroke = 1;
        return { 0.0, 0.0, 0.0, 0.0, x, y, pressure, vel, ctx.lastDab.opacity };
    }

    auto tKinematicsEnd = std::chrono::high_resolution_clock::now();
    double timeKinematicsUs = std::chrono::duration<double, std::micro>(tKinematicsEnd - tKinematicsStart).count();

    math::Rect2D dirty{0, 0, 0, 0};
    uint32_t dabsRendered = 0;
    auto tStart = std::chrono::high_resolution_clock::now();
    telemetry::StageMetrics totalStages{};

    // Amostra 2 do movimento (P2 com P1 pendente):
    // Avalia o alinhamento entre o pouso (P0 -> P1) e a trajetória da curva (P1 -> P2)
    if (ctx.pendingFirstSegment) {
        const math::Point2D p0 = ctx.strokeStartPoint;
        const math::Point2D p1 = ctx.firstSample.rawPoint;
        const math::Point2D p2 = {x, y};

        const math::Point2D v01 = p1 - p0;
        const math::Point2D v12 = p2 - p1;
        const double len01 = v01.length();
        const double len12 = v12.length();

        if (len01 > 0.5 && len12 > 0.5) {
            const double dot = (v01.x * v12.x + v01.y * v12.y) / (len01 * len12);
            if (dot < 0.4) {
                // Deflexão de impacto detectada no pouso do stylus:
                // Realinha o ponto inicial P0 tangencialmente para trás na direção de v12
                const math::Point2D u12 = v12 * (1.0 / len12);
                const math::Point2D alignedP0 = p1 - (u12 * len01);
                ctx.strokeStartPoint = alignedP0;
                ctx.stabilizer.reanchorInitialPosition(alignedP0);

                auto mappedP0 = brush::DynamicMapper::map(ctx.brushProfile, alignedP0, ctx.lastDab.pressure, 0.0, 0.0);
                ctx.lastDab = raster::Dab(mappedP0.position, mappedP0.radius, mappedP0.opacity, mappedP0.pressure, mappedP0.angle, ctx.brushProfile.blendMode, mappedP0.color, mappedP0.aspectRatio);
            }
        }

        double strokeAngle1 = 0.0;
        const double dx1 = ctx.firstSample.stabilizedPos.x - ctx.lastDab.position.x;
        const double dy1 = ctx.firstSample.stabilizedPos.y - ctx.lastDab.position.y;
        if (dx1 * dx1 + dy1 * dy1 > 0.01) {
            strokeAngle1 = std::atan2(dy1, dx1) * (180.0 / 3.14159265358979323846);
            if (strokeAngle1 < 0.0) strokeAngle1 += 360.0;
        }

        // Renderiza o segmento 1 (P0 -> P1 estabilizado)
        auto mapped1 = brush::DynamicMapper::map(
            ctx.brushProfile, ctx.firstSample.stabilizedPos, ctx.firstSample.pressure,
            ctx.firstSample.normVel, strokeAngle1, ctx.firstSample.twist,
            ctx.firstSample.altitude, ctx.firstSample.azimuth
        );
        raster::Dab dab1(mapped1.position, mapped1.radius, mapped1.opacity, mapped1.pressure, mapped1.angle, ctx.brushProfile.blendMode, mapped1.color, mapped1.aspectRatio);
        math::Rect2D dirty1{0, 0, 0, 0};
        uint32_t dabs1 = 0;
        telemetry::StageMetrics stages1{};
        renderSegment(
            ctx.lastDab, dab1, ctx.brushProfile, ctx.canvasTexture,
            ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
            ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
            ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirty1, &dabs1,
            &stages1
        );
        totalStages.timeInterpolationUs += stages1.timeInterpolationUs;
        totalStages.timeRasterDabUs += stages1.timeRasterDabUs;
        totalStages.timeUndoRecordUs += stages1.timeUndoRecordUs;
        totalStages.timeCompositeUs += stages1.timeCompositeUs;
        totalStages.tilesRecorded += stages1.tilesRecorded;
        totalStages.tilesComposited += stages1.tilesComposited;

        ctx.lastDab = dab1;
        dirty = dirty1;
        dabsRendered += dabs1;
        ctx.pendingFirstSegment = false;
        ++ctx.segmentsRenderedInStroke;
    }

    double strokeAngle = 0.0;
    const double dx = pos.x - ctx.lastDab.position.x;
    const double dy = pos.y - ctx.lastDab.position.y;
    if (dx * dx + dy * dy > 0.01) {
        strokeAngle = std::atan2(dy, dx) * (180.0 / 3.14159265358979323846);
        if (strokeAngle < 0.0) strokeAngle += 360.0;
    }

    // Renderiza o segmento atual
    auto mapped = brush::DynamicMapper::map(
        ctx.brushProfile, pos, pressure, normVel, strokeAngle, twist, altitude, azimuth
    );
    raster::Dab currentDab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, ctx.brushProfile.blendMode, mapped.color, mapped.aspectRatio);
    math::Rect2D dirtyCurrent{0, 0, 0, 0};
    uint32_t dabsCurrent = 0;
    telemetry::StageMetrics stagesCurrent{};
    renderSegment(
        ctx.lastDab, currentDab, ctx.brushProfile, ctx.canvasTexture,
        ctx.activeEngine, ctx.layerStack, ctx.selectionMask,
        ctx.undoManager, ctx.compositor, ctx.outputBuffer, ctx.canvasTexture.backgroundColor,
        ctx.distanceCarryover, ctx.symmetryConfig, &ctx.strokeStartPoint, &dirtyCurrent, &dabsCurrent,
        &stagesCurrent
    );
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
        double lag = pos.distanceTo(math::Point2D{x, y});
        ctx.telemetryManager.onSegmentRenderedDetailed(latUs, timeKinematicsUs, totalStages, pressure, mapped.pressure, vel, lag);
    }

    ctx.lastDab = currentDab;
    return { dirty.x, dirty.y, dirty.width, dirty.height, x, y, pressure, vel, currentDab.opacity };
}

std::vector<double> StrokeOrchestrator::endStrokeRaw(
    RawStrokeContext& ctx,
    std::function<void(const stroke::PointerEvent&)> endStrokeCallback
) {
    math::Rect2D totalCatchupDirty{0, 0, 0, 0};
    telemetry::StageMetrics stagesCatchup{};

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
            const math::Point2D stabPos = ctx.stabilizer.getStabilizedPosition();
            const math::Point2D v = ctx.stabilizer.getLastMovementDelta();
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

            if (isCollinear) {
                targetPt = ctx.lastRawPoint;
                shouldRenderCatchup = (distToRaw > 1.0);
                if (ctx.brushProfile.strokeTaperEnabled) {
                    targetPressure = 0.0;
                    targetRadiusMult = 0.1;
                    targetOpacityMult = 0.0;
                }
            } else if (ctx.brushProfile.strokeTaperEnabled && speed >= 0.3) {
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
        endStrokeCallback({stroke::PointerEventType::Release, ctx.stabilizer.getStabilizedPosition(), 0.0, t});
    }
    ctx.hasLastRawPoint = false;
    ctx.pendingFirstSegment = false;

    if (totalCatchupDirty.width > 0 && totalCatchupDirty.height > 0) {
        return { totalCatchupDirty.x, totalCatchupDirty.y, totalCatchupDirty.width, totalCatchupDirty.height };
    }
    return { 0.0, 0.0, 0.0, 0.0 };
}

} // namespace aladyn::engine::boundary::internal
