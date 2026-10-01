#include "LayerSnapshot.hpp"
#include "../../core/canvas/TileGridCodec.hpp"
#include "../../core/document/Layer.hpp"
#include <stdexcept>

namespace aladyn::engine::boundary {

LayerSnapshot::LayerSnapshot(const document::LayerStack& stack, int width, int height)
    : m_width(width), m_height(height) {
    const int count = static_cast<int>(stack.getDrawingLayerCount());
    m_grids.reserve(static_cast<size_t>(count));
    for (int i = 0; i < count; ++i) {
        const document::Layer* layer = stack.getDrawingLayer(i);
        if (!layer || layer->isGroup() || layer->isFilter()) {
            m_grids.push_back(nullptr);
            continue;
        }
        auto grid = std::make_unique<canvas::TileGrid>(width, height);
        grid->copyFrom(layer->getTileGrid());
        m_grids.push_back(std::move(grid));
    }
}

std::vector<uint8_t> LayerSnapshot::encodeLayer(int index) const {
    if (!hasPixels(index)) throw std::invalid_argument("layer has no pixels to encode");
    return canvas::TileGridCodec::encode(*m_grids[static_cast<size_t>(index)]);
}

} // namespace aladyn::engine::boundary
