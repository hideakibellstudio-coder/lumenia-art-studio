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
    int addLayer(const std::string& name = "");
    int addGroup(const std::string& name = "Novo Grupo");
    int addFilterLayer(const std::string& name, int filterTypeId);
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

    [[nodiscard]] int getActiveLayerIndex() const noexcept { return m_layerStack.getActiveIndex(); }
    [[nodiscard]] int getDrawingLayerCount() const noexcept { return static_cast<int>(m_layerStack.getDrawingLayerCount()); }

    void beginStroke(const stroke::PointerEvent& event);
    TelemetryData updateStroke(const stroke::PointerEvent& event);
    void endStroke(const stroke::PointerEvent& event);

    void setShapePreset(int presetId);
    void setBrushHeightPreset(int presetId);
    void setCanvasHeightPreset(int presetId);

    void loadShapeTextureFromBuffer(int width, int height, const uint8_t* buffer);
    void loadBrushHeightTextureFromBuffer(int width, int height, const uint8_t* buffer);
    void loadCanvasHeightTextureFromBuffer(int width, int height, const uint8_t* buffer);

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

private:
    void renderStrokeSegment(const raster::Dab& startDab, const raster::Dab& endDab);
    void initEngine(brush::EngineType type);

    int m_width;
    int m_height;
    bool m_isDrawing{false};

    stroke::VelocityTracker   m_velocityTracker;
    stroke::DynamicStabilizer m_stabilizer;
    brush::BrushProfile       m_brushProfile;
    canvas::CanvasTexture     m_canvasTexture;

    std::unique_ptr<engines::IBrushEngine> m_activeEngine;

    raster::Dab m_lastDab;

    document::LayerStack m_layerStack;
    document::Compositor m_compositor;
    canvas::PixelBuffer  m_outputBuffer;
    canvas::TileUndoManager m_undoManager;
};

} // namespace aladyn::engine::boundary

#endif // ALADYN_ENGINE_PAINT_ENGINE_FACADE_HPP
