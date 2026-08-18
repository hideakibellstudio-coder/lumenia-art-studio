#include "PaintEngineFacade.hpp"
#include "../../core/brush/DynamicMapper.hpp"
#include "../../core/raster/DabInterpolator.hpp"
#include "../../core/raster/DabRenderer.hpp"
#include "../../core/raster/PixelContext.hpp"
#include "../../core/engines/PencilEngine.hpp"
#include "../../core/engines/InkerEngine.hpp"
#include "../../core/engines/EraserEngine.hpp"
#include "../../core/engines/MarkerEngine.hpp"
#include "../../core/engines/BlurEngine.hpp"
#include "../../core/engines/SmudgeEngine.hpp"
#include "../../core/engines/WatercolorEngine.hpp"
#include "../../core/engines/OilImpastoEngine.hpp"
#include <algorithm>
#include <cmath>
#include <random>
#include <stdexcept>

namespace aladyn::engine::boundary {

PaintEngineFacade::PaintEngineFacade(int width, int height)
    : m_width(width), m_height(height),
      m_layerStack(width, height),
      m_compositor(width, height),
      m_outputBuffer(width, height, {255, 255, 255, 255}),
      m_scratchGrid(width, height) {

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
int PaintEngineFacade::addLayer(const std::string& name) {
    int newIdx = m_layerStack.addLayer(name);
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    return newIdx;
}

int PaintEngineFacade::addGroup(const std::string& name) {
    int newIdx = m_layerStack.addGroup(name);
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    return newIdx;
}

int PaintEngineFacade::addFilterLayer(const std::string& name, int filterTypeId) {
    auto type = static_cast<document::FilterType>(filterTypeId);
    int newIdx = m_layerStack.addFilterLayer(name, type);
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    return newIdx;
}

void PaintEngineFacade::setFilterParams(int index, const std::vector<float>& params) {
    document::Layer* layer = m_layerStack.getDrawingLayer(index);
    if (layer && layer->isFilter()) {
        auto* filterLayer = dynamic_cast<document::FilterLayer*>(layer);
        if (filterLayer) {
            filterLayer->setParams(params);
            m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
        }
    }
}

std::vector<float> PaintEngineFacade::getFilterParams(int index) const {
    const document::Layer* layer = m_layerStack.getDrawingLayer(index);
    if (layer && layer->isFilter()) {
        const auto* filterLayer = dynamic_cast<const document::FilterLayer*>(layer);
        if (filterLayer) {
            return filterLayer->getParams();
        }
    }
    return {};
}

int PaintEngineFacade::getFilterType(int index) const {
    const document::Layer* layer = m_layerStack.getDrawingLayer(index);
    if (layer && layer->isFilter()) {
        const auto* filterLayer = dynamic_cast<const document::FilterLayer*>(layer);
        if (filterLayer) {
            return static_cast<int>(filterLayer->getFilterType());
        }
    }
    return -1;
}

bool PaintEngineFacade::isFilterLayer(int index) const {
    const document::Layer* layer = m_layerStack.getDrawingLayer(index);
    return layer ? layer->isFilter() : false;
}

bool PaintEngineFacade::isGroup(int index) const {
    return m_layerStack.isGroup(index);
}

bool PaintEngineFacade::setGroupPassThrough(int index, bool passThrough) {
    return m_layerStack.setGroupPassThrough(index, passThrough);
}

bool PaintEngineFacade::removeLayer(int index) {
    bool ok = m_layerStack.removeLayer(index);
    if (ok) {
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
}

int PaintEngineFacade::duplicateLayer(int index) {
    int dupIdx = m_layerStack.duplicateLayer(index);
    if (dupIdx >= 0) {
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return dupIdx;
}

bool PaintEngineFacade::selectLayer(int index) {
    return m_layerStack.selectLayer(index);
}

bool PaintEngineFacade::reorderLayer(int fromIndex, int toIndex) {
    bool ok = m_layerStack.reorderLayer(fromIndex, toIndex);
    if (ok) {
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
}

bool PaintEngineFacade::reorderLayers(const std::vector<int>& newOrder) {
    bool ok = m_layerStack.reorderLayers(newOrder);
    if (ok) {
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
}

bool PaintEngineFacade::setLayerParents(const std::vector<int>& parentIndices) {
    bool ok = m_layerStack.setLayerParents(parentIndices);
    if (ok) {
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
}

void PaintEngineFacade::setLayerName(int index, const std::string& name) {
    document::Layer* layer = m_layerStack.getDrawingLayer(index);
    if (layer) {
        layer->setName(name);
    }
}

void PaintEngineFacade::setLayerOpacity(int index, double opacity) {
    document::Layer* layer = m_layerStack.getDrawingLayer(index);
    if (layer) {
        layer->setOpacity(opacity);
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
}

void PaintEngineFacade::setLayerBlendMode(int index, int blendModeId) {
    document::Layer* layer = m_layerStack.getDrawingLayer(index);
    if (layer) {
        layer->setBlendMode(static_cast<document::LayerBlendMode>(blendModeId));
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
}

void PaintEngineFacade::setLayerVisibility(int index, bool visible) {
    document::Layer* layer = m_layerStack.getDrawingLayer(index);
    if (layer) {
        layer->setVisible(visible);
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
}

void PaintEngineFacade::setLayerLock(int index, bool locked) {
    document::Layer* layer = m_layerStack.getDrawingLayer(index);
    if (layer) {
        layer->setLocked(locked);
    }
}

void PaintEngineFacade::setLayerAlphaLock(int index, bool locked) {
    document::Layer* layer = m_layerStack.getDrawingLayer(index);
    if (layer) {
        layer->setAlphaLocked(locked);
    }
}

bool PaintEngineFacade::isLayerAlphaLocked(int index) const noexcept {
    const document::Layer* layer = m_layerStack.getDrawingLayer(index);
    return layer ? layer->isAlphaLocked() : false;
}

void PaintEngineFacade::setLayerClippingMask(int index, bool clipped) {
    document::Layer* layer = m_layerStack.getDrawingLayer(index);
    if (layer) {
        layer->setClippingMask(clipped);
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
}

bool PaintEngineFacade::isLayerClippingMask(int index) const noexcept {
    const document::Layer* layer = m_layerStack.getDrawingLayer(index);
    return layer ? layer->isClippingMask() : false;
}

bool PaintEngineFacade::flattenGroup(int index) {
    bool ok = m_layerStack.flattenGroup(index);
    if (ok) {
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
}

bool PaintEngineFacade::mergeLayerDown(int index) {
    bool ok = m_layerStack.mergeLayerDown(index);
    if (ok) {
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
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
    m_layerStack.getBackgroundLayer().getTileGrid().clearAll({r, g, b, a});
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
}

void PaintEngineFacade::resizeCanvas(int width, int height) {
    m_width = width;
    m_height = height;
    m_outputBuffer = canvas::PixelBuffer(width, height, m_canvasTexture.backgroundColor);
    m_layerStack.resize(width, height);
    m_compositor = document::Compositor(width, height);
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
}

void PaintEngineFacade::clearCanvas() {
    m_layerStack.clearAllDrawingLayers();
    m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
}

void PaintEngineFacade::clearLayer(int index) {
    document::Layer* layer = m_layerStack.getDrawingLayer(index);
    if (layer) {
        m_undoManager.beginStep("Clear Layer");
        auto& grid = layer->getTileGrid();
        for (int ty = 0; ty < grid.getTilesCountY(); ++ty) {
            for (int tx = 0; tx < grid.getTilesCountX(); ++tx) {
                canvas::Tile* tile = grid.getTile(tx, ty);
                if (tile) {
                    const auto& buf = tile->getBuffer();
                    m_undoManager.recordTileBefore(index, tx, ty, buf.getData(), buf.getSizeInBytes());
                }
            }
        }

        grid.clearAll({0, 0, 0, 0});
        m_undoManager.commitStep(m_layerStack);
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer);
    }
}

bool PaintEngineFacade::undo() {
    bool ok = m_undoManager.undo(m_layerStack);
    if (ok) {
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
}

bool PaintEngineFacade::redo() {
    bool ok = m_undoManager.redo(m_layerStack);
    if (ok) {
        m_compositor.composite(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    return ok;
}

void PaintEngineFacade::setShapePreset(int presetId) {
    const auto preset = static_cast<texture::ShapePreset>(std::clamp(presetId, 0, 3));
    m_brushProfile.shapeTexture = texture::ProceduralTextures::createShapePreset(preset, 256);
}

void PaintEngineFacade::setBrushHeightPreset(int presetId) {
    const auto preset = static_cast<texture::HeightPreset>(std::clamp(presetId, 0, 3));
    m_brushProfile.brushHeightTexture = texture::ProceduralTextures::createHeightPreset(preset, 512, 512);
}

void PaintEngineFacade::setCanvasHeightPreset(int presetId) {
    const auto preset = static_cast<texture::HeightPreset>(std::clamp(presetId, 0, 3));
    m_canvasTexture.canvasHeightTexture = texture::ProceduralTextures::createHeightPreset(preset, 512, 512);
}

void PaintEngineFacade::loadShapeTextureFromBuffer(int width, int height, const uint8_t* buffer) {
    if (width <= 0 || height <= 0 || !buffer) return;
    m_brushProfile.shapeTexture = std::make_shared<texture::Texture2D>(
        width, height, std::vector<uint8_t>(buffer, buffer + (width * height)));
}

void PaintEngineFacade::loadBrushHeightTextureFromBuffer(int width, int height, const uint8_t* buffer) {
    if (width <= 0 || height <= 0 || !buffer) return;
    m_brushProfile.brushHeightTexture = std::make_shared<texture::Texture2D>(
        width, height, std::vector<uint8_t>(buffer, buffer + (width * height)));
}

void PaintEngineFacade::loadCanvasHeightTextureFromBuffer(int width, int height, const uint8_t* buffer) {
    if (width <= 0 || height <= 0 || !buffer) return;
    m_canvasTexture.canvasHeightTexture = std::make_shared<texture::Texture2D>(
        width, height, std::vector<uint8_t>(buffer, buffer + (width * height)));
}

void PaintEngineFacade::beginStroke(const stroke::PointerEvent& event) {
    m_isDrawing = true;
    m_velocityTracker.reset(event.position, event.timestamp);
    m_stabilizer.reset(event.position);
    m_undoManager.beginStep("Stroke");

    if (m_activeEngine) m_activeEngine->onBeginStroke();

    const auto mapped = brush::DynamicMapper::map(m_brushProfile, event.position, event.pressure, 0.0, 0.0);
    m_lastDab = raster::Dab{mapped.position, mapped.radius, mapped.opacity, mapped.pressure,
                             mapped.angle, m_brushProfile.blendMode, mapped.color};

    document::Layer* activeLayer = m_layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isFilter() || activeLayer->isGroup()) {
        m_isDrawing = false;
        return;
    }

    // Checagem recursiva de visibilidade e bloqueio de pais
    bool effVis    = activeLayer->isVisible();
    bool effLocked = activeLayer->isLocked();
    const document::LayerNode* curr = activeLayer->getParent();
    while (curr) {
        if (!curr->isVisible()) effVis    = false;
        if ( curr->isLocked()) effLocked = true;
        curr = curr->getParent();
    }
    if (!effVis || effLocked) { m_isDrawing = false; return; }

    // ─── Inicializa o scratch layer para este traço
    const bool useScratch = !m_activeEngine || m_activeEngine->usesScratchLayer();
    if (useScratch) {
        m_scratchGrid.clearTiles();
        m_hasScratch         = true;
        m_scratchLayerIndex  = m_layerStack.getActiveIndex();
        m_scratchBlendMode   = activeLayer->getBlendMode();
        m_scratchOpacity     = activeLayer->getOpacity() * std::clamp(m_brushProfile.opacity, 0.0, 1.0);
    } else {
        m_hasScratch = false;
    }

    // Renderiza o primeiro dab do beginStroke (ponto de toque inicial)
    const math::Rect2D firstDabBounds{
        m_lastDab.position.x - m_lastDab.radius - 2.0,
        m_lastDab.position.y - m_lastDab.radius - 2.0,
        (m_lastDab.radius + 2.0) * 2.0,
        (m_lastDab.radius + 2.0) * 2.0
    };
    renderStrokeSegment(m_lastDab, m_lastDab);
}

TelemetryData PaintEngineFacade::updateStroke(const stroke::PointerEvent& event) {
    if (!m_isDrawing) return TelemetryData{0.0, 0.0, 0.0};

    const double smoothedVel = m_velocityTracker.update(event.position, event.timestamp);
    const double normVel     = m_velocityTracker.getNormalizedVelocity(1500.0);
    const math::Point2D stabilizedPos = m_stabilizer.update(event.position);

    double strokeAngle = m_lastDab.angle;
    const double dx = stabilizedPos.x - m_lastDab.position.x;
    const double dy = stabilizedPos.y - m_lastDab.position.y;
    if (dx * dx + dy * dy > 0.001) {
        strokeAngle = std::atan2(dy, dx) * (180.0 / 3.14159265358979323846);
    }

    const auto mapped = brush::DynamicMapper::map(m_brushProfile, stabilizedPos,
                                                   event.pressure, normVel, strokeAngle);
    const raster::Dab currentDab{mapped.position, mapped.radius, mapped.opacity, mapped.pressure,
                                   mapped.angle, m_brushProfile.blendMode, mapped.color};

    renderStrokeSegment(m_lastDab, currentDab);
    m_lastDab = currentDab;

    return TelemetryData{event.pressure, smoothedVel, mapped.opacity};
}

void PaintEngineFacade::endStroke(const stroke::PointerEvent& event) {
    if (!m_isDrawing) return;
    updateStroke(event);
    if (m_activeEngine) m_activeEngine->onEndStroke();

    // ─── Commit da scratch layer na camada ativa
    if (m_hasScratch) {
        commitScratch();
        m_hasScratch = false;
    }

    m_isDrawing = false;
    m_undoManager.commitStep(m_layerStack);

    // Composite final limpo (sem scratch) para sincronizar m_outputBuffer
    const math::Rect2D fullCanvas{0.0, 0.0,
        static_cast<double>(m_width), static_cast<double>(m_height)};
    m_compositor.compositeRegion(
        m_layerStack.getAllLayersForComposition(), fullCanvas,
        m_outputBuffer, m_canvasTexture.backgroundColor
    );
}

// ─── COMMIT SCRATCH → CAMADA ATIVA ──────────────────────────────────────────
// Para cada tile do scratch, mescla seu conteúdo sobre o tile correspondente
// da camada ativa usando composição "over" simples (Normal blend mode).
// O blend mode real da camada é aplicado pelo Compositor — o scratch é
// apenas acúmulo de tinta pura, sem reacumulação entre dabs do mesmo traço.
void PaintEngineFacade::commitScratch() {
    document::Layer* activeLayer = m_layerStack.getActiveLayer();
    if (!activeLayer) return;

    auto& layerGrid    = activeLayer->getTileGrid();
    const int activeIdx = m_layerStack.getActiveIndex();
    const bool alphaLocked = activeLayer->isAlphaLocked();

    // Clip base para alpha lock por máscara de recorte
    const document::Layer* clipBaseLayer = activeLayer->isClippingMask()
        ? m_layerStack.getClipBaseLayer(activeIdx)
        : nullptr;

    m_scratchGrid.forEachTile([&](const canvas::TileIndex& idx, canvas::Tile& scratchTile) {
        const canvas::PixelBuffer& scratchBuf = scratchTile.getBuffer();
        const int tx = idx.x;
        const int ty = idx.y;

        // Grava undo ANTES de modificar o tile da camada real
        canvas::Tile* layerTile = layerGrid.getTile(tx, ty);
        if (layerTile) {
            const auto& buf = layerTile->getBuffer();
            m_undoManager.recordTileBefore(activeIdx, tx, ty, buf.getData(), buf.getSizeInBytes());
        } else {
            canvas::PixelBuffer emptyBuf(canvas::Tile::TILE_SIZE, canvas::Tile::TILE_SIZE, {0, 0, 0, 0});
            m_undoManager.recordTileBefore(activeIdx, tx, ty, emptyBuf.getData(), emptyBuf.getSizeInBytes());
        }

        // Cria/obtém o tile destino na camada ativa
        canvas::Tile* dstTile = layerGrid.getOrCreateTile(tx, ty);
        if (!dstTile) return;
        canvas::PixelBuffer& dstBuf = dstTile->getBuffer();

        bool tileModified = false;
        for (int py = 0; py < canvas::Tile::TILE_SIZE; ++py) {
            const int globalY = ty * canvas::Tile::TILE_SIZE + py;
            for (int px = 0; px < canvas::Tile::TILE_SIZE; ++px) {
                const raster::ColorRGBA scratch = scratchBuf.getPixel(px, py);
                if (scratch.a == 0) continue;

                const int globalX = tx * canvas::Tile::TILE_SIZE + px;

                // Clip mask: respeita o alpha da camada base
                if (clipBaseLayer) {
                    const int bTx = globalX / canvas::Tile::TILE_SIZE;
                    const int bTy = globalY / canvas::Tile::TILE_SIZE;
                    const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(
                        clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                    if (!bTile) continue;
                    const double baseA = static_cast<double>(
                        bTile->getBuffer().getPixel(
                            globalX % canvas::Tile::TILE_SIZE,
                            globalY % canvas::Tile::TILE_SIZE).a) / 255.0;
                    if (baseA <= 0.0) continue;
                }

                const raster::ColorRGBA dst = dstBuf.getPixel(px, py);

                if (alphaLocked) {
                    // Alpha locked: só modifica RGB onde já há tinta
                    if (dst.a == 0) continue;
                    const double brushOp = std::clamp(m_brushProfile.opacity, 0.0, 1.0);
                    const double srcA    = (static_cast<double>(scratch.a) / 255.0) * brushOp;
                    const double dstA    = static_cast<double>(dst.a)     / 255.0;
                    const double invSrcA = 1.0 - srcA;
                    const double denom   = srcA + dstA * invSrcA;
                    if (denom <= 0.0) continue;
                    dstBuf.setPixel(px, py, raster::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(
                            (scratch.r * srcA + dst.r * dstA * invSrcA) / denom, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(
                            (scratch.g * srcA + dst.g * dstA * invSrcA) / denom, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(
                            (scratch.b * srcA + dst.b * dstA * invSrcA) / denom, 0.0, 255.0)),
                        dst.a
                    });
                } else {
                    // Normal "over" compositing: scratch sobre o conteúdo existente
                    const double brushOp = std::clamp(m_brushProfile.opacity, 0.0, 1.0);
                    const double srcA = (static_cast<double>(scratch.a) / 255.0) * brushOp;
                    const double dstA = static_cast<double>(dst.a)     / 255.0;
                    const double outA = srcA + dstA * (1.0 - srcA);
                    if (outA <= 0.0) continue;
                    dstBuf.setPixel(px, py, raster::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(
                            (scratch.r * srcA + dst.r * dstA * (1.0 - srcA)) / outA, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(
                            (scratch.g * srcA + dst.g * dstA * (1.0 - srcA)) / outA, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(
                            (scratch.b * srcA + dst.b * dstA * (1.0 - srcA)) / outA, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outA * 255.0, 0.0, 255.0))
                    });
                }
                tileModified = true;
            }
        }
        if (tileModified) dstTile->setDirty(true);
    });

    m_scratchGrid.clearTiles();
}

void PaintEngineFacade::renderStrokeSegment(const raster::Dab& startDab, const raster::Dab& endDab) {
    document::Layer* activeLayer = m_layerStack.getActiveLayer();
    if (!activeLayer) return;

    // Checagem recursiva de visibilidade e bloqueio de pais
    bool effVis = activeLayer->isVisible();
    bool effLocked = activeLayer->isLocked();
    const document::LayerNode* curr = activeLayer->getParent();
    while (curr) {
        if (!curr->isVisible()) effVis = false;
        if (curr->isLocked()) effLocked = true;
        curr = curr->getParent();
    }

    if (!effVis || effLocked) return;

    double minX = std::min(startDab.position.x - startDab.radius, endDab.position.x - endDab.radius);
    double maxX = std::max(startDab.position.x + startDab.radius, endDab.position.x + endDab.radius);
    double minY = std::min(startDab.position.y - startDab.radius, endDab.position.y - endDab.radius);
    double maxY = std::max(startDab.position.y + startDab.radius, endDab.position.y + endDab.radius);

    const double aspect = std::max(0.05, m_brushProfile.tip.aspectRatio);
    const double padding = 8.0 / aspect + 4.0;
    const math::Rect2D dirtyBounds{
        minX - padding, minY - padding,
        (maxX - minX) + padding * 2.0, (maxY - minY) + padding * 2.0
    };

    const document::Layer* clipBaseLayer = activeLayer->isClippingMask()
        ? m_layerStack.getClipBaseLayer(m_layerStack.getActiveIndex())
        : nullptr;

    const raster::PixelContext pCtx{ activeLayer->isAlphaLocked(), clipBaseLayer };

    const auto interpolatedDabs = raster::DabInterpolator::interpolate(
        startDab, endDab, m_brushProfile.spacingFactor
    );

    auto& layerGrid  = activeLayer->getTileGrid();
    const int activeIdx = m_layerStack.getActiveIndex();

    // ─── Decide o destino dos dabs: scratch (maioria dos motores) ou camada direta (Blur/Smudge)
    const bool useScratch = m_hasScratch;
    canvas::TileGrid& targetGrid = useScratch ? m_scratchGrid : layerGrid;

    // Para motores sem scratch (Blur/Smudge), grava undo dos tiles antes de desenhar
    if (!useScratch) {
        const int startTileX = static_cast<int>(std::floor((minX - padding) / canvas::Tile::TILE_SIZE));
        const int endTileX   = static_cast<int>(std::floor((maxX + padding) / canvas::Tile::TILE_SIZE));
        const int startTileY = static_cast<int>(std::floor((minY - padding) / canvas::Tile::TILE_SIZE));
        const int endTileY   = static_cast<int>(std::floor((maxY + padding) / canvas::Tile::TILE_SIZE));

        for (int ty = startTileY; ty <= endTileY; ++ty) {
            for (int tx = startTileX; tx <= endTileX; ++tx) {
                canvas::Tile* tile = layerGrid.getTile(tx, ty);
                if (tile) {
                    const auto& buf = tile->getBuffer();
                    m_undoManager.recordTileBefore(activeIdx, tx, ty, buf.getData(), buf.getSizeInBytes());
                } else {
                    canvas::PixelBuffer emptyBuf(canvas::Tile::TILE_SIZE, canvas::Tile::TILE_SIZE, {0, 0, 0, 0});
                    m_undoManager.recordTileBefore(activeIdx, tx, ty, emptyBuf.getData(), emptyBuf.getSizeInBytes());
                }
            }
        }
    }

    static thread_local std::mt19937 rng(777);
    std::uniform_real_distribution<double> distScatter(-1.0, 1.0);

    for (const auto& dab : interpolatedDabs) {
        const int scatter = (m_brushProfile.scatterCount > 1) ? m_brushProfile.scatterCount : 1;

        for (int s = 0; s < scatter; ++s) {
            raster::Dab renderDab = dab;
            if (scatter > 1) {
                renderDab.position.x += distScatter(rng) * dab.radius * 0.8;
                renderDab.position.y += distScatter(rng) * dab.radius * 0.8;
            }

            if (m_activeEngine) {
                // Blur/Smudge recebem a camada real como targetGrid; os demais recebem o scratch.
                // compositeBuffer (m_outputBuffer) é sempre passado para Blur/Smudge o usarem.
                m_activeEngine->renderDab(renderDab, m_brushProfile, m_canvasTexture,
                                          targetGrid, &m_outputBuffer, pCtx);
            } else {
                raster::DabRenderer::renderDab(renderDab, m_brushProfile, m_canvasTexture,
                                               targetGrid, pCtx);
            }
        }
    }

    // ─── Composição para display em tempo real
    if (useScratch) {
        // Durante o traço com scratch: exibe [camada ativa existente] + [scratch overlay] + [outras camadas]
        m_compositor.compositeRegionWithScratch(
            m_layerStack.getAllLayersForComposition(), dirtyBounds,
            m_outputBuffer, m_canvasTexture.backgroundColor,
            m_scratchGrid, m_scratchLayerIndex,
            m_scratchBlendMode, m_scratchOpacity
        );
    } else {
        // Blur/Smudge: composição normal pois já escreveram direto na camada
        m_compositor.compositeRegion(
            m_layerStack.getAllLayersForComposition(), dirtyBounds,
            m_outputBuffer, m_canvasTexture.backgroundColor
        );
    }
}

} // namespace aladyn::engine::boundary
