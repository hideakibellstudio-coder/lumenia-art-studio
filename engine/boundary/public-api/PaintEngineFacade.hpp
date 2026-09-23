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
#include "../../core/color/ColorProfile.hpp"
#include "../../core/raster/TransformEngine.hpp"
#include "../../core/math/SymmetryEngine.hpp"
#include "../../core/math/GuideSnapEngine.hpp"
#include "../../core/math/CurvilinearSnapEngine.hpp"
#include "../../core/math/SnapCandidate.hpp"
#include "../../core/math/TrajectoryEstimator.hpp"
#include "../../core/math/SnapLockStateMachine.hpp"
#include "../../core/telemetry/EngineTelemetry.hpp"
#include "../../core/canvas/MipmapPyramid.hpp"
#include <vector>
#include <memory>

namespace aladyn::engine::boundary {

namespace internal {
    struct TouchdownSample;
    struct DocumentContext;
    struct EngineStateContext;
    struct RawStrokeContext;
}

struct TelemetryData {
    double pressure{0.0};
    double velocity{0.0};
    double outputFlow{0.0};
};

class PaintEngineFacade {
public:
    PaintEngineFacade(int width, int height);
    ~PaintEngineFacade();

    void resizeCanvas(int width, int height);
    void clearCanvas();

    // ─── TROCA DE MOTOR SEM VAZAMENTO ─────────────────────────────────────
    void setEngineType(int engineTypeId);
    [[nodiscard]] int getActiveEngineType() const noexcept { return static_cast<int>(m_brushProfile.engineType); }

    // ─── GERENCIAMENTO DE CAMADAS ─────────────────────────────────────────
    int addLayer(const std::string& name = "", int insertIndex = -1);
    int addGroup(const std::string& name = "Novo Grupo", int insertIndex = -1);
    int addFilterLayer(const std::string& name, int filterTypeId, int insertIndex = -1);
    void setFilterParams(int index, const std::vector<float>& params);
    [[nodiscard]] std::vector<float> getFilterParams(int index) const;
    [[nodiscard]] int getFilterType(int index) const;
    [[nodiscard]] bool isFilterLayer(int index) const { const auto* l = m_layerStack.getDrawingLayer(index); return l && l->isFilter(); }
    [[nodiscard]] bool isGroup(int index) const { return m_layerStack.isGroup(index); }
    bool setGroupPassThrough(int index, bool passThrough);
    bool removeLayer(int index);
    int duplicateLayer(int index);
    bool selectLayer(int index) { return m_layerStack.selectLayer(index); }
    bool reorderLayer(int fromIndex, int toIndex);
    bool reorderLayers(const std::vector<int>& newOrder);
    bool setLayerParents(const std::vector<int>& parentIndices);
    bool setLayerDocumentUid(int index, uint64_t uid) {
        if (uid == 0) return false;
        if (auto* l = m_layerStack.getDrawingLayer(index)) { l->setDocumentUid(uid); return true; }
        return false;
    }
    void setLayerName(int index, const std::string& name) { if (auto* l = m_layerStack.getDrawingLayer(index)) { l->setName(name); touchDocument(); } }
    [[nodiscard]] std::string getLayerName(int index) const { const auto* l = m_layerStack.getDrawingLayer(index); return l ? l->getName() : std::string{}; }
    void setLayerOpacity(int index, double opacity);
    void setLayerBlendMode(int index, int blendModeId);
    void setLayerVisibility(int index, bool visible);
    void setLayerLock(int index, bool locked);
    void setLayerAlphaLock(int index, bool locked);
    [[nodiscard]] bool isLayerAlphaLocked(int index) const noexcept { const auto* l = m_layerStack.getDrawingLayer(index); return l ? l->isAlphaLocked() : false; }
    void setLayerClippingMask(int index, bool clipped);
    [[nodiscard]] bool isLayerClippingMask(int index) const noexcept { const auto* l = m_layerStack.getDrawingLayer(index); return l ? l->isClippingMask() : false; }
    bool flattenGroup(int index);
    bool mergeLayerDown(int index);
    void clearLayer(int index);
    void setBackgroundVisibility(bool visible);
    [[nodiscard]] bool isBackgroundVisible() const noexcept { return m_layerStack.getBackgroundLayer().isVisible(); }
    void setBackgroundColor(uint8_t r, uint8_t g, uint8_t b, uint8_t a = 255);

    bool undo();
    bool beginLayerTransaction() { return !m_isDrawing && !isTransformActive() && m_undoManager.beginStructure(m_layerStack, m_selectionMask); }
    uint64_t commitLayerTransaction() { return m_undoManager.commitStructure(m_layerStack, m_selectionMask); }
    bool cancelLayerTransaction();
    bool applyPreparedGeometry(const PaintEngineFacade& prepared);
    uint64_t getUndoStepId() const noexcept { return m_undoManager.undoId(); }
    uint64_t getRedoStepId() const noexcept { return m_undoManager.redoId(); }
    std::vector<uint64_t> getHistoryStepIds() const { return m_undoManager.historyIds(); }
    bool redo();
    [[nodiscard]] bool canUndo() const noexcept { return m_undoManager.canUndo(); }
    [[nodiscard]] bool canRedo() const noexcept { return m_undoManager.canRedo(); }
    [[nodiscard]] size_t getUndoCount() const noexcept { return m_undoManager.getUndoCount(); }
    [[nodiscard]] const std::string& getHistoryError() const noexcept { return m_undoManager.getLastError(); }
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
    void beginStrokeRaw(double x, double y, double pressure = 1.0, double timestamp = 0.0,
                        double tiltX = 0.0, double tiltY = 0.0, double twist = 0.0);
    std::vector<double> updateStrokeRaw(double x, double y, double pressure = 1.0, double timestamp = 0.0,
                                        double tiltX = 0.0, double tiltY = 0.0, double twist = 0.0);
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
    void clearSelection() noexcept { m_selectionMask.clear(); }
    void invertSelection() noexcept { m_selectionMask.invert(); }
    void selectAll() noexcept { m_selectionMask.selectAll(); }
    bool expandSelection(int radiusPx);   // Seleção -> Modificar (SelectionMorphology)
    bool contractSelection(int radiusPx);
    bool featherSelection(int radiusPx);
    [[nodiscard]] bool hasSelection() const noexcept { return m_selectionMask.hasSelection(); }
    bool deleteSelectionOnActiveLayer();
    bool fillSelectionOnActiveLayer(const raster::ColorRGBA& fillColor);
    [[nodiscard]] uint8_t* getSelectionMaskData() noexcept { return m_selectionMask.getData(); }
    [[nodiscard]] size_t getSelectionMaskSize() const noexcept { return m_selectionMask.getSizeInBytes(); }
    bool setSelectionMaskBuffer(const std::vector<uint8_t>& pixels) {
        if (pixels.size() != m_selectionMask.getSizeInBytes()) return false;
        m_selectionMask.combine(pixels, raster::SelectionMode::New);
        return true;
    }
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
    bool commitTransformDistort(const std::vector<double>& corners, int interpMode = 2);
    bool cancelTransform();
    bool flipActiveLayer(bool horizontal);
    bool rotateActiveLayer90(bool clockwise);
    [[nodiscard]] uint8_t* getTransformSourceBufferData() noexcept;

    // ── Métodos de Simetria & Guias/Réguas ──────────────────────────────────
    void setSymmetryConfig(int mode, double cx, double cy, double angleRad, int segments, bool stopAtCenter) {
        m_symmetryConfig = { static_cast<math::SymmetryMode>(mode), cx, cy, angleRad, segments, stopAtCenter };
    }
    void clearSymmetry() { m_symmetryConfig.mode = math::SymmetryMode::None; }

    void setGuideConfig(int type, double p0x, double p0y, double p1x, double p1y,
                        double p2x, double p2y, double p3x, double p3y,
                        double vpAx, double vpAy, double vpBx, double vpBy,
                        double vpCx, double vpCy, double cx, double cy,
                        double fov, double pitch, double yaw, double snapRadius);
    void clearGuide() { m_guideConfig.type = math::GuideType::None; }
    [[nodiscard]] std::vector<double> snapPoint(double rawX, double rawY, double lastX = 0.0, double lastY = 0.0, bool hasLast = false) const;

    // ── Curvilinear (6P fisheye) — Fase C2b ──────────────────────────────
    // Completa os campos de GuideConfig usados apenas por Curvilinear
    // (os demais — cx/cy/fov/pitch/yaw/snapRadius — já chegam via setGuideConfig).
    void setCurvilinearGuideConfig(double baseRadius, double density,
                                    bool showV, bool showH, bool showD,
                                    bool showGround, bool showCeiling,
                                    bool showGroundVerticals, bool showCeilingVerticals,
                                    bool showStraightVerticals,
                                    int snapMode, double snapSensitivity);

    // Candidatas curvilíneas (V/H/D) passando por (clickX,clickY), cada uma
    // codificada em 11 doubles: [kind, family, p1x,p1y, p2x,p2y, dirx,diry, cx,cy,radius].
    // Puro: não lê nem escreve estado de traço — quem chama decide quando gerar
    // (tipicamente uma vez, no início do traço) e reaproveita o resultado.
    [[nodiscard]] std::vector<double> getCurvilinearCandidates(double clickX, double clickY) const;

    // Curva primária (grade) mais próxima de (x,y); vetor vazio se nada dentro de maxDist.
    [[nodiscard]] std::vector<double> getNearestPrimaryGridCurve(double x, double y, double maxDist) const;

    // Snap curvilíneo sem estado: candidates é a lista plana já congelada pelo
    // chamador (mesma codificação de getCurvilinearCandidates); lockedIndex é
    // a curva travada na chamada anterior (-1 = nenhuma). Retorna
    // [snappedX, snappedY, newLockedIndex] — o índice deve ser persistido pelo
    // chamador e devolvido na próxima chamada.
    [[nodiscard]] std::vector<double> snapCurvilinear(
        double rawX, double rawY, double startX, double startY,
        const std::vector<double>& candidates, int lockedIndex, bool isStroking, double zoom
    ) const;

    // -- Perspectiva (1P/2P/3P/Isometric) -- Fase C3.1 -----------------------
    // Sem estado, mesmo contrato de snapCurvilinear: hasLockedDir/lockedDirX/Y
    // e a direcao travada na chamada anterior (hasLockedDir=false = nenhuma).
    // Retorna [snappedX, snappedY, newHasLockedDir(0/1), newLockedDirX, newLockedDirY]
    // -- os 3 ultimos devem ser persistidos pelo chamador e devolvidos na
    // proxima chamada.
    [[nodiscard]] std::vector<double> snapPerspective(
        double rawX, double rawY, double startX, double startY,
        bool hasLockedDir, double lockedDirX, double lockedDirY, double zoom
    ) const;

    // -- Fase D0 (redesign do motor de snap) -----------------------------
    // Componentes genericos e sem estado (SnapCandidate/TrajectoryEstimator/
    // SnapLockStateMachine), ainda nao ligados a nenhum tipo de guia real --
    // expostos aqui so para permitir cobertura de teste via pytest contra o
    // facade, mesma convencao ja usada para snapCurvilinear/snapPerspective.
    // Ver claude/proposta-redesign-motor-snap-guias.md no projeto.

    // Estima direcao+confianca a partir de uma janela de pontos recentes
    // (recentPoints, mais antigo primeiro): [x0,y0, x1,y1, ...]. Retorna
    // [dirX, dirY, confidence].
    // Instância (não static) só por consistência de chamada com o resto do
    // facade (self.facade.metodo(...) em todo teste existente) -- não lê
    // nenhum estado de m_guideConfig nem de nenhum outro membro.
    [[nodiscard]] std::vector<double> estimateTrajectory(
        const std::vector<double>& recentPoints, double zoom
    ) const;

    // Um passo da maquina de estados de trava. candidates: flat, 9 doubles
    // por candidata [kind, family, p1x,p1y, dirx,diry, centerx,centery, radius].
    // prevState: 0=Searching, 1=Tentative, 2=Committed. Retorna
    // [x, y, newState, newCandidateIndex, newStreak].
    [[nodiscard]] std::vector<double> stepSnapLock(
        double rawX, double rawY,
        double trajDirX, double trajDirY, double trajConfidence,
        const std::vector<double>& candidates,
        int prevState, int prevCandidateIndex, int prevStreak,
        double attractionRadius, double breakawayRadius, int commitFrames, double scoreSharpness
    ) const;

    // ── Métodos de Colagem de Buffers e Formas Primitivas ───────────────────
    [[nodiscard]] std::vector<int> getTransformSourceBufferSize() const;

    bool pasteRgbaBufferOnActiveLayer(int x, int y, int width, int height, const uint8_t* buffer, int blendModeId = 0, double opacity = 1.0);

    void setShapePreset(int presetId) { m_brushProfile.shapeTexture = texture::ProceduralTextures::createShapePreset(static_cast<texture::ShapePreset>(presetId)); }
    void setBrushHeightPreset(int presetId) { m_brushProfile.brushHeightTexture = texture::ProceduralTextures::createHeightPreset(static_cast<texture::HeightPreset>(presetId)); }
    void setCanvasHeightPreset(int presetId) { m_canvasTexture.canvasHeightTexture = texture::ProceduralTextures::createHeightPreset(static_cast<texture::HeightPreset>(presetId)); }

    void loadShapeTextureFromBuffer(int width, int height, const uint8_t* buffer);
    void loadBrushHeightTextureFromBuffer(int width, int height, const uint8_t* buffer);
    void loadCanvasHeightTextureFromBuffer(int width, int height, const uint8_t* buffer);

    // Opções efetivas do pipeline nativo. Elas controlam o traço e a
    // composição; não são apenas valores de preferência da UI.
    void setLowLatency(bool enabled) noexcept;
    [[nodiscard]] bool getLowLatency() const noexcept { return m_lowLatency; }
    void setLinearGamma(bool enabled);
    [[nodiscard]] bool getLinearGamma() const noexcept { return m_linearGamma; }
    void setDeepColor(bool enabled);
    [[nodiscard]] bool getDeepColor() const noexcept { return m_deepColor; }
    void setRenderOptions(bool lowLatency, bool linearGamma, bool deepColor);

    void setColorProfile(int profileId) noexcept {
        if (!color::ColorProfileManager::isProfileValid(profileId)) return;
        if (m_colorProfileId != profileId) { m_colorProfileId = profileId; touchDocument(); }
    }
    [[nodiscard]] int getColorProfile() const noexcept { return m_colorProfileId; }
    [[nodiscard]] std::string transformRgbaForProfile(const std::string& buffer, int profileId) const;
    [[nodiscard]] std::vector<uint8_t> getLayerThumbnailBuffer(int layerIdx, int thumbW, int thumbH) const;

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
    [[nodiscard]] uint64_t getDocumentGeneration() const noexcept { return m_documentGeneration; }

    [[nodiscard]] uint8_t* getRawPixelData() noexcept { return m_outputBuffer.getData(); }
    [[nodiscard]] const uint8_t* getRawPixelData() const noexcept { return m_outputBuffer.getData(); }
    [[nodiscard]] size_t getPixelDataSize() const noexcept { return m_outputBuffer.getSizeInBytes(); }

    [[nodiscard]] uint8_t* getDisplayRawPixelData() noexcept;
    [[nodiscard]] size_t getDisplayPixelDataSize() const noexcept { return m_outputBuffer.getSizeInBytes(); }
    [[nodiscard]] std::vector<uint8_t> getLayerPixelBuffer(int layerIndex) const;

    // ─── TELEMETRIA E DIAGNÓSTICO EM TEMPO REAL ──────────────────────────
    void setTelemetryEnabled(bool enabled) noexcept { m_telemetryManager.setEnabled(enabled); }
    [[nodiscard]] bool isTelemetryEnabled() const noexcept { return m_telemetryManager.isEnabled(); }
    void setDetailedLoggingEnabled(bool detailed) noexcept { m_telemetryManager.setDetailedLogging(detailed); }
    [[nodiscard]] bool isDetailedLoggingEnabled() const noexcept { return m_telemetryManager.isDetailedLogging(); }
    [[nodiscard]] telemetry::RealTimeStrokeMetrics getTelemetrySnapshot() const;
    void resetTelemetry() noexcept { m_telemetryManager.reset(); }
    // ─── FASE 4: ESCALABILIDADE DE MEMÓRIA & SCRATCH DISK ─────────────────────
    size_t compressInactiveLayers();
    size_t decompressAllLayers();
    [[nodiscard]] double getTotalTileMemoryMB() const;
    [[nodiscard]] size_t getCowSharedTilesCount() const;
    void setScratchDiskEnabled(bool enabled) { m_undoManager.setScratchDiskEnabled(enabled); }
    [[nodiscard]] bool isScratchDiskEnabled() const noexcept { return m_undoManager.isScratchDiskEnabled(); }
    [[nodiscard]] size_t getUndoPagedStepsCount() const noexcept { return m_undoManager.getPagedStepsCount(); }
    [[nodiscard]] double getScratchDiskUsageMB() const noexcept {
        return static_cast<double>(m_undoManager.getScratchDiskBytes()) / (1024.0 * 1024.0);
    }
    // ─── FASE 5: DIRTY TILE STREAMING & VIEWPORT ──────────────────────────────
    [[nodiscard]] std::vector<std::pair<int, int>> getDirtyTileIndices() const {
        if (const auto* layer = m_layerStack.getActiveLayer()) {
            return layer->getTileGrid().getDirtyTileIndices();
        }
        return {};
    }
    void clearDirtyTiles() noexcept {
        if (auto* layer = m_layerStack.getActiveLayer()) {
            layer->getTileGrid().clearDirtyFlags();
        }
    }
    // ─── VIEWPORT MIPMAPPING & LOD ANTI-ALIASING ──────────────────────────────
    [[nodiscard]] uint8_t* getDisplayPixelBufferLOD(int level, int& outW, int& outH) noexcept {
        uint8_t* baseData = getDisplayRawPixelData();
        (void)baseData;
        if (const auto* layer = m_layerStack.getActiveLayer()) {
            if (!layer->getTileGrid().getDirtyTileIndices().empty()) {
                m_mipmapPyramid.markDirty();
            }
        }
        // Build from the same buffer returned to the display.  With the
        // default sRGB profile getDisplayRawPixelData() aliases outputBuffer;
        // using the untouched display scratch buffer would otherwise yield a
        // stale white pyramid.
        const auto& displayBase = (m_colorProfileId == 0) ? m_outputBuffer : m_displayBuffer;
        return m_mipmapPyramid.getLODData(level, displayBase, outW, outH);
    }
    [[nodiscard]] static int getBestLODLevel(double zoom) noexcept {
        return canvas::MipmapPyramid::getBestLODLevel(zoom);
    }
    [[nodiscard]] static double getLODScale(int level) noexcept {
        return canvas::MipmapPyramid::getLODScale(level);
    }
    void markLODDirty() noexcept {
        m_mipmapPyramid.markDirty();
    }

private:
    // Contextos agregados que este facade entrega aos orquestradores de
    // internal/. Declarados com tipo de retorno incompleto de proposito: o
    // header publico nao inclui internal/ -- so o .cpp, que e' quem constroi e
    // consome os contextos. Nunca armazene um deles: resizeCanvas() e o resync
    // de historico trocam buffers e compositor por instancias novas.
    internal::DocumentContext    docContext() noexcept;
    internal::EngineStateContext stateContext() noexcept;
    internal::RawStrokeContext   strokeContext() noexcept;
    void touchDocument() noexcept { ++m_documentGeneration; m_mipmapPyramid.markDirty(); }
    bool touchedIf(bool changed) noexcept { if (changed) touchDocument(); return changed; }
    void initEngine(brush::EngineType type);

    int m_width;
    int m_height;
    bool m_isDrawing{false};
    int m_colorProfileId{0};
    bool m_lowLatency{false};
    bool m_linearGamma{true};
    bool m_deepColor{false};
    uint64_t m_documentGeneration{0};

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
    canvas::MipmapPyramid m_mipmapPyramid;
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

    bool                                         m_pendingFirstSegment{false};
    std::unique_ptr<internal::TouchdownSample>   m_firstSample;

    telemetry::EngineTelemetryManager m_telemetryManager;
};

} // namespace aladyn::engine::boundary

#endif // ALADYN_ENGINE_PAINT_ENGINE_FACADE_HPP
