#include "LayerStack.hpp"
#include "Compositor.hpp"
#include "LayerMerger.hpp"
#include <algorithm>

namespace aladyn::engine::document {

static std::unique_ptr<Layer> cloneLayer(const Layer& source, int w, int h) {
    std::unique_ptr<Layer> result;
    if (const auto* filter = dynamic_cast<const FilterLayer*>(&source)) {
        auto copy = std::make_unique<FilterLayer>(source.getName(), filter->getFilterType(), w, h);
        copy->setParams(filter->getParams());
        result = std::move(copy);
    } else {
        result = std::make_unique<Layer>(source.getName(), source.getType(), w, h, source.isBackground());
    }
    result->setOpacity(source.getOpacity());
    result->setDocumentUid(source.getDocumentUid());
    result->setVisible(source.isVisible());
    result->setLocked(source.isLocked());
    result->setAlphaLocked(source.isAlphaLocked());
    result->setClippingMask(source.isClippingMask());
    result->setBlendMode(source.getBlendMode());
    result->setEffectiveOpacity(source.getEffectiveOpacity());
    result->getTileGrid().copyFrom(source.getTileGrid());
    return result;
}

LayerStack::LayerStack(const LayerStack& other)
    : m_width(other.m_width), m_height(other.m_height), m_activeIndex(other.m_activeIndex),
      m_backgroundLayer(cloneLayer(*other.m_backgroundLayer, m_width, m_height)) {
    for (const auto& layer : other.m_drawingLayers)
        m_drawingLayers.push_back(cloneLayer(*layer, m_width, m_height));
    for (size_t i = 0; i < m_drawingLayers.size(); ++i) {
        const auto* parent = other.m_drawingLayers[i]->getParent();
        for (size_t j = 0; parent && j < m_drawingLayers.size(); ++j)
            if (parent == other.m_drawingLayers[j].get())
                m_drawingLayers[i]->setParent(m_drawingLayers[j].get());
    }
}

void LayerStack::restore(const LayerStack& other) {
    LayerStack prepared(other); // Allocate everything before changing the live stack.
    swap(prepared);
}

void LayerStack::swap(LayerStack& prepared) noexcept {
    std::swap(m_width, prepared.m_width);
    std::swap(m_height, prepared.m_height);
    std::swap(m_activeIndex, prepared.m_activeIndex);
    m_backgroundLayer.swap(prepared.m_backgroundLayer);
    m_drawingLayers.swap(prepared.m_drawingLayers);
}

size_t LayerStack::snapshotBytes() const noexcept {
    size_t bytes = sizeof(LayerStack) + m_backgroundLayer->getMemoryFootprintBytes();
    for (const auto& layer : m_drawingLayers)
        bytes += sizeof(Layer) + layer->getName().capacity() + layer->getMemoryFootprintBytes();
    return bytes;
}

LayerStack::LayerStack(int width, int height)
    : m_width(width), m_height(height) {
    // 1. Background Layer (Layer 0) — Preenchida com papel branco por padrão
    m_backgroundLayer = std::make_unique<Layer>("Background", width, height, true);
    m_backgroundLayer->getTileGrid().clearAll({255, 255, 255, 255});

    // 2. Camada 1 inicial de desenho (Transparente)
    addLayer("Camada 1");
}

void LayerStack::resize(int width, int height) {
    width = std::max(1, width);
    height = std::max(1, height);
    if (width == m_width && height == m_height) return;

    // Preserva conteúdo e metadados; antes esta rotina recriava cada Layer e
    // apagava todos os pixels, filtros, locks e relações de grupo.
    if (m_backgroundLayer) {
        m_backgroundLayer->getTileGrid().resizePreserve(width, height);
    }
    for (auto& layer : m_drawingLayers) {
        if (layer) layer->getTileGrid().resizePreserve(width, height);
    }
    m_width = width;
    m_height = height;
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

    const Layer* active = getActiveLayer();
    std::vector<const Layer*> removed{m_drawingLayers[index].get()};
    for (size_t i = 0; i < removed.size(); ++i)
        for (const auto& layer : m_drawingLayers)
            if (layer->getParent() == removed[i] && std::find(removed.begin(), removed.end(), layer.get()) == removed.end())
                removed.push_back(layer.get());
    if (removed.size() == m_drawingLayers.size()) return false;
    std::erase_if(m_drawingLayers, [&](const auto& layer) {
        return std::find(removed.begin(), removed.end(), layer.get()) != removed.end();
    });
    m_activeIndex = std::min(index, static_cast<int>(m_drawingLayers.size()) - 1);
    for (size_t i = 0; i < m_drawingLayers.size(); ++i)
        if (m_drawingLayers[i].get() == active) m_activeIndex = static_cast<int>(i);

    return true;
}

int LayerStack::duplicateLayer(int index) {
    if (index < 0 || index >= static_cast<int>(m_drawingLayers.size())) return -1;

    const auto& src = m_drawingLayers[index];
    if (!src) return -1;

    std::string dupName = src->getName() + " Copiar";
    auto dup = cloneLayer(*src, m_width, m_height);
    dup->setName(dupName);
    dup->setParent(src->getParent());

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
    if (m_activeIndex < 0 || m_activeIndex >= static_cast<int>(m_drawingLayers.size())) return false;
    std::vector<bool> seen(m_drawingLayers.size(), false);
    for (int idx : newOrder) {
        if (idx < 0 || idx >= static_cast<int>(seen.size()) || seen[idx]) return false;
        seen[idx] = true;
    }
    const Layer* activePtr = m_drawingLayers[m_activeIndex].get();
    std::vector<std::unique_ptr<Layer>> reordered;
    reordered.reserve(m_drawingLayers.size());

    for (int idx : newOrder) {
        if (idx < 0 || idx >= static_cast<int>(m_drawingLayers.size())) return false;
        if (!m_drawingLayers[idx]) return false;
        reordered.push_back(std::move(m_drawingLayers[idx]));
    }

    m_drawingLayers = std::move(reordered);
    for (size_t i = 0; i < m_drawingLayers.size(); ++i) {
        if (m_drawingLayers[i].get() == activePtr) {
            m_activeIndex = static_cast<int>(i);
            break;
        }
    }
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
    for (size_t i = 0; i < parentIndices.size(); ++i) {
        int p = parentIndices[i];
        size_t depth = 0;
        while (p != -1) {
            if (p < 0 || p >= static_cast<int>(parentIndices.size()) ||
                p == static_cast<int>(i) || !m_drawingLayers[p]->isGroup() ||
                ++depth > parentIndices.size()) return false;
            p = parentIndices[p];
        }
    }
    for (size_t i = 0; i < parentIndices.size(); ++i)
        m_drawingLayers[i]->setParent(parentIndices[i] < 0 ? nullptr : m_drawingLayers[parentIndices[i]].get());

    return true;
}

bool LayerStack::flattenGroup(int index, bool linearGamma, bool deepColor) {
    return LayerMerger::flattenGroup(m_drawingLayers, m_activeIndex, m_width, m_height, index, linearGamma, deepColor);
}

bool LayerStack::mergeLayerDown(int index, bool linearGamma, bool deepColor) {
    return LayerMerger::mergeLayerDown(m_drawingLayers, m_activeIndex, m_width, m_height, index, linearGamma, deepColor);
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
