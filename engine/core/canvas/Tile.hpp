#ifndef ALADYN_ENGINE_TILE_HPP
#define ALADYN_ENGINE_TILE_HPP

#include "PixelBuffer.hpp"
#include "../math/Rect2D.hpp"
#include <memory>
#include <vector>
#include <cstdint>
#include <cstddef>

namespace aladyn::engine::canvas {

class Tile {
public:
    static constexpr int TILE_SIZE = 128;
    static constexpr size_t TILE_BYTES = TILE_SIZE * TILE_SIZE * sizeof(raster::ColorRGBA); // 65536 bytes

    Tile(int tileX, int tileY);
    Tile(int tileX, int tileY, std::shared_ptr<PixelBuffer> sharedBuffer);

    [[nodiscard]] int getTileX() const noexcept { return m_tileX; }
    [[nodiscard]] int getTileY() const noexcept { return m_tileY; }

    [[nodiscard]] int getPixelX() const noexcept { return m_tileX * TILE_SIZE; }
    [[nodiscard]] int getPixelY() const noexcept { return m_tileY * TILE_SIZE; }

    [[nodiscard]] math::Rect2D getBounds() const noexcept {
        return math::Rect2D{
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
    bool m_dirty{true};
    mutable bool m_isCompressed{false};
    mutable std::shared_ptr<PixelBuffer> m_buffer;
    mutable std::vector<uint8_t> m_compressedData;
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_TILE_HPP
