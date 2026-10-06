#ifndef ALADYN_ENGINE_TILE_HPP
#define ALADYN_ENGINE_TILE_HPP

#include "PixelBuffer.hpp"
#include "../../utils/Rect2D.hpp"
#include <memory>
#include <vector>
#include <cstdint>
#include <cstddef>

namespace aladyn::engine::canvas {

class Tile {
public:
    static constexpr int TILE_SIZE = 128;
    static constexpr size_t TILE_BYTES = TILE_SIZE * TILE_SIZE * sizeof(utils::ColorRGBA); // RGBA8: 65536 bytes

    // Bytes de um tile no formato: 65536 em RGBA8, 131072 em RGBA16.
    [[nodiscard]] static constexpr size_t bytesFor(PixelFormat format) noexcept {
        return static_cast<size_t>(TILE_SIZE) * TILE_SIZE * bytesPerPixel(format);
    }

    Tile(int tileX, int tileY, PixelFormat format = PixelFormat::RGBA8);
    // O formato do tile é o do buffer (um buffer nulo vira um tile RGBA8 transparente).
    Tile(int tileX, int tileY, std::shared_ptr<PixelBuffer> sharedBuffer);

    [[nodiscard]] PixelFormat getFormat() const noexcept { return m_format; }

    [[nodiscard]] int getTileX() const noexcept { return m_tileX; }
    [[nodiscard]] int getTileY() const noexcept { return m_tileY; }

    [[nodiscard]] int getPixelX() const noexcept { return m_tileX * TILE_SIZE; }
    [[nodiscard]] int getPixelY() const noexcept { return m_tileY * TILE_SIZE; }

    [[nodiscard]] utils::Rect2D getBounds() const noexcept {
        return utils::Rect2D{
            static_cast<double>(getPixelX()),
            static_cast<double>(getPixelY()),
            static_cast<double>(TILE_SIZE),
            static_cast<double>(TILE_SIZE)
        };
    }

    /// Acesso mutável (assegura descompressão e unicidade COW)
    [[nodiscard]] PixelBuffer& getBuffer() noexcept;

    /// Acesso somente-leitura (assegura descompressão sem forçar cópia COW)
    [[nodiscard]] const PixelBuffer& getBuffer() const noexcept;

    /// Leitura que não muda o tile: um tile comprimido continua comprimido e é descomprimido em `scratch`
    /// (de TILE_SIZE x TILE_SIZE, uma por thread; ela se ajusta ao formato do tile se precisar). Quem só lê
    /// (composição, exportação) usa esta: `getBuffer()` descomprime de vez, e a composição inteira desfazia
    /// `compress_inactive_layers` (181 MB -> 126 -> 181).
    [[nodiscard]] const PixelBuffer& view(PixelBuffer& scratch) const noexcept;

    [[nodiscard]] bool isDirty() const noexcept { return m_dirty; }
    void setDirty(bool dirty) noexcept { m_dirty = dirty; }

    [[nodiscard]] bool isEmpty() const noexcept;

    // ─── FASE 4: COPY-ON-WRITE & COMPRESSÃO LZ4 ──────────────────────────────
    [[nodiscard]] bool isCompressed() const noexcept { return m_isCompressed; }
    [[nodiscard]] bool isShared() const noexcept { return m_buffer && m_buffer.use_count() > 1; }
    [[nodiscard]] size_t getSharedCount() const noexcept { return m_buffer ? m_buffer.use_count() : 0; }
    [[nodiscard]] std::shared_ptr<PixelBuffer> getSharedBuffer() const noexcept { return m_buffer; }

    bool compress() noexcept;
    bool decompress() noexcept;

    void ensureUnique();
    void ensureDecompressed() const noexcept;

    [[nodiscard]] size_t getMemoryFootprint() const noexcept;

private:
    int m_tileX{0};
    int m_tileY{0};
    PixelFormat m_format{PixelFormat::RGBA8};
    bool m_dirty{true};
    mutable bool m_isCompressed{false};
    mutable std::shared_ptr<PixelBuffer> m_buffer;
    mutable std::vector<uint8_t> m_compressedData;
};

// Um tile inteiro de zeros, grande o bastante para qualquer formato: o "antes" de um tile que ainda não existia
// (histórico) e a cópia de um tile vazio. O tamanho a usar é `Tile::bytesFor(formato)`.
[[nodiscard]] const uint8_t* zeroTileData() noexcept;

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_TILE_HPP
