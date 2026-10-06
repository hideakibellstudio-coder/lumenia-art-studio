#include "PaintEngineFacade.hpp"
#include "../orchestrator/BrushEngineFactory.hpp"
#include "../orchestrator/BufferPasteOrchestrator.hpp"
#include "../orchestrator/DocumentStateOrchestrator.hpp"
#include "../orchestrator/FloodFillOrchestrator.hpp"
#include "../orchestrator/LayerStackOrchestrator.hpp"
#include "../orchestrator/MemoryOrchestrator.hpp"
#include "../orchestrator/RasterExportOrchestrator.hpp"
#include "../orchestrator/SelectionOrchestrator.hpp"
#include "../orchestrator/SnapOrchestrator.hpp"
#include "../orchestrator/StrokeOrchestrator.hpp"
#include "../orchestrator/StrokeSessionOrchestrator.hpp"
#include "../orchestrator/TransformOrchestrator.hpp"
#include "../../core/selection/SelectionMorphology.hpp"
#include "../../core/texture/ProceduralTextures.hpp"
#include <cstdlib>

// ─────────────────────────────────────────────────────────────────────────────
// ESTE ARQUIVO E' UMA CAMADA DE TRADUCAO, NAO DE LOGICA.
//
// Achado #6 do panorama de auditoria profunda de camadas
// (claude/panorama-motor-camadas-auditoria-profunda-2026-09-19.md): este
// arquivo tinha 929 linhas -- Zona Vermelha de LOC com excecao declarada --
// porque acumulava tres papeis: dono do estado do motor, tradutor da API
// publica e implementacao de logica que nunca virou orquestrador (guias/snap,
// exportacao raster, sessao de traco, historico, fabrica de motores).
//
// O primeiro papel continua aqui (os membros abaixo sao a instancia do motor).
// O segundo tambem, e e' o unico que deve crescer: cada metodo publico e' uma
// linha que traduz argumentos e delega. O terceiro saiu inteiro para
// internal/, seguindo o padrao que StrokeOrchestrator/SelectionOrchestrator/
// TransformOrchestrator ja estabeleciam.
//
// Regra para quem editar daqui pra frente: se um metodo deste arquivo crescer
// para mais de ~4 linhas, a logica pertence a um orquestrador em internal/.
// ─────────────────────────────────────────────────────────────────────────────

namespace aladyn::engine::boundary {

PaintEngineFacade::PaintEngineFacade(int width, int height, canvas::PixelFormat format)
    : m_width(canvas::checkedCanvasDimension(width, format)), m_height(canvas::checkedCanvasDimension(height, format)),
      m_layerStack(width, height, format),
      m_compositor(width, height, format),
      m_outputBuffer(width, height, {255, 255, 255, 255}),
      m_displayBuffer(0, 0),
      m_selectionMask(width, height) {

    // Keep the display/mipmap buffers coherent from the first frame.

#ifdef _WIN32
    _putenv("OMP_WAIT_POLICY=PASSIVE");
#endif

    m_firstSample = std::make_unique<orchestrator::TouchdownSample>();
    initEngine(brush::EngineType::Brush);
    // Nada é composto aqui: o compositor nasce com o buffer todo velho e o primeiro leitor recompõe o que lê.
}

PaintEngineFacade::~PaintEngineFacade() = default;

// ─── CONTEXTOS ────────────────────────────────────────────────────────────
// Construidos sob demanda e nunca armazenados: resizeCanvas() e
// syncHistoryGeometry() podem trocar buffers e compositor por instancias novas,
// entao qualquer contexto guardado entre chamadas ficaria pendente.

orchestrator::DocumentContext PaintEngineFacade::docContext() noexcept {
    return orchestrator::DocumentContext{
        m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor,
        m_documentGeneration, m_mipmapPyramid, m_linearGamma, m_deepColor
    };
}

orchestrator::EngineStateContext PaintEngineFacade::stateContext() noexcept {
    return orchestrator::EngineStateContext{
        docContext(), m_displayBuffer, m_selectionMask, m_undoManager, m_width, m_height
    };
}

orchestrator::RawStrokeContext PaintEngineFacade::strokeContext() noexcept {
    return orchestrator::RawStrokeContext{
        m_isDrawing, m_segmentsRenderedInStroke, m_pendingFirstSegment, *m_firstSample,
        m_strokeStartPoint, m_lastRawPoint, m_lastRawPressure, m_hasLastRawPoint,
        m_distanceCarryover, m_timeCarryover, m_lastTimestamp, m_lastDab, m_lastPose, m_velocityTracker, m_stabilizer, m_pressureCalibration,
        m_brushProfile, m_canvasTexture, m_activeEngine.get(), m_layerStack,
        m_selectionMask, m_undoManager, m_compositor, m_outputBuffer, m_strokeMix,
        m_symmetryConfig, m_telemetryManager, m_lowLatency,
        m_splineP0, m_splineP1, m_splineP2, m_splineCount
    };
}


// ─── TROCA DE MOTOR ───────────────────────────────────────────────────────

void PaintEngineFacade::initEngine(brush::EngineType type) {
    m_brushProfile.engineType = type;
    m_activeEngine = orchestrator::BrushEngineFactory::create(type);
    if (m_activeEngine) m_activeEngine->onActivate(m_brushProfile);
}

void PaintEngineFacade::setEngineType(int engineTypeId) {
    const auto type = static_cast<brush::EngineType>(engineTypeId);
    if (m_brushProfile.engineType == type) return;
    initEngine(type);
}

// ─── GERENCIAMENTO DE CAMADAS ─────────────────────────────────────────────
// Os métodos de camadas e máscaras de PaintEngineFacade vivem em PaintEngineFacadeLayers.cpp.

void PaintEngineFacade::setBackgroundVisibility(bool visible) {
    m_layerStack.getBackgroundLayer().setVisible(visible);
    const auto ctx = docContext();
    ctx.compositeAll();
    ctx.touch();
}

void PaintEngineFacade::setBackgroundColor(uint8_t r, uint8_t g, uint8_t b, uint8_t a) {
    m_canvasTexture.backgroundColor = {r, g, b, a};
    const auto ctx = docContext();
    ctx.compositeAll();
    ctx.touch();
}

// ─── ESTADO DO DOCUMENTO E HISTORICO ──────────────────────────────────────

void PaintEngineFacade::resizeCanvas(int width, int height) { orchestrator::DocumentStateOrchestrator::resizeCanvas(stateContext(), width, height); }
void PaintEngineFacade::clearCanvas() { orchestrator::DocumentStateOrchestrator::clearCanvas(docContext()); }
bool PaintEngineFacade::cancelLayerTransaction() { return orchestrator::DocumentStateOrchestrator::cancelLayerTransaction(stateContext()); }
bool PaintEngineFacade::undo() { return orchestrator::DocumentStateOrchestrator::undo(stateContext()); }
bool PaintEngineFacade::redo() { return orchestrator::DocumentStateOrchestrator::redo(stateContext()); }

bool PaintEngineFacade::applyPreparedGeometry(const PaintEngineFacade& prepared) {
    if (&prepared == this) return false;
    return orchestrator::DocumentStateOrchestrator::applyPreparedGeometry(
        stateContext(), prepared.m_layerStack, prepared.m_selectionMask);
}

// ─── CONTROLE DE PINCEL E TRAÇO ───────────────────────────────────────────

void PaintEngineFacade::beginStroke(const stroke::PointerEvent& event) {
    auto ctx = strokeContext();
    orchestrator::StrokeSessionOrchestrator::beginStroke(ctx, event);
}

TelemetryData PaintEngineFacade::updateStroke(const stroke::PointerEvent& event) {
    auto ctx = strokeContext();
    const auto s = orchestrator::StrokeSessionOrchestrator::updateStroke(ctx, event);
    return { s.pressure, s.velocity, s.outputFlow };
}

void PaintEngineFacade::endStroke(const stroke::PointerEvent& /*event*/) {
    auto ctx = strokeContext();
    if (orchestrator::StrokeSessionOrchestrator::endStroke(ctx)) docContext().touch();
}

void PaintEngineFacade::beginStrokeRaw(double x, double y, double pressure, double timestamp,
                                       double tiltX, double tiltY, double twist) {
    m_lastRawPoint = {x, y};
    m_hasLastRawPoint = true;
    m_lastRawPressure = pressure;
    m_pendingFirstSegment = false;
    m_distanceCarryover = -1.0;
    m_timeCarryover = 0.0;
    double t = timestamp;
    if (t <= 0.0) {
        auto now = std::chrono::high_resolution_clock::now();
        t = std::chrono::duration<double>(now.time_since_epoch()).count();
    }
    m_lastTimestamp = t;
    stroke::PointerEvent ev{stroke::PointerEventType::Press, {x, y}, pressure, t, tiltX, tiltY, twist};
    ev.computeAltitudeAzimuthFromTilt();
    beginStroke(ev);
    m_splineP0 = m_lastDab;
    m_splineCount = 1;
}


std::vector<double> PaintEngineFacade::updateStrokeRaw(double x, double y, double pressure, double timestamp,
                                                       double tiltX, double tiltY, double twist) {
    auto ctx = strokeContext();
    return orchestrator::StrokeOrchestrator::updateStrokeRaw(ctx, x, y, pressure, timestamp, tiltX, tiltY, twist);
}

std::vector<double> PaintEngineFacade::endStrokeRaw(double endX, double endY) {
    auto ctx = strokeContext();
    return orchestrator::StrokeOrchestrator::endStrokeRaw(ctx, [this](const stroke::PointerEvent& ev) {
        this->endStroke(ev);
    }, endX, endY);
}

telemetry::RealTimeStrokeMetrics PaintEngineFacade::getTelemetrySnapshot() const {
    return orchestrator::StrokeSessionOrchestrator::telemetrySnapshot(m_layerStack, m_undoManager, m_telemetryManager);
}

// ─── FLOOD FILL ───────────────────────────────────────────────────────────

bool PaintEngineFacade::floodFill(
    int seedX, int seedY, const utils::ColorRGBA& fillColor,
    int tolerance, bool contiguous, int expandPx, bool sampleAllLayers
) {
    const bool result = orchestrator::FloodFillOrchestrator::floodFill(
        m_outputBuffer, m_layerStack, m_undoManager, m_compositor,
        m_selectionMask, m_canvasTexture.backgroundColor,
        seedX, seedY, fillColor, tolerance, contiguous, expandPx, sampleAllLayers
    );
    if (result) docContext().touch();
    return result;
}

// ─── MÉTODOS DE SELEÇÃO & CONTORNOS ────────────────────────────────────────
bool PaintEngineFacade::magicWandSelect(int seedX, int seedY, int tolerance, bool contiguous, int expandPx, bool antiAliasing, int mode, bool sampleAllLayers) {
    if (sampleAllLayers) ensureAllFresh();  // a varinha lê as cores da composição
    return orchestrator::SelectionOrchestrator::magicWandSelect(seedX, seedY, tolerance, contiguous, expandPx, antiAliasing, mode, sampleAllLayers, m_width, m_height, m_outputBuffer, m_layerStack, m_selectionMask);
}
bool PaintEngineFacade::selectRect(int x, int y, int w, int h, int mode, int featherPx, int cornerRadiusPx) {
    return orchestrator::SelectionOrchestrator::selectRect(x, y, w, h, mode, featherPx, cornerRadiusPx, m_width, m_height, m_selectionMask);
}
bool PaintEngineFacade::selectEllipse(int cx, int cy, int rx, int ry, int mode, bool antiAliasing, int featherPx) {
    return orchestrator::SelectionOrchestrator::selectEllipse(cx, cy, rx, ry, mode, antiAliasing, featherPx, m_width, m_height, m_selectionMask);
}
bool PaintEngineFacade::selectPolygon(const std::vector<int>& flatPoints, int mode, bool antiAliasing, int featherPx) {
    return orchestrator::SelectionOrchestrator::selectPolygon(flatPoints, mode, antiAliasing, featherPx, m_width, m_height, m_selectionMask);
}
bool PaintEngineFacade::deleteSelectionOnActiveLayer() {
    const bool result = orchestrator::SelectionOrchestrator::deleteSelectionOnActiveLayer(m_layerStack, m_selectionMask, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
    if (result) docContext().touch();
    return result;
}
bool PaintEngineFacade::fillSelectionOnActiveLayer(const utils::ColorRGBA& fillColor) {
    const bool result = orchestrator::SelectionOrchestrator::fillSelectionOnActiveLayer(fillColor, m_layerStack, m_selectionMask, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
    if (result) docContext().touch();
    return result;
}
// Seleção é salva no .lmn: mudar a geração faz a transação gravar o Desfazer.
bool PaintEngineFacade::expandSelection(int radiusPx) { return touchedIf(selection::SelectionMorphology::expand(m_selectionMask, radiusPx)); }
bool PaintEngineFacade::contractSelection(int radiusPx) { return touchedIf(selection::SelectionMorphology::contract(m_selectionMask, radiusPx)); }
bool PaintEngineFacade::featherSelection(int radiusPx) { return touchedIf(selection::SelectionMorphology::feather(m_selectionMask, radiusPx)); }
std::vector<int> PaintEngineFacade::getSelectionBounds() const {
    auto b = m_selectionMask.getBounds();
    return { static_cast<int>(b.x), static_cast<int>(b.y), static_cast<int>(b.width), static_cast<int>(b.height) };
}
std::vector<int> PaintEngineFacade::getSelectionContourSegments() const { return m_selectionMask.getContourSegments(); }
std::vector<std::vector<int>> PaintEngineFacade::getSelectionContourLoops() const { return m_selectionMask.getContourLoops(); }

// ─── TRANSFORMAÇÃO LIVRE ───────────────────────────────────────────────────
bool PaintEngineFacade::beginTransform() {
    return orchestrator::TransformOrchestrator::beginTransform(m_transformEngine, m_layerStack, m_selectionMask, m_undoManager, m_width, m_height);
}
bool PaintEngineFacade::isTransformActive() const noexcept { return m_transformEngine.isActive(); }
std::vector<double> PaintEngineFacade::getTransformSourceBounds() const {
    const auto& b = m_transformEngine.getSourceBounds();
    return { b.x, b.y, b.width, b.height };
}
std::vector<double> PaintEngineFacade::getTransformPivot() const {
    const auto& s = m_transformEngine.getState();
    return { s.pivotX, s.pivotY };
}
bool PaintEngineFacade::commitTransform(double dx, double dy, double scaleX, double scaleY, double rotationDeg, double pivotX, double pivotY, bool flipH, bool flipV, int interpMode) {
    const bool result = orchestrator::TransformOrchestrator::commitTransform(m_transformEngine, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, dx, dy, scaleX, scaleY, rotationDeg, pivotX, pivotY, flipH, flipV, interpMode, m_width, m_height);
    if (result) docContext().touch();
    return result;
}
bool PaintEngineFacade::commitTransformDistort(const std::vector<double>& corners, int interpMode) {
    if (corners.size() != 8) return false;
    std::array<double, 8> quad{};
    std::copy(corners.begin(), corners.end(), quad.begin());
    const bool result = orchestrator::TransformOrchestrator::commitTransformDistort(m_transformEngine, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, quad, interpMode, m_width, m_height);
    if (result) docContext().touch();
    return result;
}
bool PaintEngineFacade::cancelTransform() {
    return orchestrator::TransformOrchestrator::cancelTransform(m_transformEngine, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
}
bool PaintEngineFacade::flipActiveLayer(bool horizontal) {
    const bool result = orchestrator::TransformOrchestrator::flipActiveLayer(horizontal, m_width, m_height, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
    if (result) docContext().touch();
    return result;
}
bool PaintEngineFacade::rotateActiveLayer90(bool clockwise) {
    const bool result = orchestrator::TransformOrchestrator::rotateActiveLayer90(clockwise, m_width, m_height, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
    if (result) docContext().touch();
    return result;
}
uint8_t* PaintEngineFacade::getTransformSourceBufferData() noexcept {
    const auto* buf = m_transformEngine.getSourceBuffer();
    return buf ? const_cast<uint8_t*>(buf->getData()) : nullptr;
}
std::vector<int> PaintEngineFacade::getTransformSourceBufferSize() const {
    const auto* buf = m_transformEngine.getSourceBuffer();
    return buf ? std::vector<int>{ buf->getWidth(), buf->getHeight() } : std::vector<int>{ 0, 0 };
}
bool PaintEngineFacade::pasteRgbaBufferOnActiveLayer(int x, int y, int width, int height, const uint8_t* buffer, int blendModeId, double opacity) {
    const bool result = orchestrator::BufferPasteOrchestrator::paste(x, y, width, height, buffer, blendModeId, opacity, m_width, m_height, m_layerStack, m_selectionMask, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
    if (result) docContext().touch();
    return result;
}

// ─── PRESETS E TEXTURAS PROCEDURAIS ────────────────────────────────────────

void PaintEngineFacade::setShapePreset(int presetId) {
    if (presetId <= 1) {
        m_brushProfile.shapeTexture = nullptr;
        if (presetId == 0) m_brushProfile.hardness = 0.2;
        else if (presetId == 1) m_brushProfile.hardness = 0.95;
    } else {
        m_brushProfile.shapeTexture = texture::ProceduralTextures::createShapePreset(static_cast<texture::ShapePreset>(presetId));
    }
}
void PaintEngineFacade::setBrushHeightPreset(int presetId) {
    m_brushProfile.brushHeightTexture = texture::ProceduralTextures::createHeightPreset(static_cast<texture::HeightPreset>(presetId));
}
void PaintEngineFacade::setCanvasHeightPreset(int presetId) {
    m_canvasTexture.canvasHeightTexture = texture::ProceduralTextures::createHeightPreset(static_cast<texture::HeightPreset>(presetId));
}

void PaintEngineFacade::loadShapeTextureFromBuffer(int w, int h, const uint8_t* buf) {
    if (buf && w > 0 && h > 0) m_brushProfile.shapeTexture = std::make_shared<texture::Texture2D>(w, h, std::vector<uint8_t>(buf, buf + static_cast<size_t>(w * h)));
}
void PaintEngineFacade::loadBrushHeightTextureFromBuffer(int w, int h, const uint8_t* buf) {
    if (buf && w > 0 && h > 0) m_brushProfile.brushHeightTexture = std::make_shared<texture::Texture2D>(w, h, std::vector<uint8_t>(buf, buf + static_cast<size_t>(w * h)));
}
void PaintEngineFacade::loadCanvasHeightTextureFromBuffer(int w, int h, const uint8_t* buf) {
    if (buf && w > 0 && h > 0) m_canvasTexture.canvasHeightTexture = std::make_shared<texture::Texture2D>(w, h, std::vector<uint8_t>(buf, buf + static_cast<size_t>(w * h)));
}

// ─── GUIAS, SIMETRIA E SNAP ───────────────────────────────────────────────

void PaintEngineFacade::setGuideConfig(
    int type, double p0x, double p0y, double p1x, double p1y, double p2x, double p2y, double p3x, double p3y,
    double vpAx, double vpAy, double vpBx, double vpBy, double vpCx, double vpCy, double cx, double cy,
    double fov, double pitch, double yaw, double snapRadius
) {
    orchestrator::SnapOrchestrator::setGuideConfig(m_guideConfig, type, p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y,
        vpAx, vpAy, vpBx, vpBy, vpCx, vpCy, cx, cy, fov, pitch, yaw, snapRadius);
}

void PaintEngineFacade::setCurvilinearGuideConfig(
    double baseRadius, double density,
    bool showV, bool showH, bool showD,
    bool showGround, bool showCeiling,
    bool showGroundVerticals, bool showCeilingVerticals,
    bool showStraightVerticals,
    int snapMode, double snapSensitivity
) {
    orchestrator::SnapOrchestrator::setCurvilinearGuideConfig(m_guideConfig, baseRadius, density,
        showV, showH, showD, showGround, showCeiling, showGroundVerticals, showCeilingVerticals,
        showStraightVerticals, snapMode, snapSensitivity);
}

std::vector<double> PaintEngineFacade::snapPoint(double rawX, double rawY, double lastX, double lastY, bool hasLast) const {
    return orchestrator::SnapOrchestrator::snapPoint(m_guideConfig, rawX, rawY, lastX, lastY, hasLast);
}
std::vector<double> PaintEngineFacade::getCurvilinearCandidates(double clickX, double clickY) const {
    return orchestrator::SnapOrchestrator::getCurvilinearCandidates(m_guideConfig, clickX, clickY);
}
std::vector<double> PaintEngineFacade::getNearestPrimaryGridCurve(double x, double y, double maxDist) const {
    return orchestrator::SnapOrchestrator::getNearestPrimaryGridCurve(m_guideConfig, x, y, maxDist);
}
std::vector<double> PaintEngineFacade::snapCurvilinear(
    double rawX, double rawY, double startX, double startY,
    const std::vector<double>& candidates, int lockedIndex, bool isStroking, double zoom
) const {
    return orchestrator::SnapOrchestrator::snapCurvilinear(m_guideConfig, rawX, rawY, startX, startY, candidates, lockedIndex, isStroking, zoom);
}
std::vector<double> PaintEngineFacade::snapPerspective(
    double rawX, double rawY, double startX, double startY,
    bool hasLockedDir, double lockedDirX, double lockedDirY, double zoom
) const {
    return orchestrator::SnapOrchestrator::snapPerspective(m_guideConfig, rawX, rawY, startX, startY, hasLockedDir, lockedDirX, lockedDirY, zoom);
}
std::vector<double> PaintEngineFacade::estimateTrajectory(const std::vector<double>& recentPoints, double zoom) const {
    return orchestrator::SnapOrchestrator::estimateTrajectory(recentPoints, zoom);
}
std::vector<double> PaintEngineFacade::stepSnapLock(
    double rawX, double rawY,
    double trajDirX, double trajDirY, double trajConfidence,
    const std::vector<double>& candidates,
    int prevState, int prevCandidateIndex, int prevStreak,
    double attractionRadius, double breakawayRadius, int commitFrames, double scoreSharpness
) const {
    return orchestrator::SnapOrchestrator::stepSnapLock(rawX, rawY, trajDirX, trajDirY, trajConfidence,
        candidates, prevState, prevCandidateIndex, prevStreak,
        attractionRadius, breakawayRadius, commitFrames, scoreSharpness);
}

bool PaintEngineFacade::setLayerDocumentUid(int index, uint64_t uid) {
    if (uid == 0) return false;
    auto* layer = m_layerStack.getDrawingLayer(index);
    if (!layer) return false;
    layer->setDocumentUid(uid);
    return true;
}

bool PaintEngineFacade::clearHistory() noexcept {
    if (m_isDrawing || m_undoManager.recordingStructure()) return false;
    m_undoManager.clear();
    return !m_undoManager.canUndo() && !m_undoManager.canRedo();
}

// ─── ESCALABILIDADE DE MEMORIA ────────────────────────────────────────────

size_t PaintEngineFacade::compressInactiveLayers() { return orchestrator::MemoryOrchestrator::compressInactiveLayers(m_layerStack); }
size_t PaintEngineFacade::decompressAllLayers() { return orchestrator::MemoryOrchestrator::decompressAllLayers(m_layerStack); }
double PaintEngineFacade::getTotalTileMemoryMB() const { return orchestrator::MemoryOrchestrator::getTotalTileMemoryMB(m_layerStack); }
size_t PaintEngineFacade::getCowSharedTilesCount() const { return orchestrator::MemoryOrchestrator::getCowSharedTilesCount(m_layerStack); }
double PaintEngineFacade::getScratchDiskUsageMB() const noexcept {
    return static_cast<double>(m_undoManager.getScratchDiskBytes()) / (1024.0 * 1024.0);
}

} // namespace aladyn::engine::boundary
