#include "PaintEngineFacade.hpp"
#include "internal/BrushEngineFactory.hpp"
#include "internal/BufferPasteOrchestrator.hpp"
#include "internal/DocumentStateOrchestrator.hpp"
#include "internal/FloodFillOrchestrator.hpp"
#include "internal/LayerStackOrchestrator.hpp"
#include "internal/MemoryOrchestrator.hpp"
#include "internal/RasterExportOrchestrator.hpp"
#include "internal/SelectionOrchestrator.hpp"
#include "internal/SnapOrchestrator.hpp"
#include "internal/StrokeOrchestrator.hpp"
#include "internal/StrokeSessionOrchestrator.hpp"
#include "internal/TransformOrchestrator.hpp"
#include "../../core/raster/SelectionMorphology.hpp"
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

PaintEngineFacade::PaintEngineFacade(int width, int height)
    : m_width(width), m_height(height),
      m_layerStack(width, height),
      m_compositor(width, height),
      m_outputBuffer(width, height, {255, 255, 255, 255}),
      m_displayBuffer(width, height, {255, 255, 255, 255}),
      m_selectionMask(width, height) {

    // Keep the display/mipmap buffers coherent from the first frame.

#ifdef _WIN32
    _putenv("OMP_WAIT_POLICY=PASSIVE");
#endif

    m_firstSample = std::make_unique<internal::TouchdownSample>();
    initEngine(brush::EngineType::Brush);
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
}

PaintEngineFacade::~PaintEngineFacade() = default;

// ─── CONTEXTOS ────────────────────────────────────────────────────────────
// Construidos sob demanda e nunca armazenados: resizeCanvas() e
// syncHistoryGeometry() podem trocar buffers e compositor por instancias novas,
// entao qualquer contexto guardado entre chamadas ficaria pendente.

internal::DocumentContext PaintEngineFacade::docContext() noexcept {
    return internal::DocumentContext{
        m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor,
        m_documentGeneration, m_mipmapPyramid, m_linearGamma, m_deepColor
    };
}

internal::EngineStateContext PaintEngineFacade::stateContext() noexcept {
    return internal::EngineStateContext{
        docContext(), m_displayBuffer, m_selectionMask, m_undoManager, m_width, m_height
    };
}

internal::RawStrokeContext PaintEngineFacade::strokeContext() noexcept {
    return internal::RawStrokeContext{
        m_isDrawing, m_segmentsRenderedInStroke, m_pendingFirstSegment, *m_firstSample,
        m_strokeStartPoint, m_lastRawPoint, m_lastRawPressure, m_hasLastRawPoint,
        m_distanceCarryover, m_timeCarryover, m_lastTimestamp, m_lastDab, m_velocityTracker, m_stabilizer,
        m_brushProfile, m_canvasTexture, m_activeEngine.get(), m_layerStack,
        m_selectionMask, m_undoManager, m_compositor, m_outputBuffer,
        m_symmetryConfig, m_telemetryManager, m_lowLatency,
        m_splineP0, m_splineP1, m_splineP2, m_splineCount
    };
}


// ─── TROCA DE MOTOR ───────────────────────────────────────────────────────

void PaintEngineFacade::initEngine(brush::EngineType type) {
    m_brushProfile.engineType = type;
    m_activeEngine = internal::BrushEngineFactory::create(type);
    if (m_activeEngine) m_activeEngine->onActivate(m_brushProfile);
}

void PaintEngineFacade::setEngineType(int engineTypeId) {
    const auto type = static_cast<brush::EngineType>(engineTypeId);
    if (m_brushProfile.engineType == type) return;
    initEngine(type);
}

// ─── GERENCIAMENTO DE CAMADAS ─────────────────────────────────────────────
// NOTA (Achado #4 da mesma auditoria): as 9 chamadas a m_undoManager.clear()
// que existiam nestas operacoes eram vestigiais -- ja eram no-ops em producao
// (TileUndoManager::clear() tem guard `if (recordingStructure()) return;` e
// toda mutacao estrutural roda dentro de uma transacao aberta) e eram uma
// armadilha para qualquer chamada futura fora de transacao. Nao as
// reintroduza.

int PaintEngineFacade::addLayer(const std::string& name, int insertIndex) { return internal::LayerStackOrchestrator::addLayer(docContext(), name, insertIndex); }
int PaintEngineFacade::addGroup(const std::string& name, int insertIndex) { return internal::LayerStackOrchestrator::addGroup(docContext(), name, insertIndex); }
int PaintEngineFacade::addFilterLayer(const std::string& name, int filterTypeId, int insertIndex) { return internal::LayerStackOrchestrator::addFilterLayer(docContext(), name, filterTypeId, insertIndex); }
bool PaintEngineFacade::removeLayer(int index) { return internal::LayerStackOrchestrator::removeLayer(docContext(), index); }
int PaintEngineFacade::duplicateLayer(int index) { return internal::LayerStackOrchestrator::duplicateLayer(docContext(), index); }
bool PaintEngineFacade::reorderLayer(int fromIndex, int toIndex) { return internal::LayerStackOrchestrator::reorderLayer(docContext(), fromIndex, toIndex); }
bool PaintEngineFacade::reorderLayers(const std::vector<int>& newOrder) { return internal::LayerStackOrchestrator::reorderLayers(docContext(), newOrder); }
bool PaintEngineFacade::setLayerParents(const std::vector<int>& parentIndices) { return internal::LayerStackOrchestrator::setLayerParents(docContext(), parentIndices); }
bool PaintEngineFacade::flattenGroup(int index) { return internal::LayerStackOrchestrator::flattenGroup(docContext(), index); }
bool PaintEngineFacade::mergeLayerDown(int index) { return internal::LayerStackOrchestrator::mergeLayerDown(docContext(), index); }
bool PaintEngineFacade::setGroupPassThrough(int index, bool passThrough) { return internal::LayerStackOrchestrator::setGroupPassThrough(docContext(), index, passThrough); }
void PaintEngineFacade::clearLayer(int index) { internal::LayerStackOrchestrator::clearLayer(docContext(), index); }

void PaintEngineFacade::setLayerOpacity(int index, double opacity) { internal::LayerStackOrchestrator::setLayerOpacity(docContext(), index, opacity); }
void PaintEngineFacade::setLayerBlendMode(int index, int blendModeId) { internal::LayerStackOrchestrator::setLayerBlendMode(docContext(), index, blendModeId); }
void PaintEngineFacade::setLayerVisibility(int index, bool visible) { internal::LayerStackOrchestrator::setLayerVisibility(docContext(), index, visible); }
void PaintEngineFacade::setLayerClippingMask(int index, bool clipped) { internal::LayerStackOrchestrator::setLayerClippingMask(docContext(), index, clipped); }
void PaintEngineFacade::setLayerLock(int index, bool locked) { internal::LayerStackOrchestrator::setLayerLock(docContext(), index, locked); }
void PaintEngineFacade::setLayerAlphaLock(int index, bool locked) { internal::LayerStackOrchestrator::setLayerAlphaLock(docContext(), index, locked); }

void PaintEngineFacade::setFilterParams(int index, const std::vector<float>& params) { internal::LayerStackOrchestrator::setFilterParams(docContext(), index, params); }
std::vector<float> PaintEngineFacade::getFilterParams(int index) const { return internal::LayerStackOrchestrator::getFilterParams(m_layerStack, index); }
int PaintEngineFacade::getFilterType(int index) const { return internal::LayerStackOrchestrator::getFilterType(m_layerStack, index); }

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

void PaintEngineFacade::resizeCanvas(int width, int height) { internal::DocumentStateOrchestrator::resizeCanvas(stateContext(), width, height); }
void PaintEngineFacade::clearCanvas() { internal::DocumentStateOrchestrator::clearCanvas(docContext()); }
bool PaintEngineFacade::cancelLayerTransaction() { return internal::DocumentStateOrchestrator::cancelLayerTransaction(stateContext()); }
bool PaintEngineFacade::undo() { return internal::DocumentStateOrchestrator::undo(stateContext()); }
bool PaintEngineFacade::redo() { return internal::DocumentStateOrchestrator::redo(stateContext()); }

bool PaintEngineFacade::applyPreparedGeometry(const PaintEngineFacade& prepared) {
    if (&prepared == this) return false;
    return internal::DocumentStateOrchestrator::applyPreparedGeometry(
        stateContext(), prepared.m_layerStack, prepared.m_selectionMask);
}

// ─── CONTROLE DE PINCEL E TRAÇO ───────────────────────────────────────────

void PaintEngineFacade::beginStroke(const stroke::PointerEvent& event) {
    auto ctx = strokeContext();
    internal::StrokeSessionOrchestrator::beginStroke(ctx, event);
}

TelemetryData PaintEngineFacade::updateStroke(const stroke::PointerEvent& event) {
    auto ctx = strokeContext();
    const auto s = internal::StrokeSessionOrchestrator::updateStroke(ctx, event);
    return { s.pressure, s.velocity, s.outputFlow };
}

void PaintEngineFacade::endStroke(const stroke::PointerEvent& /*event*/) {
    auto ctx = strokeContext();
    if (internal::StrokeSessionOrchestrator::endStroke(ctx)) docContext().touch();
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
    return internal::StrokeOrchestrator::updateStrokeRaw(ctx, x, y, pressure, timestamp, tiltX, tiltY, twist);
}

std::vector<double> PaintEngineFacade::endStrokeRaw(double endX, double endY) {
    auto ctx = strokeContext();
    return internal::StrokeOrchestrator::endStrokeRaw(ctx, [this](const stroke::PointerEvent& ev) {
        this->endStroke(ev);
    }, endX, endY);
}

telemetry::RealTimeStrokeMetrics PaintEngineFacade::getTelemetrySnapshot() const {
    return internal::StrokeSessionOrchestrator::telemetrySnapshot(m_layerStack, m_undoManager, m_telemetryManager);
}

// ─── FLOOD FILL ───────────────────────────────────────────────────────────

bool PaintEngineFacade::floodFill(
    int seedX, int seedY, const raster::ColorRGBA& fillColor,
    int tolerance, bool contiguous, int expandPx, int gapClosingPx,
    bool antiAliasing, bool sampleAllLayers
) {
    const bool result = internal::FloodFillOrchestrator::floodFill(
        m_outputBuffer, m_layerStack, m_undoManager, m_compositor,
        m_selectionMask, m_canvasTexture.backgroundColor,
        seedX, seedY, fillColor, tolerance, contiguous, expandPx, gapClosingPx, antiAliasing, sampleAllLayers
    );
    if (result) docContext().touch();
    return result;
}

// ─── MÉTODOS DE SELEÇÃO & CONTORNOS ────────────────────────────────────────
bool PaintEngineFacade::magicWandSelect(int seedX, int seedY, int tolerance, bool contiguous, int expandPx, bool antiAliasing, int mode, bool sampleAllLayers) {
    return internal::SelectionOrchestrator::magicWandSelect(seedX, seedY, tolerance, contiguous, expandPx, antiAliasing, mode, sampleAllLayers, m_width, m_height, m_outputBuffer, m_layerStack, m_selectionMask);
}
bool PaintEngineFacade::selectRect(int x, int y, int w, int h, int mode, int featherPx, int cornerRadiusPx) {
    return internal::SelectionOrchestrator::selectRect(x, y, w, h, mode, featherPx, cornerRadiusPx, m_width, m_height, m_selectionMask);
}
bool PaintEngineFacade::selectEllipse(int cx, int cy, int rx, int ry, int mode, bool antiAliasing, int featherPx) {
    return internal::SelectionOrchestrator::selectEllipse(cx, cy, rx, ry, mode, antiAliasing, featherPx, m_width, m_height, m_selectionMask);
}
bool PaintEngineFacade::selectPolygon(const std::vector<int>& flatPoints, int mode, bool antiAliasing, int featherPx) {
    return internal::SelectionOrchestrator::selectPolygon(flatPoints, mode, antiAliasing, featherPx, m_width, m_height, m_selectionMask);
}
bool PaintEngineFacade::deleteSelectionOnActiveLayer() {
    const bool result = internal::SelectionOrchestrator::deleteSelectionOnActiveLayer(m_layerStack, m_selectionMask, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
    if (result) docContext().touch();
    return result;
}
bool PaintEngineFacade::fillSelectionOnActiveLayer(const raster::ColorRGBA& fillColor) {
    const bool result = internal::SelectionOrchestrator::fillSelectionOnActiveLayer(fillColor, m_layerStack, m_selectionMask, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
    if (result) docContext().touch();
    return result;
}
// Seleção é salva no .lmn: mudar a geração faz a transação gravar o Desfazer.
bool PaintEngineFacade::expandSelection(int radiusPx) { return touchedIf(raster::SelectionMorphology::expand(m_selectionMask, radiusPx)); }
bool PaintEngineFacade::contractSelection(int radiusPx) { return touchedIf(raster::SelectionMorphology::contract(m_selectionMask, radiusPx)); }
bool PaintEngineFacade::featherSelection(int radiusPx) { return touchedIf(raster::SelectionMorphology::feather(m_selectionMask, radiusPx)); }
std::vector<int> PaintEngineFacade::getSelectionBounds() const {
    auto b = m_selectionMask.getBounds();
    return { static_cast<int>(b.x), static_cast<int>(b.y), static_cast<int>(b.width), static_cast<int>(b.height) };
}
std::vector<int> PaintEngineFacade::getSelectionContourSegments() const { return m_selectionMask.getContourSegments(); }
std::vector<std::vector<int>> PaintEngineFacade::getSelectionContourLoops() const { return m_selectionMask.getContourLoops(); }

// ─── TRANSFORMAÇÃO LIVRE ───────────────────────────────────────────────────
bool PaintEngineFacade::beginTransform() {
    return internal::TransformOrchestrator::beginTransform(m_transformEngine, m_layerStack, m_selectionMask, m_undoManager, m_width, m_height);
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
    const bool result = internal::TransformOrchestrator::commitTransform(m_transformEngine, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, dx, dy, scaleX, scaleY, rotationDeg, pivotX, pivotY, flipH, flipV, interpMode, m_width, m_height);
    if (result) docContext().touch();
    return result;
}
bool PaintEngineFacade::commitTransformDistort(const std::vector<double>& corners, int interpMode) {
    if (corners.size() != 8) return false;
    std::array<double, 8> quad{};
    std::copy(corners.begin(), corners.end(), quad.begin());
    const bool result = internal::TransformOrchestrator::commitTransformDistort(m_transformEngine, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, quad, interpMode, m_width, m_height);
    if (result) docContext().touch();
    return result;
}
bool PaintEngineFacade::cancelTransform() {
    return internal::TransformOrchestrator::cancelTransform(m_transformEngine, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, m_width, m_height);
}
bool PaintEngineFacade::flipActiveLayer(bool horizontal) {
    const bool result = internal::TransformOrchestrator::flipActiveLayer(horizontal, m_width, m_height, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
    if (result) docContext().touch();
    return result;
}
bool PaintEngineFacade::rotateActiveLayer90(bool clockwise) {
    const bool result = internal::TransformOrchestrator::rotateActiveLayer90(clockwise, m_width, m_height, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
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
    const bool result = internal::BufferPasteOrchestrator::paste(x, y, width, height, buffer, blendModeId, opacity, m_width, m_height, m_layerStack, m_selectionMask, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
    if (result) docContext().touch();
    return result;
}

// ─── PRESETS E TEXTURAS PROCEDURAIS ────────────────────────────────────────

void PaintEngineFacade::loadShapeTextureFromBuffer(int w, int h, const uint8_t* buf) {
    if (buf && w > 0 && h > 0) m_brushProfile.shapeTexture = std::make_shared<texture::Texture2D>(w, h, std::vector<uint8_t>(buf, buf + static_cast<size_t>(w * h)));
}
void PaintEngineFacade::loadBrushHeightTextureFromBuffer(int w, int h, const uint8_t* buf) {
    if (buf && w > 0 && h > 0) m_brushProfile.brushHeightTexture = std::make_shared<texture::Texture2D>(w, h, std::vector<uint8_t>(buf, buf + static_cast<size_t>(w * h)));
}
void PaintEngineFacade::loadCanvasHeightTextureFromBuffer(int w, int h, const uint8_t* buf) {
    if (buf && w > 0 && h > 0) m_canvasTexture.canvasHeightTexture = std::make_shared<texture::Texture2D>(w, h, std::vector<uint8_t>(buf, buf + static_cast<size_t>(w * h)));
}

// ─── OPCOES DE RENDER E SAIDA RASTER ──────────────────────────────────────

void PaintEngineFacade::setLowLatency(bool enabled) noexcept { m_lowLatency = enabled; }
void PaintEngineFacade::setLinearGamma(bool enabled) { setRenderOptions(m_lowLatency, enabled, m_deepColor); }
void PaintEngineFacade::setDeepColor(bool enabled) { setRenderOptions(m_lowLatency, m_linearGamma, enabled); }

void PaintEngineFacade::setRenderOptions(bool lowLatency, bool linearGamma, bool deepColor) {
    const bool compositionChanged = (m_linearGamma != linearGamma) || (m_deepColor != deepColor);
    m_lowLatency = lowLatency;
    m_linearGamma = linearGamma;
    m_deepColor = deepColor;
    m_compositor.setLinearGamma(linearGamma);
    m_compositor.setDeepColor(deepColor);
    if (compositionChanged) {
        const auto ctx = docContext();
        ctx.compositeAll();
        ctx.touch();
    }
}

uint8_t* PaintEngineFacade::getDisplayRawPixelData() noexcept {
    return internal::RasterExportOrchestrator::resolveDisplayBuffer(m_colorProfileId, m_outputBuffer, m_displayBuffer);
}
std::vector<uint8_t> PaintEngineFacade::getLayerPixelBuffer(int layerIndex) const {
    return internal::RasterExportOrchestrator::getLayerPixelBuffer(m_layerStack, layerIndex, m_width, m_height);
}
std::vector<uint8_t> PaintEngineFacade::getLayerThumbnailBuffer(int layerIdx, int thumbW, int thumbH) const {
    return internal::RasterExportOrchestrator::getLayerThumbnailBuffer(m_layerStack, layerIdx, thumbW, thumbH);
}
std::string PaintEngineFacade::transformRgbaForProfile(const std::string& buffer, int profileId) const {
    return internal::RasterExportOrchestrator::transformRgbaForProfile(buffer, profileId);
}

// ─── GUIAS, SIMETRIA E SNAP ───────────────────────────────────────────────

void PaintEngineFacade::setGuideConfig(
    int type, double p0x, double p0y, double p1x, double p1y, double p2x, double p2y, double p3x, double p3y,
    double vpAx, double vpAy, double vpBx, double vpBy, double vpCx, double vpCy, double cx, double cy,
    double fov, double pitch, double yaw, double snapRadius
) {
    internal::SnapOrchestrator::setGuideConfig(m_guideConfig, type, p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y,
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
    internal::SnapOrchestrator::setCurvilinearGuideConfig(m_guideConfig, baseRadius, density,
        showV, showH, showD, showGround, showCeiling, showGroundVerticals, showCeilingVerticals,
        showStraightVerticals, snapMode, snapSensitivity);
}

std::vector<double> PaintEngineFacade::snapPoint(double rawX, double rawY, double lastX, double lastY, bool hasLast) const {
    return internal::SnapOrchestrator::snapPoint(m_guideConfig, rawX, rawY, lastX, lastY, hasLast);
}
std::vector<double> PaintEngineFacade::getCurvilinearCandidates(double clickX, double clickY) const {
    return internal::SnapOrchestrator::getCurvilinearCandidates(m_guideConfig, clickX, clickY);
}
std::vector<double> PaintEngineFacade::getNearestPrimaryGridCurve(double x, double y, double maxDist) const {
    return internal::SnapOrchestrator::getNearestPrimaryGridCurve(m_guideConfig, x, y, maxDist);
}
std::vector<double> PaintEngineFacade::snapCurvilinear(
    double rawX, double rawY, double startX, double startY,
    const std::vector<double>& candidates, int lockedIndex, bool isStroking, double zoom
) const {
    return internal::SnapOrchestrator::snapCurvilinear(m_guideConfig, rawX, rawY, startX, startY, candidates, lockedIndex, isStroking, zoom);
}
std::vector<double> PaintEngineFacade::snapPerspective(
    double rawX, double rawY, double startX, double startY,
    bool hasLockedDir, double lockedDirX, double lockedDirY, double zoom
) const {
    return internal::SnapOrchestrator::snapPerspective(m_guideConfig, rawX, rawY, startX, startY, hasLockedDir, lockedDirX, lockedDirY, zoom);
}
std::vector<double> PaintEngineFacade::estimateTrajectory(const std::vector<double>& recentPoints, double zoom) const {
    return internal::SnapOrchestrator::estimateTrajectory(recentPoints, zoom);
}
std::vector<double> PaintEngineFacade::stepSnapLock(
    double rawX, double rawY,
    double trajDirX, double trajDirY, double trajConfidence,
    const std::vector<double>& candidates,
    int prevState, int prevCandidateIndex, int prevStreak,
    double attractionRadius, double breakawayRadius, int commitFrames, double scoreSharpness
) const {
    return internal::SnapOrchestrator::stepSnapLock(rawX, rawY, trajDirX, trajDirY, trajConfidence,
        candidates, prevState, prevCandidateIndex, prevStreak,
        attractionRadius, breakawayRadius, commitFrames, scoreSharpness);
}

// ─── ESCALABILIDADE DE MEMORIA ────────────────────────────────────────────

size_t PaintEngineFacade::compressInactiveLayers() { return internal::MemoryOrchestrator::compressInactiveLayers(m_layerStack); }
size_t PaintEngineFacade::decompressAllLayers() { return internal::MemoryOrchestrator::decompressAllLayers(m_layerStack); }
double PaintEngineFacade::getTotalTileMemoryMB() const { return internal::MemoryOrchestrator::getTotalTileMemoryMB(m_layerStack); }
size_t PaintEngineFacade::getCowSharedTilesCount() const { return internal::MemoryOrchestrator::getCowSharedTilesCount(m_layerStack); }

} // namespace aladyn::engine::boundary
