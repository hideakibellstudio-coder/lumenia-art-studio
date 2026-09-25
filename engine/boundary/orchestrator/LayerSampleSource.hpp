#ifndef ALADYN_ENGINE_LAYER_SAMPLE_SOURCE_HPP
#define ALADYN_ENGINE_LAYER_SAMPLE_SOURCE_HPP

#include "../../core/canvas/PixelBuffer.hpp"
#include "../../core/document/LayerStack.hpp"
#include <memory>

namespace aladyn::engine::boundary::orchestrator {

// De onde o balde e a varinha leem as cores que decidem a região: a composição
// de todas as camadas visíveis ou só a camada ativa (opção "Todas as Camadas"
// das duas ferramentas). Até 2026-09-25 só a varinha respeitava a opção; o
// balde lia sempre a composição e desmarcar a caixa não mudava nada.
class LayerSampleSource {
public:
    // `composite` quando `allLayers`; senão a camada ativa copiada para
    // `storage` (mesmo tamanho da composição, transparente onde não há tile).
    // nullptr se não há camada ativa.
    static const canvas::PixelBuffer* select(
        bool allLayers,
        const canvas::PixelBuffer& composite,
        const document::LayerStack& layerStack,
        std::unique_ptr<canvas::PixelBuffer>& storage
    ) {
        if (allLayers) return &composite;
        const document::Layer* activeLayer = layerStack.getActiveLayer();
        if (!activeLayer) return nullptr;

        const int width = composite.getWidth();
        const int height = composite.getHeight();
        storage = std::make_unique<canvas::PixelBuffer>(width, height, utils::ColorRGBA{0, 0, 0, 0});
        // Leitura pelo acesso const: descomprime se preciso sem forçar a cópia
        // de um tile compartilhado (COW).
        activeLayer->getTileGrid().forEachTile([&](const canvas::TileIndex&, const canvas::Tile& tile) {
            const int px0 = tile.getPixelX();
            const int py0 = tile.getPixelY();
            const canvas::PixelBuffer& pixels = tile.getBuffer();
            for (int py = 0; py < canvas::Tile::TILE_SIZE && py0 + py < height; ++py) {
                for (int px = 0; px < canvas::Tile::TILE_SIZE && px0 + px < width; ++px) {
                    storage->setPixel(px0 + px, py0 + py, pixels.getPixel(px, py));
                }
            }
        });
        return storage.get();
    }
};

} // namespace aladyn::engine::boundary::orchestrator

#endif
