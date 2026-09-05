#ifndef ALADYN_ENGINE_PAINT_ENGINE_FACADE_HPP
#define ALADYN_ENGINE_PAINT_ENGINE_FACADE_HPP

#include "../../core/math/Point2D.hpp"
#include "../../core/stroke/PointerEvent.hpp"
#include "../../core/stroke/VelocityTracker.hpp"
#include "../../core/stroke/DynamicStabilizer.hpp"
#include "../../core/brush/BrushProfile.hpp"
#include "../../core/canvas/CanvasTexture.hpp"
#include "../../core/math/Rect2D.hpp"
#include "../../core/canvas/PixelBuffer.hpp"
#include "../../core/canvas/CanvasTexture.hpp"
#include "../../core/canvas/TileUndoManager.hpp"
#include "../../core/document/Layer.hpp"
#include "../../core/document/LayerStack.hpp"
#include "../../core/document/Compositor.hpp"
#include "../../core/texture/ProceduralTextures.hpp"
#include "../../core/engines/IBrushEngine.hpp"
#include "../../core/raster/SelectionMask.hpp"
#include "../../core/raster/TransformEngine.hpp"
#include "../../core/math/SymmetryEngine.hpp"
#include "../../core/math/GuideSnapEngine.hpp"
#include "../../core/telemetry/EngineTelemetry.hpp"
#include <vector>
#include <memory>

namespace aladyn::engine::boundary {

struct TelemetryData {
    double pressure{0.0};
    double velocity{0.0};
    double outputFlow{0.0};
};

class PaintEngineFacade {
public:
    PaintEngineFacade(int width, int height);

    void resizeCanvas(int width, int height);
    void clearCanvas();

    // ─── TROCA DE MOTOR SEM VAZAMENTO ─────────────────────────────────────
    void setEngineType(int engineTypeId);
    [[nodiscard]] int getActiveEngineType() const noexcept;

    // ─── GERENCIAMENTO DE CAMADAS ─────────────────────────────────────────
    int addLayer(const std::string& name = "", int insertIndex = -1);
    int addGroup(const std::string& name = "Novo Grupo", int insertIndex = -1);
    int addFilterLayer(const std::string& name, int filterTypeId, int insertIndex = -1);
    void setFilterParams(int index, const std::vector<float>& params);
    [[nodiscard]] std::vector<float> getFilterParams(int index) const;
    [[nodiscard]] int getFilterType(int index) const;
    [[nodiscard]] bool isFilterLayer(int index) const;
    bool isGroup(int index) const;
    bool setGroupPassThrough(int index, bool passThrough);
    bool removeLayer(int index);
    int duplicateLayer(int index);
    bool selectLayer(int index);
    bool reorderLayer(int fromIndex, int toIndex);
    bool reorderLayers(const std::vector<int>& newOrder);
    bool setLayerParents(const std::vector<int>& parentIndices);
    void setLayerName(int index, const std::string& name);
    void setLayerOpacity(int index, double opacity);
    void setLayerBlendMode(int index, int blendModeId);
    void setLayerVisibility(int index, bool visible);
    void setLayerLock(int index, bool locked);
    void setLayerAlphaLock(int index, bool locked);
    [[nodiscard]] bool isLayerAlphaLocked(int index) const noexcept;
    void setLayerClippingMask(int index, bool clipped);
    [[nodiscard]] bool isLayerClippingMask(int index) const noexcept;
    bool flattenGroup(int index);
    bool mergeLayerDown(int index);
    void clearLayer(int index);
    void setBackgroundVisibility(bool visible);
    [[nodiscard]] bool isBackgroundVisible() const noexcept;
    void setBackgroundColor(uint8_t r, uint8_t g, uint8_t b, uint8_t a = 255);

    bool undo();
    bool redo();
    [[nodiscard]] bool canUndo() const noexcept { return m_undoManager.canUndo(); }
    [[nodiscard]] bool canRedo() const noexcept { return m_undoManager.canRedo(); }
    [[nodiscard]] size_t getUndoCount() const noexcept { return m_undoManager.getUndoCount(); }
    [[nodiscard]] size_t getRedoCount() const noexcept { return m_undoManager.getRedoCount(); }
    void setUndoMemoryLimitMB(size_t mb) noexcept { m_undoManager.setMaxMemoryMB(mb); }
    [[nodiscard]] size_t getUndoMemoryLimitMB() const noexcept { return m_undoManager.getMaxMemoryMB(); }
    void setUndoMaxSteps(size_t steps) noexcept { m_undoManager.setMaxSteps(steps); }
    [[nodiscard]] size_t getUndoMaxSteps() const noexcept { return m_undoManager.getMaxSteps(); }

    [[nodiscard]] int getActiveLayerIndex() const noexcept { return m_layerStack.getActiveIndex(); }
    [[nodiscard]] int getDrawingLayerCount() const noexcept { return static_cast<int>(m_layerStack.getDrawingLayerCount()); }

    void beginStroke(const stroke::PointerEvent& event);
    TelemetryData updateStroke(const stroke::PointerEvent& event);
    void endStroke(const stroke::PointerEvent& event);

    // ── Fast-Path Nativo Direto (Zero Alocações / Zero Overhead Python) ────
    void beginStrokeRaw(double x, double y, double pressure = 1.0, double timestamp = 0.0);
    std::vector<double> updateStrokeRaw(double x, double y, double pressure = 1.0, double timestamp = 0.0);
    std::vector<double> endStrokeRaw();

    bool floodFill(int seedX, int seedY, const raster::ColorRGBA& fillColor,
                   int tolerance = 20, bool contiguous = true,
                   int expandPx = 1, int gapClosingPx = 0, bool antiAliasing = true,
                   bool sampleAllLayers = true);

    bool magicWandSelect(int seedX, int seedY, int tolerance = 20, bool contiguous = true,
                         int expandPx = 0, bool antiAliasing = true, int mode = 0,
                         bool sampleAllLayers = true);
    bool selectRect(int x, int y, int w, int h, int mode = 0, int featherPx = 0, int cornerRadiusPx = 0);
    bool selectEllipse(int cx, int cy, int rx, int ry, int mode = 0, bool antiAliasing = true, int featherPx = 0);
    bool selectPolygon(const std::vector<int>& flatPoints, int mode = 0, bool antiAliasing = true, int featherPx = 0);
    void clearSelection() noexcept;
    void invertSelection() noexcept;
    void selectAll() noexcept;
    [[nodiscard]] bool hasSelection() const noexcept;
    bool deleteSelectionOnActiveLayer();
    bool fillSelectionOnActiveLayer(const raster::ColorRGBA& fillColor);
    [[nodiscard]] uint8_t* getSelectionMaskData() noexcept;
    [[nodiscard]] size_t getSelectionMaskSize() const noexcept;
    [[nodiscard]] std::vector<int> getSelectionBounds() const;
    [[nodiscard]] std::vector<int> getSelectionContourSegments() const;
    [[nodiscard]] std::vector<std::vector<int>> getSelectionContourLoops() const;
    [[nodiscard]] raster::SelectionMask& getSelectionMask() noexcept { return m_selectionMask; }
    [[nodiscard]] const raster::SelectionMask& getSelectionMask() const noexcept { return m_selectionMask; }

    // ── Métodos de Transformação Livre (Transform Tool) ─────────────────────
    bool beginTransform();
    [[nodiscard]] bool isTransformActive() const noexcept;
    [[nodiscard]] std::vector<double> getTransformSourceBounds() const;
    [[nodiscard]] std::vector<double> getTransformPivot() const;
    bool commitTransform(double dx, double dy, double scaleX, double scaleY,
                         double rotationDeg, double pivotX, double pivotY,
                         bool flipH, bool flipV, int interpMode = 2);
    bool cancelTransform();
    bool flipActiveLayer(bool horizontal);
    bool rotateActiveLayer90(bool clockwise);
    [[nodiscard]] uint8_t* getTransformSourceBufferData() noexcept;

    // ── Métodos de Simetria & Guias/Réguas ──────────────────────────────────
    void setSymmetryConfig(int mode, double cx, double cy, double angleRad, int segments, bool stopAtCenter);
    void clearSymmetry();
    [[nodiscard]] const math::SymmetryConfig& getSymmetryConfig() const noexcept { return m_symmetryConfig; }

    void setGuideConfig(int type, double p0x, double p0y, double p1x, double p1y,
                        double p2x, double p2y, double p3x, double p3y,
                        double vpAx, double vpAy, double vpBx, double vpBy,
                        double vpCx, double vpCy, double cx, double cy,
                        double fov, double pitch, double yaw, double snapRadius);
    void clearGuide();
    [[nodiscard]] const math::GuideConfig& getGuideConfig() const noexcept { return m_guideConfig; }
    [[nodiscard]] std::vector<double> snapPoint(double rawX, double rawY, double lastX = 0.0, double lastY = 0.0, bool hasLast = false) const;

    // ── Métodos de Colagem de Buffers e Formas Primitivas ───────────────────
    [[nodiscard]] std::vector<int> getTransformSourceBufferSize() const;
    [[nodiscard]] raster::TransformEngine& getTransformEngine() noexcept { return m_transformEngine; }

    bool pasteRgbaBufferOnActiveLayer(int x, int y, int width, int height, const uint8_t* buffer, int blendModeId = 0, double opacity = 1.0);

    void setShapePreset(int presetId);
    void setBrushHeightPreset(int presetId);
    void setCanvasHeightPreset(int presetId);

    void loadShapeTextureFromBuffer(int width, int height, const uint8_t* buffer);
    void loadBrushHeightTextureFromBuffer(int width, int height, const uint8_t* buffer);
    void loadCanvasHeightTextureFromBuffer(int width, int height, const uint8_t* buffer);

    void setColorProfile(int profileId) noexcept;
    [[nodiscard]] int getColorProfile() const noexcept { return m_colorProfileId; }
    void applyActiveColorProfile(uint8_t* targetBuffer, size_t numPixels) const noexcept;

    [[nodiscard]] brush::BrushProfile& getBrushProfile() noexcept { return m_brushProfile; }
    [[nodiscard]] const brush::BrushProfile& getBrushProfile() const noexcept { return m_brushProfile; }

    [[nodiscard]] canvas::CanvasTexture& getCanvasTexture() noexcept { return m_canvasTexture; }
    [[nodiscard]] const canvas::CanvasTexture& getCanvasTexture() const noexcept { return m_canvasTexture; }

    [[nodiscard]] stroke::DynamicStabilizer& getStabilizer() noexcept { return m_stabilizer; }
    [[nodiscard]] const stroke::DynamicStabilizer& getStabilizer() const noexcept { return m_stabilizer; }

    [[nodiscard]] document::LayerStack& getLayerStack() noexcept { return m_layerStack; }
    [[nodiscard]] const document::LayerStack& getLayerStack() const noexcept { return m_layerStack; }

    [[nodiscard]] int getWidth() const noexcept { return m_width; }
    [[nodiscard]] int getHeight() const noexcept { return m_height; }

    [[nodiscard]] uint8_t* getRawPixelData() noexcept { return m_outputBuffer.getData(); }
    [[nodiscard]] const uint8_t* getRawPixelData() const noexcept { return m_outputBuffer.getData(); }
    [[nodiscard]] size_t getPixelDataSize() const noexcept { return m_outputBuffer.getSizeInBytes(); }

    [[nodiscard]] uint8_t* getDisplayRawPixelData() noexcept;
    [[nodiscard]] size_t getDisplayPixelDataSize() const noexcept { return m_outputBuffer.getSizeInBytes(); }

    // ─── TELEMETRIA E DIAGNÓSTICO EM TEMPO REAL ──────────────────────────
    void setTelemetryEnabled(bool enabled) noexcept { m_telemetryManager.setEnabled(enabled); }
    [[nodiscard]] bool isTelemetryEnabled() const noexcept { return m_telemetryManager.isEnabled(); }
    void setDetailedLoggingEnabled(bool detailed) noexcept { m_telemetryManager.setDetailedLogging(detailed); }
    [[nodiscard]] bool isDetailedLoggingEnabled() const noexcept { return m_telemetryManager.isDetailedLogging(); }
    [[nodiscard]] telemetry::RealTimeStrokeMetrics getTelemetrySnapshot() const;
    void resetTelemetry() noexcept { m_telemetryManager.reset(); }
    [[nodiscard]] telemetry::EngineTelemetryManager& getTelemetryManager() noexcept { return m_telemetryManager; }
    [[nodiscard]] const telemetry::EngineTelemetryManager& getTelemetryManager() const noexcept { return m_telemetryManager; }

private:
    void renderStrokeSegment(const raster::Dab& startDab, const raster::Dab& endDab);
    void initEngine(brush::EngineType type);

    int m_width;
    int m_height;
    bool m_isDrawing{false};
    int m_colorProfileId{0};

    stroke::VelocityTracker   m_velocityTracker;
    stroke::DynamicStabilizer m_stabilizer;
    brush::BrushProfile       m_brushProfile;
    canvas::CanvasTexture     m_canvasTexture;

    std::unique_ptr<engines::IBrushEngine> m_activeEngine;

    raster::Dab m_lastDab;

    document::LayerStack m_layerStack;
    document::Compositor m_compositor;
    canvas::PixelBuffer  m_outputBuffer;
    mutable canvas::PixelBuffer m_displayBuffer;
    raster::SelectionMask m_selectionMask;
    raster::TransformEngine m_transformEngine;
    canvas::TileUndoManager m_undoManager;

    math::SymmetryConfig m_symmetryConfig;
    math::GuideConfig    m_guideConfig;
    math::Point2D        m_strokeStartPoint{0.0, 0.0};
    math::Point2D        m_lastRawPoint{0.0, 0.0};
    double               m_lastRawPressure{1.0};
    bool                 m_hasLastRawPoint{false};
    double               m_distanceCarryover{0.0};
    uint32_t             m_segmentsRenderedInStroke{0};

    struct TouchdownSample {
        math::Point2D rawPoint{0.0, 0.0};
        double pressure{1.0};
        double timestamp{0.0};
        math::Point2D stabilizedPos{0.0, 0.0};
        double normVel{0.0};
        double vel{0.0};
    };
    bool            m_pendingFirstSegment{false};
    TouchdownSample m_firstSample{};

    telemetry::EngineTelemetryManager m_telemetryManager;
};

} // namespace aladyn::engine::boundary

#endif // ALADYN_ENGINE_PAINT_ENGINE_FACADE_HPP
