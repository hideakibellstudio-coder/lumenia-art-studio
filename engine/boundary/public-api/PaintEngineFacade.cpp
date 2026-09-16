#include "PaintEngineFacade.hpp"
#include "../../core/brush/DynamicMapper.hpp"
#include "../../core/engines/PencilEngine.hpp"
#include "../../core/engines/InkerEngine.hpp"
#include "../../core/engines/EraserEngine.hpp"
#include "../../core/engines/MarkerEngine.hpp"
#include "../../core/engines/BlurEngine.hpp"
#include "../../core/engines/SmudgeEngine.hpp"
#include "../../core/engines/WatercolorEngine.hpp"
#include "../../core/engines/OilImpastoEngine.hpp"
#include "../../core/raster/FloodFill.hpp"
#include "../../core/color/ColorProfile.hpp"
#include "internal/StrokeOrchestrator.hpp"
#include "internal/SelectionOrchestrator.hpp"
#include "internal/TransformOrchestrator.hpp"
#include "internal/BufferPasteOrchestrator.hpp"
#include "internal/LayerStackOrchestrator.hpp"
#include "internal/FloodFillOrchestrator.hpp"
#include "internal/MemoryOrchestrator.hpp"
#include <algorithm>
#include <cmath>
#include <cstdlib>

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

void PaintEngineFacade::initEngine(brush::EngineType type) {
    m_brushProfile.engineType = type;

    switch (type) {
        case brush::EngineType::Pencil:
            m_activeEngine = std::make_unique<engines::PencilEngine>();
            break;
        case brush::EngineType::Inker:
            m_activeEngine = std::make_unique<engines::InkerEngine>();
            break;
        case brush::EngineType::Eraser:
            m_activeEngine = std::make_unique<engines::EraserEngine>();
            break;
        case brush::EngineType::Marker:
            m_activeEngine = std::make_unique<engines::MarkerEngine>();
            break;
        case brush::EngineType::Blur:
            m_activeEngine = std::make_unique<engines::BlurEngine>();
            break;
        case brush::EngineType::Smudge:
            m_activeEngine = std::make_unique<engines::SmudgeEngine>();
            break;
        case brush::EngineType::Watercolor:
            m_activeEngine = std::make_unique<engines::WatercolorEngine>();
            break;
        case brush::EngineType::OilImpasto:
            m_activeEngine = std::make_unique<engines::OilImpastoEngine>();
            break;
        default:
            m_activeEngine.reset();
            break;
    }

    if (m_activeEngine) {
        m_activeEngine->onActivate(m_brushProfile);
    }
}

void PaintEngineFacade::setEngineType(int engineTypeId) {
    const auto type = static_cast<brush::EngineType>(engineTypeId);
    if (m_brushProfile.engineType == type) return;
    initEngine(type);
}

// ─── GERENCIAMENTO DE CAMADAS ─────────────────────────────────────────────

int PaintEngineFacade::addLayer(const std::string& name, int insertIndex) {
    const int result = internal::LayerStackOrchestrator::addLayer(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, name, insertIndex);
    if (result >= 0) { m_undoManager.clear(); touchDocument(); }
    return result;
}

int PaintEngineFacade::addGroup(const std::string& name, int insertIndex) {
    const int result = internal::LayerStackOrchestrator::addGroup(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, name, insertIndex);
    if (result >= 0) { m_undoManager.clear(); touchDocument(); }
    return result;
}

int PaintEngineFacade::addFilterLayer(const std::string& name, int filterTypeId, int insertIndex) {
    const int result = internal::LayerStackOrchestrator::addFilterLayer(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, name, filterTypeId, insertIndex);
    if (result >= 0) { m_undoManager.clear(); touchDocument(); }
    return result;
}

void PaintEngineFacade::setFilterParams(int index, const std::vector<float>& params) {
    auto* l = m_layerStack.getDrawingLayer(index);
    if (auto* fl = dynamic_cast<document::FilterLayer*>(l)) {
        for (size_t i = 0; i < params.size(); ++i) fl->setParam(i, params[i]);
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
        touchDocument();
    }
}

std::vector<float> PaintEngineFacade::getFilterParams(int index) const {
    const auto* l = m_layerStack.getDrawingLayer(index);
    if (const auto* fl = dynamic_cast<const document::FilterLayer*>(l)) {
        std::vector<float> p;
        for (size_t i = 0; i < 4; ++i) p.push_back(fl->getParam(i, 0.0f));
        return p;
    }
    return {};
}

int PaintEngineFacade::getFilterType(int index) const {
    const auto* l = m_layerStack.getDrawingLayer(index);
    if (const auto* fl = dynamic_cast<const document::FilterLayer*>(l)) return static_cast<int>(fl->getFilterType());
    return 0;
}

bool PaintEngineFacade::setGroupPassThrough(int index, bool passThrough) {
    bool ok = m_layerStack.setGroupPassThrough(index, passThrough);
    if (ok) { m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor); touchDocument(); }
    return ok;
}

bool PaintEngineFacade::removeLayer(int index) {
    const bool result = internal::LayerStackOrchestrator::removeLayer(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index);
    if (result) { m_undoManager.clear(); touchDocument(); }
    return result;
}

int PaintEngineFacade::duplicateLayer(int index) {
    const int result = internal::LayerStackOrchestrator::duplicateLayer(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index);
    if (result >= 0) { m_undoManager.clear(); touchDocument(); }
    return result;
}

bool PaintEngineFacade::reorderLayer(int fromIndex, int toIndex) {
    const bool result = internal::LayerStackOrchestrator::reorderLayer(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, fromIndex, toIndex);
    if (result) { m_undoManager.clear(); touchDocument(); }
    return result;
}

bool PaintEngineFacade::reorderLayers(const std::vector<int>& newOrder) {
    const bool result = internal::LayerStackOrchestrator::reorderLayers(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, newOrder);
    if (result) { m_undoManager.clear(); touchDocument(); }
    return result;
}

bool PaintEngineFacade::setLayerParents(const std::vector<int>& parentIndices) {
    const bool result = internal::LayerStackOrchestrator::setLayerParents(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, parentIndices);
    if (result) touchDocument();
    return result;
}


void PaintEngineFacade::setLayerOpacity(int index, double opacity) {
    internal::LayerStackOrchestrator::setLayerOpacity(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index, opacity);
    touchDocument();
}

void PaintEngineFacade::setLayerBlendMode(int index, int blendModeId) {
    internal::LayerStackOrchestrator::setLayerBlendMode(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index, blendModeId);
    touchDocument();
}

void PaintEngineFacade::setLayerVisibility(int index, bool visible) {
    internal::LayerStackOrchestrator::setLayerVisibility(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index, visible);
    touchDocument();
}

void PaintEngineFacade::setLayerLock(int index, bool locked) {
    if (auto* l = m_layerStack.getDrawingLayer(index)) { l->setLocked(locked); touchDocument(); }
}

void PaintEngineFacade::setLayerAlphaLock(int index, bool locked) {
    if (auto* l = m_layerStack.getDrawingLayer(index)) { l->setAlphaLocked(locked); touchDocument(); }
}


void PaintEngineFacade::setLayerClippingMask(int index, bool clipped) {
    internal::LayerStackOrchestrator::setLayerClippingMask(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index, clipped);
    touchDocument();
}


bool PaintEngineFacade::flattenGroup(int index) {
    const bool result = internal::LayerStackOrchestrator::flattenGroup(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index, m_linearGamma, m_deepColor);
    if (result) { m_undoManager.clear(); touchDocument(); }
    return result;
}

bool PaintEngineFacade::mergeLayerDown(int index) {
    const bool result = internal::LayerStackOrchestrator::mergeLayerDown(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index, m_linearGamma, m_deepColor);
    if (result) { m_undoManager.clear(); touchDocument(); }
    return result;
}

void PaintEngineFacade::clearLayer(int index) {
    internal::LayerStackOrchestrator::clearLayer(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index);
    touchDocument();
}

void PaintEngineFacade::setBackgroundVisibility(bool visible) {
    m_layerStack.getBackgroundLayer().setVisible(visible);
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    touchDocument();
}


void PaintEngineFacade::setBackgroundColor(uint8_t r, uint8_t g, uint8_t b, uint8_t a) {
    m_canvasTexture.backgroundColor = {r, g, b, a};
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    touchDocument();
}

void PaintEngineFacade::resizeCanvas(int width, int height) {
    m_width = width;
    m_height = height;
    m_layerStack.resize(width, height);
    // Snapshots antigos têm dimensões incompatíveis com a nova grade.
    m_undoManager.clear();
    m_compositor = document::Compositor(width, height);
    m_compositor.setLinearGamma(m_linearGamma);
    m_compositor.setDeepColor(m_deepColor);
    m_outputBuffer.resize(width, height, m_canvasTexture.backgroundColor);
    m_displayBuffer.resize(width, height, m_canvasTexture.backgroundColor);
    m_selectionMask.resize(width, height);
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    touchDocument();
}

void PaintEngineFacade::clearCanvas() {
    auto* active = m_layerStack.getActiveLayer();
    if (active && !active->isLocked() && !active->isGroup() && !active->isFilter()) {
        active->getTileGrid().clearTiles();
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
        touchDocument();
    }
}

// ─── CONTROLE DE PINCEL E TRAÇO ───────────────────────────────────────────

void PaintEngineFacade::beginStroke(const stroke::PointerEvent& event) {
    m_isDrawing = true;
    m_segmentsRenderedInStroke = 0;
    m_pendingFirstSegment = false;
    m_strokeStartPoint = event.position;
    m_lastRawPressure = event.pressure;
    m_distanceCarryover = 0.0;
    m_stabilizer.reset(event.position);
    m_velocityTracker.reset(event.position, event.timestamp);
    m_undoManager.beginStep("Stroke");
    if (m_activeEngine) m_activeEngine->onBeginStroke();
    auto mapped = brush::DynamicMapper::map(
        m_brushProfile, event.position, event.pressure, 0.0, 0.0,
        event.twist, event.altitude, event.azimuth
    );
    m_lastDab = raster::Dab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, m_brushProfile.blendMode, mapped.color, mapped.aspectRatio);
    m_telemetryManager.onBeginStroke(event.pressure, static_cast<int>(m_brushProfile.engineType));
}

TelemetryData PaintEngineFacade::updateStroke(const stroke::PointerEvent& event) {
    if (!m_isDrawing) return {0.0, 0.0, 0.0};
    ++m_segmentsRenderedInStroke;
    m_lastRawPressure = event.pressure;
    const double currentVelocity = m_velocityTracker.update(event.position, event.timestamp);
    const double normVel = m_velocityTracker.getNormalizedVelocity(1500.0);
    // Mesmo critério do StrokeOrchestrator: o atalho de baixa latência só vale
    // quando não há estabilização pedida. `m_lowLatency` sozinho desviava o
    // estabilizador, e como low_latency=True é o padrão do backend o slider de
    // suavização não tinha efeito nenhum neste caminho também.
    const bool atalho = m_lowLatency && m_stabilizer.getStabilizationPercentage() <= 0.5;
    const math::Point2D pos = atalho ? event.position : m_stabilizer.update(event.position, normVel);

    double strokeAngle = 0.0;
    const double dx = pos.x - m_lastDab.position.x;
    const double dy = pos.y - m_lastDab.position.y;
    if (dx * dx + dy * dy > 0.01) {
        strokeAngle = std::atan2(dy, dx) * (180.0 / 3.14159265358979323846);
        if (strokeAngle < 0.0) strokeAngle += 360.0;
    }

    auto mapped = brush::DynamicMapper::map(
        m_brushProfile, pos, event.pressure, normVel, strokeAngle,
        event.twist, event.altitude, event.azimuth
    );
    raster::Dab currentDab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, m_brushProfile.blendMode, mapped.color, mapped.aspectRatio);
    renderStrokeSegment(m_lastDab, currentDab);
    m_lastDab = currentDab;
    return { event.pressure, currentVelocity, currentDab.opacity };
}

void PaintEngineFacade::endStroke(const stroke::PointerEvent& /*event*/) {
    if (!m_isDrawing) return;
    if (m_segmentsRenderedInStroke == 0) {
        math::Rect2D dirty{0, 0, 0, 0};
        uint32_t dabsRendered = 0;
                telemetry::StageMetrics stagesCatchup{};
        internal::StrokeOrchestrator::renderSegment(
            m_lastDab, m_lastDab, m_brushProfile, m_canvasTexture,
            m_activeEngine.get(), m_layerStack, m_selectionMask,
            m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor,
            m_distanceCarryover, m_symmetryConfig, &m_strokeStartPoint, &dirty, &dabsRendered
        );
        m_segmentsRenderedInStroke = 1;
    }
    if (m_activeEngine) m_activeEngine->onEndStroke();
    m_undoManager.commitStep(m_layerStack);
    touchDocument();
    m_isDrawing = false;
    m_distanceCarryover = 0.0;

    if (m_activeEngine && m_activeEngine->getType() == brush::EngineType::Eraser) {
        if (auto* layer = m_layerStack.getActiveLayer()) {
            layer->getTileGrid().pruneEmptyTiles();
        }
    }

    if (m_telemetryManager.isEnabled()) {
        uint32_t activeTiles = 0;
        if (const auto* layer = m_layerStack.getActiveLayer()) {
            activeTiles = static_cast<uint32_t>(layer->getTileGrid().getActiveTilesCount());
        }
        double tileMemMB = (activeTiles * canvas::Tile::TILE_SIZE * canvas::Tile::TILE_SIZE * 4) / (1024.0 * 1024.0);
        double undoMemMB = m_undoManager.getMemoryUsageBytes() / (1024.0 * 1024.0);
        uint32_t undoSteps = static_cast<uint32_t>(m_undoManager.getUndoCount());
        m_telemetryManager.onEndStroke(0, activeTiles, tileMemMB, undoMemMB, undoSteps);
    }
}

void PaintEngineFacade::beginStrokeRaw(double x, double y, double pressure, double timestamp,
                                       double tiltX, double tiltY, double twist) {
    m_lastRawPoint = {x, y};
    m_hasLastRawPoint = true;
    m_lastRawPressure = pressure;
    m_pendingFirstSegment = false;
    double t = timestamp;
    if (t <= 0.0) {
        auto now = std::chrono::high_resolution_clock::now();
        t = std::chrono::duration<double>(now.time_since_epoch()).count();
    }
    stroke::PointerEvent ev{stroke::PointerEventType::Press, {x, y}, pressure, t, tiltX, tiltY, twist};
    ev.computeAltitudeAzimuthFromTilt();
    beginStroke(ev);
}

std::vector<double> PaintEngineFacade::updateStrokeRaw(double x, double y, double pressure, double timestamp,
                                                       double tiltX, double tiltY, double twist) {
    internal::RawStrokeContext ctx{
        m_isDrawing, m_segmentsRenderedInStroke, m_pendingFirstSegment, *m_firstSample,
        m_strokeStartPoint, m_lastRawPoint, m_lastRawPressure, m_hasLastRawPoint,
        m_distanceCarryover, m_lastDab, m_velocityTracker, m_stabilizer,
        m_brushProfile, m_canvasTexture, m_activeEngine.get(), m_layerStack,
        m_selectionMask, m_undoManager, m_compositor, m_outputBuffer,
        m_symmetryConfig, m_telemetryManager, m_lowLatency
    };
    return internal::StrokeOrchestrator::updateStrokeRaw(ctx, x, y, pressure, timestamp, tiltX, tiltY, twist);
}

std::vector<double> PaintEngineFacade::endStrokeRaw() {
    internal::RawStrokeContext ctx{
        m_isDrawing, m_segmentsRenderedInStroke, m_pendingFirstSegment, *m_firstSample,
        m_strokeStartPoint, m_lastRawPoint, m_lastRawPressure, m_hasLastRawPoint,
        m_distanceCarryover, m_lastDab, m_velocityTracker, m_stabilizer,
        m_brushProfile, m_canvasTexture, m_activeEngine.get(), m_layerStack,
        m_selectionMask, m_undoManager, m_compositor, m_outputBuffer,
        m_symmetryConfig, m_telemetryManager, m_lowLatency
    };
    return internal::StrokeOrchestrator::endStrokeRaw(ctx, [this](const stroke::PointerEvent& ev) {
        this->endStroke(ev);
    });
}

void PaintEngineFacade::renderStrokeSegment(const raster::Dab& startDab, const raster::Dab& endDab) {
    internal::StrokeOrchestrator::renderSegment(
        startDab, endDab, m_brushProfile, m_canvasTexture,
        m_activeEngine.get(), m_layerStack, m_selectionMask,
        m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor,
        m_distanceCarryover,
        m_symmetryConfig, &m_strokeStartPoint
    );
}

telemetry::RealTimeStrokeMetrics PaintEngineFacade::getTelemetrySnapshot() const {
    uint32_t activeTiles = 0;
    if (const auto* layer = m_layerStack.getActiveLayer()) {
        activeTiles = static_cast<uint32_t>(layer->getTileGrid().getActiveTilesCount());
    }
    double tileMemMB = (activeTiles * canvas::Tile::TILE_SIZE * canvas::Tile::TILE_SIZE * 4) / (1024.0 * 1024.0);
    double undoMemMB = m_undoManager.getMemoryUsageBytes() / (1024.0 * 1024.0);
    uint32_t undoSteps = static_cast<uint32_t>(m_undoManager.getUndoCount());
    return m_telemetryManager.getSnapshot(activeTiles, tileMemMB, undoMemMB, undoSteps);
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
    if (result) touchDocument();
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
    if (result) touchDocument();
    return result;
}
bool PaintEngineFacade::fillSelectionOnActiveLayer(const raster::ColorRGBA& fillColor) {
    const bool result = internal::SelectionOrchestrator::fillSelectionOnActiveLayer(fillColor, m_layerStack, m_selectionMask, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
    if (result) touchDocument();
    return result;
}
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
    if (result) touchDocument();
    return result;
}
bool PaintEngineFacade::cancelTransform() {
    return internal::TransformOrchestrator::cancelTransform(m_transformEngine, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, m_width, m_height);
}
bool PaintEngineFacade::flipActiveLayer(bool horizontal) {
    const bool result = internal::TransformOrchestrator::flipActiveLayer(horizontal, m_width, m_height, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
    if (result) touchDocument();
    return result;
}
bool PaintEngineFacade::rotateActiveLayer90(bool clockwise) {
    const bool result = internal::TransformOrchestrator::rotateActiveLayer90(clockwise, m_width, m_height, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
    if (result) touchDocument();
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
    if (result) touchDocument();
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

void PaintEngineFacade::setLowLatency(bool enabled) noexcept {
    m_lowLatency = enabled;
}

void PaintEngineFacade::setLinearGamma(bool enabled) {
    setRenderOptions(m_lowLatency, enabled, m_deepColor);
}

void PaintEngineFacade::setDeepColor(bool enabled) {
    setRenderOptions(m_lowLatency, m_linearGamma, enabled);
}

void PaintEngineFacade::setRenderOptions(bool lowLatency, bool linearGamma, bool deepColor) {
    const bool compositionChanged = (m_linearGamma != linearGamma) || (m_deepColor != deepColor);
    m_lowLatency = lowLatency;
    m_linearGamma = linearGamma;
    m_deepColor = deepColor;
    m_compositor.setLinearGamma(linearGamma);
    m_compositor.setDeepColor(deepColor);
    if (compositionChanged) {
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
        touchDocument();
        m_mipmapPyramid.markDirty();
    }
}

void PaintEngineFacade::applyActiveColorProfile(uint8_t* targetBuffer, size_t numPixels) const noexcept {
    if (!targetBuffer || numPixels == 0 || numPixels > static_cast<size_t>(std::numeric_limits<int>::max())) return;
    color::ColorProfileManager::transformBuffer(
        targetBuffer,
        targetBuffer,
        static_cast<int>(numPixels),
        static_cast<color::ColorProfileType>(m_colorProfileId)
    );
}
uint8_t* PaintEngineFacade::getDisplayRawPixelData() noexcept {
    if (m_colorProfileId == 0) return m_outputBuffer.getData();
    const size_t totalBytes = m_outputBuffer.getSizeInBytes();
    std::memcpy(m_displayBuffer.getData(), m_outputBuffer.getData(), totalBytes);
    applyActiveColorProfile(m_displayBuffer.getData(), totalBytes / 4);
    return m_displayBuffer.getData();
}
bool PaintEngineFacade::cancelLayerTransaction() {
    if (!m_undoManager.cancelStructure(m_layerStack, m_selectionMask)) return false;
    syncHistoryGeometry();
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    touchDocument();
    return true;
}
void PaintEngineFacade::syncHistoryGeometry() {
    const int width = m_layerStack.getWidth(), height = m_layerStack.getHeight();
    if (width == m_width && height == m_height) return;
    canvas::PixelBuffer output(width, height, m_canvasTexture.backgroundColor);
    canvas::PixelBuffer display(width, height, m_canvasTexture.backgroundColor);
    document::Compositor compositor(width, height);
    compositor.setLinearGamma(m_linearGamma);
    compositor.setDeepColor(m_deepColor);
    m_outputBuffer = std::move(output);
    m_displayBuffer = std::move(display);
    m_compositor = std::move(compositor);
    m_width = width;
    m_height = height;
    m_mipmapPyramid.markDirty();
}

bool PaintEngineFacade::applyPreparedGeometry(const PaintEngineFacade& prepared) {
    if (&prepared == this || !m_undoManager.recordingStructure()) return false;
    // Keep this facade (brush state, guide state and all earlier history).
    // Only adopt the validated replacement layer stack and selection.
    auto selection = prepared.m_selectionMask;
    m_layerStack.restore(prepared.m_layerStack);
    m_selectionMask = std::move(selection);
    syncHistoryGeometry();
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    touchDocument();
    return true;
}
bool PaintEngineFacade::undo() {
    bool ok = m_undoManager.undo(m_layerStack, m_selectionMask);
    if (ok) {
        syncHistoryGeometry();
        touchDocument();
        if (auto* layer = m_layerStack.getActiveLayer()) {
            layer->getTileGrid().pruneEmptyTiles();
        }
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
}
bool PaintEngineFacade::redo() {
    bool ok = m_undoManager.redo(m_layerStack, m_selectionMask);
    if (ok) {
        syncHistoryGeometry();
        touchDocument();
        if (auto* layer = m_layerStack.getActiveLayer()) {
            layer->getTileGrid().pruneEmptyTiles();
        }
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
}

std::vector<uint8_t> PaintEngineFacade::getLayerPixelBuffer(int layerIndex) const {
    const auto* layer = m_layerStack.getDrawingLayer(layerIndex);
    if (!layer || layer->isGroup() || layer->isFilter()) return {};

    std::vector<uint8_t> out(static_cast<size_t>(m_width) * static_cast<size_t>(m_height) * 4u, 0u);
    const auto& grid = layer->getTileGrid();
    grid.forEachTile([&](const canvas::TileIndex&, const canvas::Tile& tile) {
        const auto& src = tile.getBuffer();
        const int baseX = tile.getPixelX();
        const int baseY = tile.getPixelY();
        const int minX = std::max(0, baseX);
        const int minY = std::max(0, baseY);
        const int maxX = std::min(m_width, baseX + canvas::Tile::TILE_SIZE);
        const int maxY = std::min(m_height, baseY + canvas::Tile::TILE_SIZE);
        if (minX >= maxX || minY >= maxY) return;

        const auto* srcData = reinterpret_cast<const uint8_t*>(src.getData());
        for (int y = minY; y < maxY; ++y) {
            const int localY = y - baseY;
            for (int x = minX; x < maxX; ++x) {
                const int localX = x - baseX;
                const size_t srcOffset = static_cast<size_t>(localY * canvas::Tile::TILE_SIZE + localX) * 4u;
                const size_t dstOffset = static_cast<size_t>(y * m_width + x) * 4u;
                std::memcpy(out.data() + dstOffset, srcData + srcOffset, 4u);
            }
        }
    });
    return out;
}

void PaintEngineFacade::setGuideConfig(
    int type, double p0x, double p0y, double p1x, double p1y, double p2x, double p2y, double p3x, double p3y,
    double vpAx, double vpAy, double vpBx, double vpBy, double vpCx, double vpCy, double cx, double cy,
    double fov, double pitch, double yaw, double snapRadius
) {
    m_guideConfig = { static_cast<math::GuideType>(type), {p0x, p0y}, {p1x, p1y}, {p2x, p2y}, {p3x, p3y}, {vpAx, vpAy}, {vpBx, vpBy}, {vpCx, vpCy}, cx, cy, fov, pitch, yaw, snapRadius };
}

std::vector<double> PaintEngineFacade::snapPoint(double rawX, double rawY, double lastX, double lastY, bool hasLast) const {
    const math::Point2D last{ lastX, lastY };
    const math::Point2D snapped = math::GuideSnapEngine::snapPoint(m_guideConfig, {rawX, rawY}, hasLast ? &last : nullptr);
    return { snapped.x, snapped.y };
}

size_t PaintEngineFacade::compressInactiveLayers() {
    return internal::MemoryOrchestrator::compressInactiveLayers(m_layerStack);
}

size_t PaintEngineFacade::decompressAllLayers() {
    return internal::MemoryOrchestrator::decompressAllLayers(m_layerStack);
}

double PaintEngineFacade::getTotalTileMemoryMB() const {
    return internal::MemoryOrchestrator::getTotalTileMemoryMB(m_layerStack);
}

size_t PaintEngineFacade::getCowSharedTilesCount() const {
    return internal::MemoryOrchestrator::getCowSharedTilesCount(m_layerStack);
}

std::string PaintEngineFacade::transformRgbaForProfile(const std::string& buffer, int profileId) const {
    if (!color::ColorProfileManager::isProfileValid(profileId)) {
        throw std::invalid_argument("Unknown color profile");
    }
    if (buffer.size() % 4 != 0) {
        throw std::invalid_argument("RGBA input length must be a multiple of four");
    }
    const size_t pixels = buffer.size() / 4;
    if (pixels > static_cast<size_t>(std::numeric_limits<int>::max())) {
        throw std::invalid_argument("RGBA input is too large");
    }
    std::string transformed = buffer;
    color::ColorProfileManager::transformBuffer(
        reinterpret_cast<const uint8_t*>(buffer.data()),
        reinterpret_cast<uint8_t*>(transformed.data()),
        static_cast<int>(pixels),
        static_cast<color::ColorProfileType>(profileId)
    );
    return transformed;
}

std::vector<uint8_t> PaintEngineFacade::getLayerThumbnailBuffer(int layerIdx, int thumbW, int thumbH) const {
    const auto* layer = m_layerStack.getDrawingLayer(layerIdx);
    if (!layer) return {};

    const auto& grid = layer->getTileGrid();
    int srcW = grid.getWidth();
    int srcH = grid.getHeight();
    if (srcW <= 0 || srcH <= 0 || thumbW <= 0 || thumbH <= 0) return {};

    const size_t expectedBytes = static_cast<size_t>(thumbW) * static_cast<size_t>(thumbH) * 4;
    std::vector<uint8_t> out(expectedBytes, 0);

    float scaleX = static_cast<float>(srcW) / thumbW;
    float scaleY = static_cast<float>(srcH) / thumbH;

    for (int dy = 0; dy < thumbH; ++dy) {
        int sy = static_cast<int>(dy * scaleY);
        if (sy >= srcH) sy = srcH - 1;
        for (int dx = 0; dx < thumbW; ++dx) {
            int sx = static_cast<int>(dx * scaleX);
            if (sx >= srcW) sx = srcW - 1;

            int tileX = sx / canvas::Tile::TILE_SIZE;
            int tileY = sy / canvas::Tile::TILE_SIZE;
            int localX = sx % canvas::Tile::TILE_SIZE;
            int localY = sy % canvas::Tile::TILE_SIZE;

            const auto* tile = const_cast<canvas::TileGrid&>(grid).getTile(tileX, tileY);
            raster::ColorRGBA px = tile ? tile->getBuffer().getPixel(localX, localY) : raster::ColorRGBA{0, 0, 0, 0};

            size_t outIdx = static_cast<size_t>((dy * thumbW + dx) * 4);
            out[outIdx + 0] = px.r;
            out[outIdx + 1] = px.g;
            out[outIdx + 2] = px.b;
            out[outIdx + 3] = px.a;
        }
    }
    return out;
}

} // namespace aladyn::engine::boundary
