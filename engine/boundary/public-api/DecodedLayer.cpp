#include "DecodedLayer.hpp"
#include "../../core/canvas/CanvasLimits.hpp"
#include "../../core/canvas/TileGridCodec.hpp"
#include <stdexcept>
#include <utility>

namespace aladyn::engine::boundary {

DecodedLayer::DecodedLayer(int width, int height, const uint8_t* data, size_t size)
    : m_grid(canvas::checkedCanvasDimension(width), canvas::checkedCanvasDimension(height)) {
    canvas::TileGridCodec::decode(data, size, m_grid);
}

canvas::TileGrid DecodedLayer::take() {
    if (m_taken) throw std::logic_error("decoded layer was already adopted");
    m_taken = true;
    return std::move(m_grid);
}

} // namespace aladyn::engine::boundary
