#include "DecodedLayer.hpp"
#include "../../core/canvas/CanvasLimits.hpp"
#include "../../core/canvas/TileGridCodec.hpp"
#include <stdexcept>
#include <utility>

namespace aladyn::engine::boundary {

// O formato de pixel é o que o bloco declara; quem adota o bloco confere que é o do documento.
DecodedLayer::DecodedLayer(int width, int height, const uint8_t* data, size_t size)
    : DecodedLayer(width, height, data, size, canvas::TileGridCodec::peekFormat(data, size)) {}

DecodedLayer::DecodedLayer(int width, int height, const uint8_t* data, size_t size, canvas::PixelFormat format)
    : m_grid(canvas::checkedCanvasDimension(width, format), canvas::checkedCanvasDimension(height, format), format) {
    canvas::TileGridCodec::decode(data, size, m_grid);
}

canvas::TileGrid DecodedLayer::take() {
    if (m_taken) throw std::logic_error("decoded layer was already adopted");
    m_taken = true;
    return std::move(m_grid);
}

} // namespace aladyn::engine::boundary
