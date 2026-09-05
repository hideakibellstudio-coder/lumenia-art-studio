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
#include "../../core/raster/ColorProfileManager.hpp"
#include "internal/StrokeOrchestrator.hpp"
#include "internal/SelectionOrchestrator.hpp"
#include "internal/TransformOrchestrator.hpp"
#include "internal/BufferPasteOrchestrator.hpp"
#include "internal/LayerStackOrchestrator.hpp"
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

#ifdef _WIN32
    _putenv("OMP_WAIT_POLICY=PASSIVE");
#endif

    initEngine(brush::EngineType::Brush);
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
}

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

int PaintEngineFacade::getActiveEngineType() const noexcept {
    return static_cast<int>(m_brushProfile.engineType);
}

// ─── GERENCIAMENTO DE CAMADAS ─────────────────────────────────────────────

int PaintEngineFacade::addLayer(const std::string& name, int insertIndex) {
    return internal::LayerStackOrchestrator::addLayer(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, name, insertIndex);
}

int PaintEngineFacade::addGroup(const std::string& name, int insertIndex) {
    return internal::LayerStackOrchestrator::addGroup(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, name, insertIndex);
}

int PaintEngineFacade::addFilterLayer(const std::string& name, int filterTypeId, int insertIndex) {
    return internal::LayerStackOrchestrator::addFilterLayer(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, name, filterTypeId, insertIndex);
}

void PaintEngineFacade::setFilterParams(int index, const std::vector<float>& params) {
    auto* l = m_layerStack.getDrawingLayer(index);
    if (auto* fl = dynamic_cast<document::FilterLayer*>(l)) {
        for (size_t i = 0; i < params.size(); ++i) fl->setParam(i, params[i]);
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
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

bool PaintEngineFacade::isFilterLayer(int index) const {
    const auto* l = m_layerStack.getDrawingLayer(index);
    return l && l->isFilter();
}

bool PaintEngineFacade::isGroup(int index) const {
    return m_layerStack.isGroup(index);
}

bool PaintEngineFacade::setGroupPassThrough(int index, bool passThrough) {
    bool ok = m_layerStack.setGroupPassThrough(index, passThrough);
    if (ok) m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    return ok;
}

bool PaintEngineFacade::removeLayer(int index) {
    return internal::LayerStackOrchestrator::removeLayer(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index);
}

int PaintEngineFacade::duplicateLayer(int index) {
    return internal::LayerStackOrchestrator::duplicateLayer(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index);
}

bool PaintEngineFacade::selectLayer(int index) {
    return m_layerStack.selectLayer(index);
}

bool PaintEngineFacade::reorderLayer(int fromIndex, int toIndex) {
    return internal::LayerStackOrchestrator::reorderLayer(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, fromIndex, toIndex);
}

bool PaintEngineFacade::reorderLayers(const std::vector<int>& newOrder) {
    return internal::LayerStackOrchestrator::reorderLayers(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, newOrder);
}

bool PaintEngineFacade::setLayerParents(const std::vector<int>& parentIndices) {
    return internal::LayerStackOrchestrator::setLayerParents(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, parentIndices);
}

void PaintEngineFacade::setLayerName(int index, const std::string& name) {
    if (auto* l = m_layerStack.getDrawingLayer(index)) l->setName(name);
}

void PaintEngineFacade::setLayerOpacity(int index, double opacity) {
    internal::LayerStackOrchestrator::setLayerOpacity(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index, opacity);
}

void PaintEngineFacade::setLayerBlendMode(int index, int blendModeId) {
    internal::LayerStackOrchestrator::setLayerBlendMode(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index, blendModeId);
}

void PaintEngineFacade::setLayerVisibility(int index, bool visible) {
    internal::LayerStackOrchestrator::setLayerVisibility(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index, visible);
}

void PaintEngineFacade::setLayerLock(int index, bool locked) {
    if (auto* l = m_layerStack.getDrawingLayer(index)) l->setLocked(locked);
}

void PaintEngineFacade::setLayerAlphaLock(int index, bool locked) {
    if (auto* l = m_layerStack.getDrawingLayer(index)) l->setAlphaLocked(locked);
}

bool PaintEngineFacade::isLayerAlphaLocked(int index) const noexcept {
    const auto* l = m_layerStack.getDrawingLayer(index);
    return l ? l->isAlphaLocked() : false;
}

void PaintEngineFacade::setLayerClippingMask(int index, bool clipped) {
    internal::LayerStackOrchestrator::setLayerClippingMask(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index, clipped);
}

bool PaintEngineFacade::isLayerClippingMask(int index) const noexcept {
    const auto* l = m_layerStack.getDrawingLayer(index);
    return l ? l->isClippingMask() : false;
}

bool PaintEngineFacade::flattenGroup(int index) {
    return internal::LayerStackOrchestrator::flattenGroup(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index);
}

bool PaintEngineFacade::mergeLayerDown(int index) {
    return internal::LayerStackOrchestrator::mergeLayerDown(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index);
}

void PaintEngineFacade::clearLayer(int index) {
    internal::LayerStackOrchestrator::clearLayer(m_layerStack, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, index);
}

void PaintEngineFacade::setBackgroundVisibility(bool visible) {
    m_layerStack.getBackgroundLayer().setVisible(visible);
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
}

bool PaintEngineFacade::isBackgroundVisible() const noexcept {
    return m_layerStack.getBackgroundLayer().isVisible();
}

void PaintEngineFacade::setBackgroundColor(uint8_t r, uint8_t g, uint8_t b, uint8_t a) {
    m_canvasTexture.backgroundColor = {r, g, b, a};
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
}

void PaintEngineFacade::resizeCanvas(int width, int height) {
    m_width = width;
    m_height = height;
    m_layerStack.resize(width, height);
    m_compositor = document::Compositor(width, height);
    m_outputBuffer.resize(width, height, m_canvasTexture.backgroundColor);
    m_displayBuffer.resize(width, height, m_canvasTexture.backgroundColor);
    m_selectionMask.resize(width, height);
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
}

void PaintEngineFacade::clearCanvas() {
    auto* active = m_layerStack.getActiveLayer();
    if (active && !active->isLocked() && !active->isGroup() && !active->isFilter()) {
        active->getTileGrid().clearTiles();
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
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
    auto mapped = brush::DynamicMapper::map(m_brushProfile, event.position, event.pressure, 0.0, 0.0);
    m_lastDab = raster::Dab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, m_brushProfile.blendMode, mapped.color);
    m_telemetryManager.onBeginStroke(event.pressure, static_cast<int>(m_brushProfile.engineType));
}

TelemetryData PaintEngineFacade::updateStroke(const stroke::PointerEvent& event) {
    if (!m_isDrawing) return {0.0, 0.0, 0.0};
    ++m_segmentsRenderedInStroke;
    m_lastRawPressure = event.pressure;
    const double currentVelocity = m_velocityTracker.update(event.position, event.timestamp);
    const double normVel = m_velocityTracker.getNormalizedVelocity(1500.0);
    math::Point2D pos = m_stabilizer.update(event.position, normVel);
    auto mapped = brush::DynamicMapper::map(m_brushProfile, pos, event.pressure, normVel, 0.0);
    raster::Dab currentDab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, m_brushProfile.blendMode, mapped.color);
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

void PaintEngineFacade::beginStrokeRaw(double x, double y, double pressure, double timestamp) {
    m_lastRawPoint = {x, y};
    m_hasLastRawPoint = true;
    m_lastRawPressure = pressure;
    m_pendingFirstSegment = false;
    double t = timestamp;
    if (t <= 0.0) {
        auto now = std::chrono::high_resolution_clock::now();
        t = std::chrono::duration<double>(now.time_since_epoch()).count();
    }
    beginStroke({stroke::PointerEventType::Press, {x, y}, pressure, t});
}

std::vector<double> PaintEngineFacade::updateStrokeRaw(double x, double y, double pressure, double timestamp) {
    if (!m_isDrawing) return {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    m_lastRawPoint = {x, y};
    m_hasLastRawPoint = true;
    m_lastRawPressure = pressure;

    auto tKinematicsStart = std::chrono::high_resolution_clock::now();

    double t = timestamp;
    if (t <= 0.0) {
        auto now = std::chrono::high_resolution_clock::now();
        t = std::chrono::duration<double>(now.time_since_epoch()).count();
    }

    const double vel = m_velocityTracker.update({x, y}, t);
    const double normVel = m_velocityTracker.getNormalizedVelocity(1500.0);
    const math::Point2D pos = m_stabilizer.update({x, y}, normVel);

    // Amostra 1 do movimento (P1): Reter para confirmar alinhamento direcional com P2
    if (m_segmentsRenderedInStroke == 0 && !m_pendingFirstSegment) {
        m_firstSample.rawPoint = {x, y};
        m_firstSample.pressure = pressure;
        m_firstSample.timestamp = t;
        m_firstSample.stabilizedPos = pos;
        m_firstSample.normVel = normVel;
        m_firstSample.vel = vel;
        m_pendingFirstSegment = true;
        m_segmentsRenderedInStroke = 1;
        return { 0.0, 0.0, 0.0, 0.0, x, y, pressure, vel, m_lastDab.opacity };
    }

    auto tKinematicsEnd = std::chrono::high_resolution_clock::now();
    double timeKinematicsUs = std::chrono::duration<double, std::micro>(tKinematicsEnd - tKinematicsStart).count();

    math::Rect2D dirty{0, 0, 0, 0};
    uint32_t dabsRendered = 0;
    auto tStart = std::chrono::high_resolution_clock::now();
    telemetry::StageMetrics totalStages{};

    // Amostra 2 do movimento (P2 com P1 pendente):
    // Avalia o alinhamento entre o pouso (P0 -> P1) e a trajetória da curva (P1 -> P2)
    if (m_pendingFirstSegment) {
        const math::Point2D p0 = m_strokeStartPoint;
        const math::Point2D p1 = m_firstSample.rawPoint;
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
                m_strokeStartPoint = alignedP0;
                m_stabilizer.reanchorInitialPosition(alignedP0);

                auto mappedP0 = brush::DynamicMapper::map(m_brushProfile, alignedP0, m_lastDab.pressure, 0.0, 0.0);
                m_lastDab = raster::Dab(mappedP0.position, mappedP0.radius, mappedP0.opacity, mappedP0.pressure, mappedP0.angle, m_brushProfile.blendMode, mappedP0.color);
            }
        }

        // Renderiza o segmento 1 (P0 -> P1 estabilizado)
        auto mapped1 = brush::DynamicMapper::map(m_brushProfile, m_firstSample.stabilizedPos, m_firstSample.pressure, m_firstSample.normVel, 0.0);
        raster::Dab dab1(mapped1.position, mapped1.radius, mapped1.opacity, mapped1.pressure, mapped1.angle, m_brushProfile.blendMode, mapped1.color);
        math::Rect2D dirty1{0, 0, 0, 0};
        uint32_t dabs1 = 0;
        telemetry::StageMetrics stages1{};
        internal::StrokeOrchestrator::renderSegment(
            m_lastDab, dab1, m_brushProfile, m_canvasTexture,
            m_activeEngine.get(), m_layerStack, m_selectionMask,
            m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor,
            m_distanceCarryover, m_symmetryConfig, &m_strokeStartPoint, &dirty1, &dabs1,
            &stages1
        );
        totalStages.timeInterpolationUs += stages1.timeInterpolationUs;
        totalStages.timeRasterDabUs += stages1.timeRasterDabUs;
        totalStages.timeUndoRecordUs += stages1.timeUndoRecordUs;
        totalStages.timeCompositeUs += stages1.timeCompositeUs;
        totalStages.tilesRecorded += stages1.tilesRecorded;
        totalStages.tilesComposited += stages1.tilesComposited;

        m_lastDab = dab1;
        dirty = dirty1;
        dabsRendered += dabs1;
        m_pendingFirstSegment = false;
        ++m_segmentsRenderedInStroke;
    }

    // Renderiza o segmento atual
    auto mapped = brush::DynamicMapper::map(m_brushProfile, pos, pressure, normVel, 0.0);
    raster::Dab currentDab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, m_brushProfile.blendMode, mapped.color);
    math::Rect2D dirtyCurrent{0, 0, 0, 0};
    uint32_t dabsCurrent = 0;
    telemetry::StageMetrics stagesCurrent{};
    internal::StrokeOrchestrator::renderSegment(
        m_lastDab, currentDab, m_brushProfile, m_canvasTexture,
        m_activeEngine.get(), m_layerStack, m_selectionMask,
        m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor,
        m_distanceCarryover, m_symmetryConfig, &m_strokeStartPoint, &dirtyCurrent, &dabsCurrent,
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
    ++m_segmentsRenderedInStroke;

    totalStages.dabsRendered = dabsRendered;
    totalStages.dirtyWidth = dirty.width;
    totalStages.dirtyHeight = dirty.height;
    totalStages.dirtyAreaPx = dirty.width * dirty.height;

    if (m_telemetryManager.isEnabled()) {
        auto tEnd = std::chrono::high_resolution_clock::now();
        double latUs = std::chrono::duration<double, std::micro>(tEnd - tStart).count() + timeKinematicsUs;
        double lag = pos.distanceTo(math::Point2D{x, y});
        m_telemetryManager.onSegmentRenderedDetailed(latUs, timeKinematicsUs, totalStages, pressure, mapped.pressure, vel, lag);
    }

    m_lastDab = currentDab;
    return { dirty.x, dirty.y, dirty.width, dirty.height, x, y, pressure, vel, currentDab.opacity };
}

std::vector<double> PaintEngineFacade::endStrokeRaw() {
    math::Rect2D totalCatchupDirty{0, 0, 0, 0};
    telemetry::StageMetrics stagesCatchup{};

    if (m_isDrawing) {
        if (m_pendingFirstSegment) {
            auto mapped1 = brush::DynamicMapper::map(m_brushProfile, m_firstSample.stabilizedPos, m_firstSample.pressure, m_firstSample.normVel, 0.0);
            raster::Dab dab1(mapped1.position, mapped1.radius, mapped1.opacity, mapped1.pressure, mapped1.angle, m_brushProfile.blendMode, mapped1.color);
            math::Rect2D dirty1{0, 0, 0, 0};
            uint32_t dabs1 = 0;
            internal::StrokeOrchestrator::renderSegment(
                m_lastDab, dab1, m_brushProfile, m_canvasTexture,
                m_activeEngine.get(), m_layerStack, m_selectionMask,
                m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor,
                m_distanceCarryover, m_symmetryConfig, &m_strokeStartPoint, &dirty1, &dabs1
            );
            if (dirty1.width > 0 && dirty1.height > 0) {
                totalCatchupDirty = dirty1;
            }
            m_lastDab = dab1;
            m_pendingFirstSegment = false;
        }

        if (m_hasLastRawPoint && m_segmentsRenderedInStroke > 0) {
            const math::Point2D stabPos = m_stabilizer.getStabilizedPosition();
            const math::Point2D v = m_stabilizer.getLastMovementDelta();
            const double speed = v.length();
            const math::Point2D toRaw = m_lastRawPoint - stabPos;
            const double distToRaw = toRaw.length();

            bool isCollinear = false;
            if (speed > 0.1 && distToRaw > 0.5) {
                const double dot = (v.x * toRaw.x + v.y * toRaw.y) / (speed * distToRaw);
                isCollinear = (dot > 0.4);
            }

            math::Point2D targetPt = stabPos;
            bool shouldRenderCatchup = false;
            double targetPressure = m_lastRawPressure;
            double targetRadiusMult = 1.0;
            double targetOpacityMult = 1.0;

            if (isCollinear) {
                targetPt = m_lastRawPoint;
                shouldRenderCatchup = (distToRaw > 1.0);
                if (m_brushProfile.strokeTaperEnabled) {
                    targetPressure = 0.0;
                    targetRadiusMult = 0.1;
                    targetOpacityMult = 0.0;
                }
            } else if (m_brushProfile.strokeTaperEnabled && speed >= 0.3) {
                // Desvio/gancho de levantamento da caneta detectado (pen-up hook off-axis).
                // Projeta estritamente ao longo da tangente física do traço
                const double taperDist = std::min(m_lastDab.radius * 1.5, 35.0);
                const math::Point2D tangent = v * (1.0 / speed);
                targetPt = stabPos + (tangent * taperDist);
                targetPressure = 0.0;
                targetRadiusMult = 0.1;
                targetOpacityMult = 0.0;
                shouldRenderCatchup = true;
            }

            if (shouldRenderCatchup) {
                auto mapped = brush::DynamicMapper::map(m_brushProfile, targetPt, targetPressure, 0.0, 0.0);
                mapped.radius *= targetRadiusMult;
                mapped.opacity *= targetOpacityMult;
                raster::Dab currentDab(mapped.position, mapped.radius, mapped.opacity, mapped.pressure, mapped.angle, m_brushProfile.blendMode, mapped.color);
                math::Rect2D dirty{0, 0, 0, 0};
                uint32_t dabsRendered = 0;
                internal::StrokeOrchestrator::renderSegment(
                    m_lastDab, currentDab, m_brushProfile, m_canvasTexture,
                    m_activeEngine.get(), m_layerStack, m_selectionMask,
                    m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor,
                    m_distanceCarryover, m_symmetryConfig, &m_strokeStartPoint, &dirty, &dabsRendered,
                    &stagesCatchup
                );
                if (dirty.width > 0 && dirty.height > 0) {
                    totalCatchupDirty = (totalCatchupDirty.width > 0) ? totalCatchupDirty.united(dirty) : dirty;
                }
                m_lastDab = currentDab;
            }
                    }
    }

    auto now = std::chrono::high_resolution_clock::now();
    double t = std::chrono::duration<double>(now.time_since_epoch()).count();
    endStroke({stroke::PointerEventType::Release, m_stabilizer.getStabilizedPosition(), 0.0, t});
    m_hasLastRawPoint = false;
    m_pendingFirstSegment = false;

    if (totalCatchupDirty.width > 0 && totalCatchupDirty.height > 0) {
        return { totalCatchupDirty.x, totalCatchupDirty.y, totalCatchupDirty.width, totalCatchupDirty.height };
    }
    return { 0.0, 0.0, 0.0, 0.0 };
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
    bool antiAliasing, bool /*sampleAllLayers*/
) {
    document::Layer* activeLayer = m_layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) return false;

    // Clipping Mask é 100% não-destrutivo: o preenchimento atua no espaço da camada e o recorte é visual
    const raster::PixelContext pCtx{ activeLayer->isAlphaLocked(), nullptr, &m_selectionMask };

    m_undoManager.beginStep("Bucket Fill");
    math::Rect2D affectedBounds{0, 0, 0, 0};
    bool ok = raster::FloodFill::execute(
        m_outputBuffer, seedX, seedY, fillColor, tolerance, contiguous, expandPx, gapClosingPx, antiAliasing,
        activeLayer->getTileGrid(), m_undoManager, m_layerStack.getActiveIndex(), pCtx, affectedBounds
    );

    if (ok) {
        m_undoManager.commitStep(m_layerStack);
        m_compositor.compositeRegion(m_layerStack.getAllLayersForComposition(), affectedBounds, m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
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
void PaintEngineFacade::clearSelection() noexcept { m_selectionMask.clear(); }
void PaintEngineFacade::invertSelection() noexcept { m_selectionMask.invert(); }
void PaintEngineFacade::selectAll() noexcept { m_selectionMask.selectAll(); }
bool PaintEngineFacade::hasSelection() const noexcept { return m_selectionMask.hasSelection(); }
bool PaintEngineFacade::deleteSelectionOnActiveLayer() {
    return internal::SelectionOrchestrator::deleteSelectionOnActiveLayer(m_layerStack, m_selectionMask, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
}
bool PaintEngineFacade::fillSelectionOnActiveLayer(const raster::ColorRGBA& fillColor) {
    return internal::SelectionOrchestrator::fillSelectionOnActiveLayer(fillColor, m_layerStack, m_selectionMask, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
}
uint8_t* PaintEngineFacade::getSelectionMaskData() noexcept { return m_selectionMask.getData(); }
size_t PaintEngineFacade::getSelectionMaskSize() const noexcept { return m_selectionMask.getSizeInBytes(); }
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
    return internal::TransformOrchestrator::commitTransform(m_transformEngine, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, dx, dy, scaleX, scaleY, rotationDeg, pivotX, pivotY, flipH, flipV, interpMode, m_width, m_height);
}
bool PaintEngineFacade::cancelTransform() {
    return internal::TransformOrchestrator::cancelTransform(m_transformEngine, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor, m_width, m_height);
}
bool PaintEngineFacade::flipActiveLayer(bool horizontal) {
    return internal::TransformOrchestrator::flipActiveLayer(horizontal, m_width, m_height, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
}
bool PaintEngineFacade::rotateActiveLayer90(bool clockwise) {
    return internal::TransformOrchestrator::rotateActiveLayer90(clockwise, m_width, m_height, m_layerStack, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
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
    return internal::BufferPasteOrchestrator::paste(x, y, width, height, buffer, blendModeId, opacity, m_width, m_height, m_layerStack, m_selectionMask, m_undoManager, m_compositor, m_outputBuffer, m_canvasTexture.backgroundColor);
}

// ─── PRESETS E TEXTURAS PROCEDURAIS ────────────────────────────────────────

void PaintEngineFacade::setShapePreset(int id) { m_brushProfile.shapeTexture = texture::ProceduralTextures::createShapePreset(static_cast<texture::ShapePreset>(id)); }
void PaintEngineFacade::setBrushHeightPreset(int id) { m_brushProfile.brushHeightTexture = texture::ProceduralTextures::createHeightPreset(static_cast<texture::HeightPreset>(id)); }
void PaintEngineFacade::setCanvasHeightPreset(int id) { m_canvasTexture.canvasHeightTexture = texture::ProceduralTextures::createHeightPreset(static_cast<texture::HeightPreset>(id)); }
void PaintEngineFacade::loadShapeTextureFromBuffer(int w, int h, const uint8_t* buf) {
    if (buf && w > 0 && h > 0) m_brushProfile.shapeTexture = std::make_shared<texture::Texture2D>(w, h, std::vector<uint8_t>(buf, buf + static_cast<size_t>(w * h)));
}
void PaintEngineFacade::loadBrushHeightTextureFromBuffer(int w, int h, const uint8_t* buf) {
    if (buf && w > 0 && h > 0) m_brushProfile.brushHeightTexture = std::make_shared<texture::Texture2D>(w, h, std::vector<uint8_t>(buf, buf + static_cast<size_t>(w * h)));
}
void PaintEngineFacade::loadCanvasHeightTextureFromBuffer(int w, int h, const uint8_t* buf) {
    if (buf && w > 0 && h > 0) m_canvasTexture.canvasHeightTexture = std::make_shared<texture::Texture2D>(w, h, std::vector<uint8_t>(buf, buf + static_cast<size_t>(w * h)));
}
void PaintEngineFacade::setColorProfile(int profileId) noexcept { m_colorProfileId = profileId; }
void PaintEngineFacade::applyActiveColorProfile(uint8_t* targetBuffer, size_t numPixels) const noexcept {
    raster::ColorProfileManager::applyColorProfile(targetBuffer, numPixels, m_colorProfileId);
}
uint8_t* PaintEngineFacade::getDisplayRawPixelData() noexcept {
    if (m_colorProfileId == 0) return m_outputBuffer.getData();
    const size_t totalBytes = m_outputBuffer.getSizeInBytes();
    std::memcpy(m_displayBuffer.getData(), m_outputBuffer.getData(), totalBytes);
    applyActiveColorProfile(m_displayBuffer.getData(), totalBytes / 4);
    return m_displayBuffer.getData();
}
bool PaintEngineFacade::undo() {
    bool ok = m_undoManager.undo(m_layerStack);
    if (ok) {
        if (auto* layer = m_layerStack.getActiveLayer()) {
            layer->getTileGrid().pruneEmptyTiles();
        }
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
}
bool PaintEngineFacade::redo() {
    bool ok = m_undoManager.redo(m_layerStack);
    if (ok) {
        if (auto* layer = m_layerStack.getActiveLayer()) {
            layer->getTileGrid().pruneEmptyTiles();
        }
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
}
void PaintEngineFacade::setSymmetryConfig(int mode, double cx, double cy, double angleRad, int segments, bool stopAtCenter) {
    m_symmetryConfig = { static_cast<math::SymmetryMode>(mode), cx, cy, angleRad, segments, stopAtCenter };
}
void PaintEngineFacade::clearSymmetry() { m_symmetryConfig.mode = math::SymmetryMode::None; }
void PaintEngineFacade::setGuideConfig(
    int type, double p0x, double p0y, double p1x, double p1y, double p2x, double p2y, double p3x, double p3y,
    double vpAx, double vpAy, double vpBx, double vpBy, double vpCx, double vpCy, double cx, double cy,
    double fov, double pitch, double yaw, double snapRadius
) {
    m_guideConfig = { static_cast<math::GuideType>(type), {p0x, p0y}, {p1x, p1y}, {p2x, p2y}, {p3x, p3y}, {vpAx, vpAy}, {vpBx, vpBy}, {vpCx, vpCy}, cx, cy, fov, pitch, yaw, snapRadius };
}
void PaintEngineFacade::clearGuide() {
    m_guideConfig.type = math::GuideType::None;
}

std::vector<double> PaintEngineFacade::snapPoint(double rawX, double rawY, double lastX, double lastY, bool hasLast) const {
    const math::Point2D last{ lastX, lastY };
    const math::Point2D snapped = math::GuideSnapEngine::snapPoint(m_guideConfig, {rawX, rawY}, hasLast ? &last : nullptr);
    return { snapped.x, snapped.y };
}

} // namespace aladyn::engine::boundary
