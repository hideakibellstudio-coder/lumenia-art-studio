#include "PaintEngineFacade.hpp"
#include "DecodedLayer.hpp"
#include "LayerSnapshot.hpp"
#include "../orchestrator/DocumentContext.hpp"
#include "../../core/canvas/TileGridCodec.hpp"
#include <memory>
#include <stdexcept>

// ─────────────────────────────────────────────────────────────────────────────
// PaintEngineFacade — persistencia (S1.2).
//
// O instantaneo que a gravacao em segundo plano le, a restauracao de uma camada a
// partir do bloco de tiles, e a composicao em lote que abrir um arquivo usa. Separado
// de PaintEngineFacade.cpp (403 linhas) pela responsabilidade, nao pelo tamanho.
// ─────────────────────────────────────────────────────────────────────────────

namespace aladyn::engine::boundary {

std::shared_ptr<LayerSnapshot> PaintEngineFacade::snapshotLayers() const {
    return std::make_shared<LayerSnapshot>(m_layerStack, m_width, m_height);
}

void PaintEngineFacade::restoreLayerTiles(int layerIndex, const uint8_t* data, size_t size) {
    document::Layer* layer = m_layerStack.getDrawingLayer(layerIndex);
    if (!layer || layer->isGroup() || layer->isFilter()) {
        throw std::invalid_argument("layer has no pixels to restore");
    }
    canvas::TileGridCodec::decode(data, size, layer->getTileGrid());
    const auto ctx = docContext();
    ctx.compositeAll();
    ctx.touch();
}

void PaintEngineFacade::adoptDecodedLayer(int layerIndex, DecodedLayer& decoded) {
    document::Layer* layer = m_layerStack.getDrawingLayer(layerIndex);
    if (!layer || layer->isGroup() || layer->isFilter()) {
        throw std::invalid_argument("layer has no pixels to restore");
    }
    if (decoded.width() != m_width || decoded.height() != m_height) {
        throw std::invalid_argument("decoded layer has another canvas size");
    }
    if (decoded.pixelFormat() != layer->getTileGrid().getFormat()) {
        throw std::invalid_argument("decoded layer has another pixel format");
    }
    layer->getTileGrid() = decoded.take();
    const auto ctx = docContext();
    ctx.compositeAll();
    ctx.touch();
}

void PaintEngineFacade::endBatch() {
    if (m_batchDepth == 0) throw std::logic_error("endBatch without beginBatch");
    // Nada a compor no fim: dentro do lote as operações só marcaram tiles velhos, e quem lê recompõe o que lê.
    --m_batchDepth;
}

} // namespace aladyn::engine::boundary
