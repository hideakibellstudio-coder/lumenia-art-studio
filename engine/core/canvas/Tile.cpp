#include "Tile.hpp"
#include "../../infrastructure/compression/Lz4Codec.hpp"
#include <algorithm>
#include <atomic>

namespace aladyn::engine::canvas {

Tile::Tile(int tileX, int tileY, PixelFormat format)
    : m_tileX(tileX), m_tileY(tileY), m_format(format),
      m_buffer(std::make_shared<PixelBuffer>(TILE_SIZE, TILE_SIZE, format, utils::ColorRGBA{0, 0, 0, 0})) {}

Tile::Tile(int tileX, int tileY, std::shared_ptr<PixelBuffer> sharedBuffer)
    : m_tileX(tileX), m_tileY(tileY), m_buffer(std::move(sharedBuffer)) {
    if (!m_buffer) {
        m_buffer = std::make_shared<PixelBuffer>(TILE_SIZE, TILE_SIZE, utils::ColorRGBA{0, 0, 0, 0});
    }
    m_format = m_buffer->getFormat();
}

PixelBuffer& Tile::getBuffer() noexcept {
    ensureDecompressed();
    ensureUnique();
    return *m_buffer;
}

const PixelBuffer& Tile::getBuffer() const noexcept {
    ensureDecompressed();
    return *m_buffer;
}

const PixelBuffer& Tile::view(PixelBuffer& scratch) const noexcept {
    if (!m_isCompressed) return *m_buffer;
    scratch.reformat(m_format);
    if (!m_compressedData.empty() && compression::Lz4Codec::decompressBlock(
            m_compressedData.data(), m_compressedData.size(), scratch.getData(), bytesFor(m_format))) {
        return scratch;
    }
    // Bloco corrompido: aparece transparente em vez de derrubar a composição.
    scratch.clearTransparent();
    return scratch;
}

void Tile::ensureDecompressed() const noexcept {
    if (m_isCompressed) {
        const_cast<Tile*>(this)->decompress();
    }
}

void Tile::ensureUnique() {
    if (m_buffer && m_buffer.use_count() > 1) {
        m_buffer = std::make_shared<PixelBuffer>(*m_buffer);
    } else {
        // Contagem 1 pode ser a de um instantâneo que outra thread acabou de soltar
        // (gravação em segundo plano): a fence garante que as leituras dela terminaram
        // antes da nossa escrita.
        std::atomic_thread_fence(std::memory_order_acquire);
    }
}

bool Tile::compress() noexcept {
    if (m_isCompressed) return true;
    if (!m_buffer) return false;

    // Se o buffer for compartilhado por COW com outro tile, não comprime inline
    if (m_buffer.use_count() > 1) {
        return false;
    }

    const uint8_t* rawData = m_buffer->getData();
    const size_t rawSize = m_buffer->getSizeInBytes();

    std::vector<uint8_t> compressed = compression::Lz4Codec::compress(rawData, rawSize);
    if (compressed.empty()) return false;

    m_compressedData = std::move(compressed);
    m_compressedData.shrink_to_fit();
    m_buffer.reset();
    m_isCompressed = true;
    return true;
}

bool Tile::decompress() noexcept {
    if (!m_isCompressed) return true;
    if (m_compressedData.empty()) return false;

    auto newBuf = std::make_shared<PixelBuffer>(TILE_SIZE, TILE_SIZE, m_format, utils::ColorRGBA{0, 0, 0, 0});
    bool ok = compression::Lz4Codec::decompressBlock(
        m_compressedData.data(),
        m_compressedData.size(),
        newBuf->getData(),
        bytesFor(m_format)
    );
    if (!ok) return false;

    m_buffer = std::move(newBuf);
    m_compressedData.clear();
    m_compressedData.shrink_to_fit();
    m_isCompressed = false;
    return true;
}

namespace {

template <class Pixel>
bool alphaIsZeroEverywhere(const PixelBuffer& buf) noexcept {
    const Pixel* pixels = buf.pixels<Pixel>();
    const size_t count = buf.getSizeInBytes() / sizeof(Pixel);
    for (size_t i = 0; i < count; ++i) {
        if (pixels[i].a != 0) return false;
    }
    return true;
}

bool alphaIsZeroEverywhere(const PixelBuffer& buf) noexcept {
    return buf.getFormat() == PixelFormat::RGBA16 ? alphaIsZeroEverywhere<utils::ColorRGBA16>(buf)
                                                  : alphaIsZeroEverywhere<utils::ColorRGBA>(buf);
}

} // namespace

bool Tile::isEmpty() const noexcept {
    if (!m_isCompressed) return alphaIsZeroEverywhere(*m_buffer);
    // Perguntar se um tile comprimido está vazio não o descomprime de vez (a região suja de uma camada
    // pergunta isso de cada tile dela a cada mudança de opacidade ou modo).
    thread_local PixelBuffer scratch(TILE_SIZE, TILE_SIZE, utils::ColorRGBA{0, 0, 0, 0});  // `view` a ajusta ao formato
    return alphaIsZeroEverywhere(view(scratch));
}

size_t Tile::getMemoryFootprint() const noexcept {
    size_t base = sizeof(Tile);
    if (m_isCompressed) {
        return base + m_compressedData.size();
    }
    if (m_buffer) {
        const size_t bufBytes = m_buffer->getSizeInBytes();
        const size_t owners = m_buffer.use_count();
        return base + (owners > 0 ? (bufBytes / owners) : bufBytes);
    }
    return base;
}

const uint8_t* zeroTileData() noexcept {
    static const std::vector<uint8_t> zeros(Tile::bytesFor(PixelFormat::RGBA16), 0);
    return zeros.data();
}

} // namespace aladyn::engine::canvas
