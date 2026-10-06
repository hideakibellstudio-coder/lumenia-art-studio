#include "RegionBuffer.hpp"
#include <algorithm>
#include <cstring>

namespace aladyn::engine::document::internal {

namespace {

template <typename Pixel>
void fillRows(canvas::PixelBuffer& buffer, const RegionBounds& bounds, Pixel color, int parallelRowThreshold) {
    Pixel* data = buffer.pixels<Pixel>();
    const size_t stride = static_cast<size_t>(buffer.getWidth());
    const size_t count = static_cast<size_t>(bounds.maxX - bounds.minX + 1);
    #pragma omp parallel for schedule(static) if((bounds.maxY - bounds.minY) > parallelRowThreshold)
    for (int y = bounds.minY; y <= bounds.maxY; ++y) {
        std::fill_n(data + (static_cast<size_t>(y) * stride + bounds.minX), count, color);
    }
}

} // namespace

void fillBackground(
    canvas::PixelBuffer& buffer,
    const RegionBounds& bounds,
    const utils::ColorRGBA& bgFill,
    int canvasWidth,
    int canvasHeight,
    int parallelRowThreshold
) {
    const bool covers = bounds.minX == 0 && bounds.maxX == canvasWidth - 1 && bounds.minY == 0 && bounds.maxY == canvasHeight - 1;
    const bool transparent = bgFill.r == 0 && bgFill.g == 0 && bgFill.b == 0 && bgFill.a == 0;
    if (covers && transparent) {
        std::memset(buffer.getData(), 0, static_cast<size_t>(canvasWidth) * canvasHeight * buffer.getBytesPerPixel());
        return;
    }
    if (buffer.getFormat() == canvas::PixelFormat::RGBA16) {
        fillRows<utils::ColorRGBA16>(buffer, bounds, canvas::widen(bgFill), parallelRowThreshold);
        return;
    }
    // O 8 bits segue preenchendo com a palavra de 32 bits, como sempre.
    const uint32_t bg32 = (static_cast<uint32_t>(bgFill.a) << 24) | (static_cast<uint32_t>(bgFill.b) << 16) |
                          (static_cast<uint32_t>(bgFill.g) << 8) | static_cast<uint32_t>(bgFill.r);
    uint32_t* outData32 = reinterpret_cast<uint32_t*>(buffer.getData());
    const int outStride = buffer.getWidth();
    #pragma omp parallel for schedule(static) if((bounds.maxY - bounds.minY) > parallelRowThreshold)
    for (int y = bounds.minY; y <= bounds.maxY; ++y) {
        std::fill_n(outData32 + (static_cast<size_t>(y) * outStride + bounds.minX), bounds.maxX - bounds.minX + 1, bg32);
    }
}

// Os trechos (linha, de x0 a x1) de `outer` que ficam fora de `inner`: as linhas acima e abaixo inteiras e,
// nas linhas de `inner`, a faixa da esquerda e a da direita.
template <typename Visit>
void RegionMargin::forEachSegment(Visit&& visit) const {
    for (int y = m_outer.minY; y <= m_outer.maxY; ++y) {
        if (y < m_inner.minY || y > m_inner.maxY) {
            visit(y, m_outer.minX, m_outer.maxX);
            continue;
        }
        if (m_inner.minX > m_outer.minX) visit(y, m_outer.minX, m_inner.minX - 1);
        if (m_inner.maxX < m_outer.maxX) visit(y, m_inner.maxX + 1, m_outer.maxX);
    }
}

RegionMargin::RegionMargin(canvas::PixelBuffer& buffer, const RegionBounds& outer, const RegionBounds& inner)
    : m_buffer(buffer), m_outer(outer), m_inner(inner) {
    const uint8_t* data = m_buffer.getData();
    const size_t pixelBytes = m_buffer.getBytesPerPixel();
    const size_t stride = static_cast<size_t>(m_buffer.getWidth());
    forEachSegment([&](int y, int x0, int x1) {
        const uint8_t* row = data + (static_cast<size_t>(y) * stride + x0) * pixelBytes;
        m_saved.insert(m_saved.end(), row, row + static_cast<size_t>(x1 - x0 + 1) * pixelBytes);
    });
}

void RegionMargin::restore() {
    uint8_t* data = m_buffer.getData();
    const size_t pixelBytes = m_buffer.getBytesPerPixel();
    const size_t stride = static_cast<size_t>(m_buffer.getWidth());
    size_t at = 0;
    forEachSegment([&](int y, int x0, int x1) {
        const size_t bytes = static_cast<size_t>(x1 - x0 + 1) * pixelBytes;
        std::memcpy(data + (static_cast<size_t>(y) * stride + x0) * pixelBytes, m_saved.data() + at, bytes);
        at += bytes;
    });
}

void narrowRegion(const canvas::PixelBuffer& wide, canvas::PixelBuffer& narrowed, const RegionBounds& region) {
    const utils::ColorRGBA16* source = wide.pixels<utils::ColorRGBA16>();
    utils::ColorRGBA* target = narrowed.pixels<utils::ColorRGBA>();
    const size_t sourceStride = static_cast<size_t>(wide.getWidth());
    const size_t targetStride = static_cast<size_t>(narrowed.getWidth());
    #pragma omp parallel for schedule(static) if((region.maxY - region.minY) > 64)
    for (int y = region.minY; y <= region.maxY; ++y) {
        const utils::ColorRGBA16* in = source + static_cast<size_t>(y) * sourceStride;
        utils::ColorRGBA* out = target + static_cast<size_t>(y) * targetStride;
        for (int x = region.minX; x <= region.maxX; ++x) out[x] = canvas::narrow(in[x]);
    }
}

} // namespace aladyn::engine::document::internal
