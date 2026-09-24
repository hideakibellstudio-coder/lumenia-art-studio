#ifndef ALADYN_ENGINE_STROKE_ORCHESTRATOR_HPP
#define ALADYN_ENGINE_STROKE_ORCHESTRATOR_HPP

#include "../../../core/raster/Dab.hpp"
#include "../../../core/brush/BrushProfile.hpp"
#include "../../../core/canvas/CanvasTexture.hpp"
#include "../../../core/document/LayerStack.hpp"
#include "../../../core/canvas/TileUndoManager.hpp"
#include "../../../core/document/Compositor.hpp"
#include "../../../core/raster/SelectionMask.hpp"
#include "../../../core/engines/IBrushEngine.hpp"
#include "../../../core/math/SymmetryEngine.hpp"
#include "../../../core/stroke/VelocityTracker.hpp"
#include "../../../core/stroke/DynamicStabilizer.hpp"
#include "../../../core/stroke/PointerEvent.hpp"
#include "../../../core/telemetry/EngineTelemetry.hpp"
#include <functional>
#include <vector>

namespace aladyn::engine::boundary::internal {

struct TouchdownSample {
    math::Point2D rawPoint{0.0, 0.0};
    double pressure{1.0};
    double timestamp{0.0};
    math::Point2D stabilizedPos{0.0, 0.0};
    double normVel{0.0};
    double vel{0.0};
    double tiltX{0.0};
    double tiltY{0.0};
    double twist{0.0};
    double altitude{90.0};
    double azimuth{0.0};
};

struct RawStrokeContext {
    bool& isDrawing;
    uint32_t& segmentsRenderedInStroke;
    bool& pendingFirstSegment;
    TouchdownSample& firstSample;
    math::Point2D& strokeStartPoint;
    math::Point2D& lastRawPoint;
    double& lastRawPressure;
    bool& hasLastRawPoint;
    double& distanceCarryover;
    double& timeCarryover;
    double& lastTimestamp;
    raster::Dab& lastDab;
    stroke::VelocityTracker& velocityTracker;
    stroke::DynamicStabilizer& stabilizer;
    const brush::BrushProfile& brushProfile;
    const canvas::CanvasTexture& canvasTexture;
    engines::IBrushEngine* activeEngine;
    document::LayerStack& layerStack;
    const raster::SelectionMask& selectionMask;
    canvas::TileUndoManager& undoManager;
    document::Compositor& compositor;
    canvas::PixelBuffer& outputBuffer;
    const math::SymmetryConfig& symmetryConfig;
    telemetry::EngineTelemetryManager& telemetryManager;
    bool lowLatency{false};
    raster::Dab& splineP0;
    raster::Dab& splineP1;
    raster::Dab& splineP2;
    uint32_t& splineCount;
};

class StrokeOrchestrator {
public:
    static void renderSegment(
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
        const math::SymmetryConfig& symmetryConfig = {},
        const math::Point2D* strokeStart = nullptr,
        math::Rect2D* outDirtyBounds = nullptr,
        uint32_t* outDabsRendered = nullptr,
        telemetry::StageMetrics* outStages = nullptr,
        bool performComposite = true
    );

    static void renderSplineSegment(
        const raster::Dab& p0,
        const raster::Dab& p1,
        const raster::Dab& p2,
        const raster::Dab& p3,
        RawStrokeContext& ctx,
        math::Rect2D* outDirtyBounds = nullptr,
        uint32_t* outDabsRendered = nullptr,
        telemetry::StageMetrics* outStages = nullptr,
        bool performComposite = true
    );


    static std::vector<double> updateStrokeRaw(
        RawStrokeContext& ctx,
        double x, double y, double pressure, double timestamp,
        double tiltX = 0.0, double tiltY = 0.0, double twist = 0.0
    );

    static std::vector<double> endStrokeRaw(
        RawStrokeContext& ctx,
        std::function<void(const stroke::PointerEvent&)> endStrokeCallback,
        double endX = -1e9, double endY = -1e9
    );
};

} // namespace aladyn::engine::boundary::internal

#endif // ALADYN_ENGINE_STROKE_ORCHESTRATOR_HPP
