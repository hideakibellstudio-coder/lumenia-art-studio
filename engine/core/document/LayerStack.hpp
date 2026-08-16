#ifndef ALADYN_ENGINE_LAYER_STACK_HPP
#define ALADYN_ENGINE_LAYER_STACK_HPP

#include "Layer.hpp"
#include "FilterLayer.hpp"
#include "../canvas/PixelBuffer.hpp"
#include <vector>
#include <memory>
#include <string>

namespace aladyn::engine::document {

// ─── GERENCIADOR DA PILHA DE CAMADAS (LayerStack) ───────────────────────────
//
// Estrutura:
//   - Layer 0 (Background Layer): Fundo isolado contendo a cor/textura do papel.
//   - Layers 1..N (Drawing Layers): Pilha de camadas de desenho com transparência pura.
//
// Responsabilidade:
//   Gerenciar adição, remoção, reordenação, seleção e snapshots de amostragem
//   para motores como Blur e Smudge (isolados do fundo branco do papel).
// ───────────────────────────────────────────────────────────────────────────
class LayerStack {
public:
    LayerStack(int width, int height);

    void resize(int width, int height);
    void clearAllDrawingLayers();

    // ─── GERENCIAMENTO DE CAMADAS ───────────────────────────────────────────
    int addLayer(const std::string& name = "");
    int addGroup(const std::string& name = "Novo Grupo");
    int addFilterLayer(const std::string& name, FilterType type);
    bool isGroup(int index) const;
    bool setGroupPassThrough(int index, bool passThrough);
    bool removeLayer(int index);
    int duplicateLayer(int index);
    bool selectLayer(int index);
    bool reorderLayer(int fromIndex, int toIndex);
    bool reorderLayers(const std::vector<int>& newOrder);
    bool setLayerParents(const std::vector<int>& parentIndices);
    bool flattenGroup(int index);
    bool mergeLayerDown(int index);

    [[nodiscard]] int getActiveIndex() const noexcept { return m_activeIndex; }
    [[nodiscard]] size_t getDrawingLayerCount() const noexcept { return m_drawingLayers.size(); }

    [[nodiscard]] Layer* getActiveLayer() noexcept;
    [[nodiscard]] const Layer* getActiveLayer() const noexcept;

    [[nodiscard]] Layer* getDrawingLayer(int index) noexcept;
    [[nodiscard]] const Layer* getDrawingLayer(int index) const noexcept;
    [[nodiscard]] const Layer* getClipBaseLayer(int drawingIndex) const;

    [[nodiscard]] Layer& getBackgroundLayer() noexcept { return *m_backgroundLayer; }
    [[nodiscard]] const Layer& getBackgroundLayer() const noexcept { return *m_backgroundLayer; }

    [[nodiscard]] int getWidth() const noexcept { return m_width; }
    [[nodiscard]] int getHeight() const noexcept { return m_height; }

    // Retorna todos os ponteiros de camadas na ordem de composição (Background + Drawing Layers)
    [[nodiscard]] std::vector<const Layer*> getAllLayersForComposition() const;

private:
    int m_width;
    int m_height;
    int m_activeIndex{0};

    std::unique_ptr<Layer> m_backgroundLayer;
    std::vector<std::unique_ptr<Layer>> m_drawingLayers;
};

} // namespace aladyn::engine::document

#endif // ALADYN_ENGINE_LAYER_STACK_HPP
