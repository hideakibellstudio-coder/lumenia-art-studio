#ifndef ALADYN_ENGINE_MEMORY_ORCHESTRATOR_HPP
#define ALADYN_ENGINE_MEMORY_ORCHESTRATOR_HPP

#include "../../../core/document/LayerStack.hpp"
#include <cstddef>

namespace aladyn::engine::boundary::internal {

/**
 * @brief Orquestrador atômico de escalabilidade de memória e gerenciamento de tiles.
 */
class MemoryOrchestrator {
public:
    static size_t compressInactiveLayers(document::LayerStack& stack) {
        size_t totalCompressed = 0;
        const int activeIdx = stack.getActiveIndex();
        const int count = static_cast<int>(stack.getDrawingLayerCount());
        for (int i = 0; i < count; ++i) {
            if (i != activeIdx) {
                if (auto* layer = stack.getDrawingLayer(i)) {
                    totalCompressed += layer->compressInactiveTiles();
                }
            }
        }
        return totalCompressed;
    }

    static size_t decompressAllLayers(document::LayerStack& stack) {
        size_t totalDecompressed = 0;
        const int count = static_cast<int>(stack.getDrawingLayerCount());
        for (int i = 0; i < count; ++i) {
            if (auto* layer = stack.getDrawingLayer(i)) {
                totalDecompressed += layer->decompressAllTiles();
            }
        }
        return totalDecompressed;
    }

    static double getTotalTileMemoryMB(const document::LayerStack& stack) {
        size_t totalBytes = 0;
        const int count = static_cast<int>(stack.getDrawingLayerCount());
        for (int i = 0; i < count; ++i) {
            if (const auto* layer = stack.getDrawingLayer(i)) {
                totalBytes += layer->getMemoryFootprintBytes();
            }
        }
        return static_cast<double>(totalBytes) / (1024.0 * 1024.0);
    }

    static size_t getCowSharedTilesCount(const document::LayerStack& stack) {
        size_t total = 0;
        const int count = static_cast<int>(stack.getDrawingLayerCount());
        for (int i = 0; i < count; ++i) {
            if (const auto* layer = stack.getDrawingLayer(i)) {
                total += layer->getTileGrid().getCowSharedTilesCount();
            }
        }
        return total;
    }
};

} // namespace aladyn::engine::boundary::internal

#endif // ALADYN_ENGINE_MEMORY_ORCHESTRATOR_HPP
