#include "LayerStack.hpp"
#include "Compositor.hpp"
#include <algorithm>

namespace aladyn::engine::document {

LayerStack::LayerStack(int width, int height)
    : m_width(width), m_height(height) {
    // 1. Background Layer (Layer 0) — Preenchida com papel branco por padrão
    m_backgroundLayer = std::make_unique<Layer>("Background", width, height, true);
    m_backgroundLayer->getTileGrid().clearAll({255, 255, 255, 255});

    // 2. Camada 1 inicial de desenho (Transparente)
    addLayer("Camada 1");
}

void LayerStack::resize(int width, int height) {
    m_width = width;
    m_height = height;

    if (m_backgroundLayer) {
        auto oldBg = std::move(m_backgroundLayer);
        m_backgroundLayer = std::make_unique<Layer>("Background", width, height, true);
        m_backgroundLayer->getTileGrid().clearAll({255, 255, 255, 255});
    }

    for (size_t i = 0; i < m_drawingLayers.size(); ++i) {
        std::string name = m_drawingLayers[i]->getName();
        double opacity = m_drawingLayers[i]->getOpacity();
        bool visible = m_drawingLayers[i]->isVisible();
        LayerBlendMode mode = m_drawingLayers[i]->getBlendMode();

        auto newLayer = std::make_unique<Layer>(name, width, height, false);
        newLayer->setOpacity(opacity);
        newLayer->setVisible(visible);
        newLayer->setBlendMode(mode);
        m_drawingLayers[i] = std::move(newLayer);
    }
}

void LayerStack::clearAllDrawingLayers() {
    for (auto& layer : m_drawingLayers) {
        if (layer) {
            layer->getTileGrid().clearAll({0, 0, 0, 0});
        }
    }
}

int LayerStack::addLayer(const std::string& name, int insertIndex) {
    std::string layerName = name;
    if (layerName.empty()) {
        layerName = "Camada " + std::to_string(m_drawingLayers.size() + 1);
    }

    auto layer = std::make_unique<Layer>(layerName, m_width, m_height, false);
    // As camadas de desenho nascem com transparência pura
    layer->getTileGrid().clearAll({0, 0, 0, 0});

    if (insertIndex >= 0 && insertIndex < static_cast<int>(m_drawingLayers.size())) {
        m_drawingLayers.insert(m_drawingLayers.begin() + insertIndex, std::move(layer));
        m_activeIndex = insertIndex;
    } else {
        m_drawingLayers.push_back(std::move(layer));
        m_activeIndex = static_cast<int>(m_drawingLayers.size() - 1);
    }
    return m_activeIndex;
}

int LayerStack::addGroup(const std::string& name, int insertIndex) {
    std::string groupName = name;
    if (groupName.empty()) {
        groupName = "Grupo " + std::to_string(m_drawingLayers.size() + 1);
    }

    // Cria camada com LayerNodeType::Group para que isGroup() retorne true corretamente
    auto layer = std::make_unique<Layer>(groupName, LayerNodeType::Group, m_width, m_height, false);
    layer->getTileGrid().clearAll({0, 0, 0, 0});
    layer->setBlendMode(LayerBlendMode::PassThrough);

    if (insertIndex >= 0 && insertIndex < static_cast<int>(m_drawingLayers.size())) {
        m_drawingLayers.insert(m_drawingLayers.begin() + insertIndex, std::move(layer));
        m_activeIndex = insertIndex;
    } else {
        m_drawingLayers.push_back(std::move(layer));
        m_activeIndex = static_cast<int>(m_drawingLayers.size() - 1);
    }
    return m_activeIndex;
}

int LayerStack::addFilterLayer(const std::string& name, FilterType type, int insertIndex) {
    std::string layerName = name;
    if (layerName.empty()) {
        layerName = "Filtro " + std::to_string(m_drawingLayers.size() + 1);
    }

    auto filterLayer = std::make_unique<FilterLayer>(layerName, type, m_width, m_height);
    if (insertIndex >= 0 && insertIndex < static_cast<int>(m_drawingLayers.size())) {
        m_drawingLayers.insert(m_drawingLayers.begin() + insertIndex, std::move(filterLayer));
        m_activeIndex = insertIndex;
    } else {
        m_drawingLayers.push_back(std::move(filterLayer));
        m_activeIndex = static_cast<int>(m_drawingLayers.size() - 1);
    }
    return m_activeIndex;
}

bool LayerStack::isGroup(int index) const {
    if (index < 0 || index >= static_cast<int>(m_drawingLayers.size())) return false;
    return m_drawingLayers[index] && m_drawingLayers[index]->isGroup();
}

bool LayerStack::setGroupPassThrough(int index, bool passThrough) {
    if (index < 0 || index >= static_cast<int>(m_drawingLayers.size())) return false;
    if (!m_drawingLayers[index]) return false;
    m_drawingLayers[index]->setBlendMode(
        passThrough ? LayerBlendMode::PassThrough : LayerBlendMode::Normal
    );
    return true;
}

bool LayerStack::removeLayer(int index) {
    if (index < 0 || index >= static_cast<int>(m_drawingLayers.size())) return false;
    if (m_drawingLayers.size() <= 1) return false; // Não permite deletar a única camada de desenho

    m_drawingLayers.erase(m_drawingLayers.begin() + index);

    // Ajusta o índice ativo
    if (m_activeIndex >= static_cast<int>(m_drawingLayers.size())) {
        m_activeIndex = static_cast<int>(m_drawingLayers.size()) - 1;
    }
    return true;
}

int LayerStack::duplicateLayer(int index) {
    if (index < 0 || index >= static_cast<int>(m_drawingLayers.size())) return -1;

    const auto& src = m_drawingLayers[index];
    if (!src) return -1;

    std::string dupName = src->getName() + " Copiar";
    // Preserva o LayerNodeType original (DrawingLayer ou Group)
    auto dup = std::make_unique<Layer>(dupName, src->getType(), m_width, m_height, src->isBackground());
    dup->setOpacity(src->getOpacity());
    dup->setVisible(src->isVisible());
    dup->setLocked(src->isLocked());
    dup->setAlphaLocked(src->isAlphaLocked());
    dup->setClippingMask(src->isClippingMask());
    dup->setBlendMode(src->getBlendMode());
    dup->getTileGrid().copyFrom(src->getTileGrid());

    int insertIdx = index + 1;
    m_drawingLayers.insert(m_drawingLayers.begin() + insertIdx, std::move(dup));
    m_activeIndex = insertIdx;
    return m_activeIndex;
}

bool LayerStack::selectLayer(int index) {
    if (index < 0 || index >= static_cast<int>(m_drawingLayers.size())) return false;
    m_activeIndex = index;
    return true;
}

bool LayerStack::reorderLayer(int fromIndex, int toIndex) {
    const int count = static_cast<int>(m_drawingLayers.size());
    if (fromIndex < 0 || fromIndex >= count || toIndex < 0 || toIndex >= count) return false;
    if (fromIndex == toIndex) return true;

    auto layer = std::move(m_drawingLayers[fromIndex]);
    m_drawingLayers.erase(m_drawingLayers.begin() + fromIndex);
    m_drawingLayers.insert(m_drawingLayers.begin() + toIndex, std::move(layer));

    if (m_activeIndex == fromIndex) {
        m_activeIndex = toIndex;
    }
    return true;
}

bool LayerStack::reorderLayers(const std::vector<int>& newOrder) {
    if (newOrder.size() != m_drawingLayers.size()) return false;
    std::vector<std::unique_ptr<Layer>> reordered;
    reordered.reserve(m_drawingLayers.size());

    for (int idx : newOrder) {
        if (idx < 0 || idx >= static_cast<int>(m_drawingLayers.size())) return false;
        if (!m_drawingLayers[idx]) return false;
        reordered.push_back(std::move(m_drawingLayers[idx]));
    }

    m_drawingLayers = std::move(reordered);
    return true;
}

static bool wouldCreateCycle(const LayerNode* child, const LayerNode* newParent) noexcept {
    if (!child || !newParent) return false;
    if (child == newParent) return true;
    const LayerNode* curr = newParent;
    int depth = 0;
    while (curr && depth < 64) {
        if (curr == child) return true;
        curr = curr->getParent();
        ++depth;
    }
    return false;
}

bool LayerStack::setLayerParents(const std::vector<int>& parentIndices) {
    if (parentIndices.size() != m_drawingLayers.size()) return false;
    for (size_t i = 0; i < m_drawingLayers.size(); ++i) {
        if (!m_drawingLayers[i]) continue;
        int parentIdx = parentIndices[i];
        if (parentIdx >= 0 && parentIdx < static_cast<int>(m_drawingLayers.size()) && parentIdx != static_cast<int>(i)) {
            LayerNode* newParent = m_drawingLayers[parentIdx].get();
            if (!wouldCreateCycle(m_drawingLayers[i].get(), newParent)) {
                m_drawingLayers[i]->setParent(newParent);
            } else {
                m_drawingLayers[i]->setParent(nullptr); // Previne ciclo de nós
            }
        } else {
            m_drawingLayers[i]->setParent(nullptr);
        }
    }
    return true;
}

bool LayerStack::flattenGroup(int index) {
    const int count = static_cast<int>(m_drawingLayers.size());
    if (index < 0 || index >= count) return false;
    if (!m_drawingLayers[index] || !m_drawingLayers[index]->isGroup()) return false;

    const Layer* groupNode = m_drawingLayers[index].get();
    std::string groupName = groupNode->getName();
    double groupOpacity = groupNode->getOpacity();
    bool groupVis = groupNode->isVisible();
    LayerBlendMode groupBlend = groupNode->getBlendMode();
    const LayerNode* groupParent = groupNode->getParent();

    std::vector<int> descendantIndices;
    for (int i = 0; i < count; ++i) {
        if (i == index || !m_drawingLayers[i]) continue;
        const LayerNode* curr = m_drawingLayers[i]->getParent();
        while (curr) {
            if (curr == groupNode) {
                descendantIndices.push_back(i);
                break;
            }
            curr = curr->getParent();
        }
    }

    auto flattened = std::make_unique<Layer>(groupName, m_width, m_height, false);
    flattened->setOpacity(groupOpacity);
    flattened->setVisible(groupVis);
    flattened->setBlendMode(groupBlend == LayerBlendMode::PassThrough ? LayerBlendMode::Normal : groupBlend);

    for (int dIdx : descendantIndices) {
        Layer* dLayer = m_drawingLayers[dIdx].get();
        if (!dLayer || dLayer->isGroup() || !dLayer->isVisible()) continue;

        double relOpacity = dLayer->getOpacity();
        const LayerNode* curr = dLayer->getParent();
        while (curr && curr != groupNode) {
            if (!curr->isVisible()) { relOpacity = 0.0; break; }
            relOpacity *= curr->getOpacity();
            curr = curr->getParent();
        }
        if (relOpacity <= 0.0) continue;

        auto& srcGrid = dLayer->getTileGrid();
        auto& dstGrid = flattened->getTileGrid();
        const int tilesY = srcGrid.getTilesCountY();
        const int tilesX = srcGrid.getTilesCountX();

        for (int ty = 0; ty < tilesY; ++ty) {
            for (int tx = 0; tx < tilesX; ++tx) {
                canvas::Tile* sTile = srcGrid.getTile(tx, ty);
                if (!sTile) continue;
                canvas::Tile* dTile = dstGrid.getOrCreateTile(tx, ty);
                if (!dTile) continue;

                canvas::PixelBuffer& sBuf = sTile->getBuffer();
                canvas::PixelBuffer& dBuf = dTile->getBuffer();

                for (int py = 0; py < canvas::Tile::TILE_SIZE; ++py) {
                    for (int px = 0; px < canvas::Tile::TILE_SIZE; ++px) {
                        raster::ColorRGBA src = sBuf.getPixel(px, py);
                        if (src.a == 0) continue;

                        const double srcA = (static_cast<double>(src.a) / 255.0) * relOpacity;
                        if (srcA <= 0.0) continue;

                        raster::ColorRGBA dst = dBuf.getPixel(px, py);
                        const double dstA = static_cast<double>(dst.a) / 255.0;
                        const double outA = srcA + dstA * (1.0 - srcA);
                        if (outA <= 0.0) continue;

                        const double srcR = static_cast<double>(src.r);
                        const double srcG = static_cast<double>(src.g);
                        const double srcB = static_cast<double>(src.b);

                        const double dstR = static_cast<double>(dst.r);
                        const double dstG = static_cast<double>(dst.g);
                        const double dstB = static_cast<double>(dst.b);

                        const double outR = (srcR * srcA + dstR * dstA * (1.0 - srcA)) / outA;
                        const double outG = (srcG * srcA + dstG * dstA * (1.0 - srcA)) / outA;
                        const double outB = (srcB * srcA + dstB * dstA * (1.0 - srcA)) / outA;

                        dBuf.setPixel(px, py, {
                            static_cast<uint8_t>(std::clamp(outR, 0.0, 255.0)),
                            static_cast<uint8_t>(std::clamp(outG, 0.0, 255.0)),
                            static_cast<uint8_t>(std::clamp(outB, 0.0, 255.0)),
                            static_cast<uint8_t>(std::clamp(outA * 255.0, 0.0, 255.0))
                        });
                    }
                }
            }
        }
    }

    std::vector<std::unique_ptr<Layer>> newLayers;
    newLayers.reserve(m_drawingLayers.size());

    for (int i = 0; i < count; ++i) {
        if (i == index) {
            newLayers.push_back(std::move(flattened));
        } else if (std::find(descendantIndices.begin(), descendantIndices.end(), i) != descendantIndices.end()) {
            continue;
        } else {
            newLayers.push_back(std::move(m_drawingLayers[i]));
        }
    }

    m_drawingLayers = std::move(newLayers);
    m_activeIndex = std::min(index, static_cast<int>(m_drawingLayers.size()) - 1);

    // Reassocia ponteiros de pais
    for (auto& l : m_drawingLayers) {
        if (l && l->getParent() == groupNode) {
            l->setParent(const_cast<LayerNode*>(groupParent));
        }
    }
    return true;
}

bool LayerStack::mergeLayerDown(int index) {
    const int count = static_cast<int>(m_drawingLayers.size());
    if (index <= 0 || index >= count) return false;

    if (m_drawingLayers[index] && m_drawingLayers[index]->isGroup()) {
        flattenGroup(index);
    }
    if (index - 1 >= 0 && index - 1 < static_cast<int>(m_drawingLayers.size()) &&
        m_drawingLayers[index - 1] && m_drawingLayers[index - 1]->isGroup()) {
        flattenGroup(index - 1);
    }

    Layer* upperLayer = m_drawingLayers[index].get();
    Layer* lowerLayer = m_drawingLayers[index - 1].get();
    if (!upperLayer || !lowerLayer) return false;

    // Se a camada superior for uma FilterLayer, rasteriza o filtro sobre os tiles da camada inferior
    if (upperLayer->isFilter()) {
        const auto* filterLayer = dynamic_cast<const FilterLayer*>(upperLayer);
        if (filterLayer) {
            auto& lowerGrid = lowerLayer->getTileGrid();
            lowerGrid.forEachTile([&](const auto& /*idx*/, canvas::Tile& tile) {
                Compositor::applyFilterToBuffer(*filterLayer, tile.getBuffer());
                tile.setDirty(true);
            });
        }
        m_drawingLayers.erase(m_drawingLayers.begin() + index);
        m_activeIndex = index - 1;
        return true;
    }

    const double upperOpacity = upperLayer->getOpacity();

    auto& upperGrid = upperLayer->getTileGrid();
    auto& lowerGrid = lowerLayer->getTileGrid();

    const int tilesY = upperGrid.getTilesCountY();
    const int tilesX = upperGrid.getTilesCountX();

    const LayerBlendMode upperBlend = upperLayer->getBlendMode();
    const bool upperIsClipping = upperLayer->isClippingMask();

    for (int ty = 0; ty < tilesY; ++ty) {
        for (int tx = 0; tx < tilesX; ++tx) {
            canvas::Tile* uTile = upperGrid.getTile(tx, ty);
            if (!uTile) continue;

            // Se for clipping mask, só opera onde a camada base já tem tile
            canvas::Tile* lTile = upperIsClipping ? lowerGrid.getTile(tx, ty) : lowerGrid.getOrCreateTile(tx, ty);
            if (!lTile) continue;

            canvas::PixelBuffer& uBuf = uTile->getBuffer();
            canvas::PixelBuffer& lBuf = lTile->getBuffer();

            for (int py = 0; py < canvas::Tile::TILE_SIZE; ++py) {
                for (int px = 0; px < canvas::Tile::TILE_SIZE; ++px) {
                    raster::ColorRGBA src = uBuf.getPixel(px, py);
                    if (src.a == 0) continue;

                    raster::ColorRGBA dst = lBuf.getPixel(px, py);
                    // Não mescla fora da silhueta da camada base
                    if (upperIsClipping && dst.a == 0) continue;

                    raster::ColorRGBA blended = Compositor::blendPixel(src, upperOpacity, dst, upperBlend);
                    lBuf.setPixel(px, py, blended);
                }
            }
        }
    }

    m_drawingLayers.erase(m_drawingLayers.begin() + index);
    m_activeIndex = index - 1;
    return true;
}

Layer* LayerStack::getActiveLayer() noexcept {
    if (m_activeIndex >= 0 && m_activeIndex < static_cast<int>(m_drawingLayers.size())) {
        return m_drawingLayers[m_activeIndex].get();
    }
    return nullptr;
}

const Layer* LayerStack::getActiveLayer() const noexcept {
    if (m_activeIndex >= 0 && m_activeIndex < static_cast<int>(m_drawingLayers.size())) {
        return m_drawingLayers[m_activeIndex].get();
    }
    return nullptr;
}

Layer* LayerStack::getDrawingLayer(int index) noexcept {
    if (index >= 0 && index < static_cast<int>(m_drawingLayers.size())) {
        return m_drawingLayers[index].get();
    }
    return nullptr;
}

const Layer* LayerStack::getDrawingLayer(int index) const noexcept {
    if (index >= 0 && index < static_cast<int>(m_drawingLayers.size())) {
        return m_drawingLayers[index].get();
    }
    return nullptr;
}

std::vector<const Layer*> LayerStack::getAllLayersForComposition() const {
    std::vector<const Layer*> list;
    list.reserve(m_drawingLayers.size() + 1);

    if (m_backgroundLayer && m_backgroundLayer->isVisible()) {
        m_backgroundLayer->setEffectiveOpacity(m_backgroundLayer->getOpacity());
        list.push_back(m_backgroundLayer.get());
    }
    for (size_t i = 0; i < m_drawingLayers.size(); ++i) {
        const auto& layerPtr = m_drawingLayers[i];
        if (!layerPtr || layerPtr->isGroup()) continue;

        bool effVis = layerPtr->isVisible();
        double effOpacity = layerPtr->getOpacity();

        // Se for máscara de recorte, sua visibilidade depende da visibilidade da camada base
        if (layerPtr->isClippingMask()) {
            const Layer* base = getClipBaseLayer(static_cast<int>(i));
            if (!base || !base->isVisible()) {
                effVis = false;
            } else {
                const LayerNode* bCurr = base->getParent();
                while (bCurr) {
                    if (!bCurr->isVisible()) {
                        effVis = false;
                        break;
                    }
                    bCurr = bCurr->getParent();
                }
            }
        }

        const LayerNode* curr = layerPtr->getParent();
        while (curr) {
            if (!curr->isVisible()) {
                effVis = false;
                break;
            }
            effOpacity *= curr->getOpacity();
            curr = curr->getParent();
        }

        if (effVis && effOpacity > 0.0) {
            const_cast<Layer*>(layerPtr.get())->setEffectiveOpacity(effOpacity);
            list.push_back(layerPtr.get());
        }
    }
    return list;
}

const Layer* LayerStack::getClipBaseLayer(int drawingIndex) const {
    if (drawingIndex <= 0 || drawingIndex >= static_cast<int>(m_drawingLayers.size())) {
        return nullptr;
    }
    for (int i = drawingIndex - 1; i >= 0; --i) {
        const auto& l = m_drawingLayers[i];
        if (!l) continue;
        if (l->isClippingMask()) continue; // Pula outras camadas recortadas na cadeia
        if (l->isFilter()) continue;       // Filtro não possui pixels raster
        if (l->isGroup()) continue;        // Grupo não possui tiles diretos
        return l.get();
    }
    return nullptr;
}

} // namespace aladyn::engine::document
