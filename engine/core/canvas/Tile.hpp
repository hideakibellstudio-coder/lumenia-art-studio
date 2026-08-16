#ifndef ALADYN_ENGINE_TILE_HPP
#define ALADYN_ENGINE_TILE_HPP

#include "PixelBuffer.hpp"
#include "../math/Rect2D.hpp"

namespace aladyn::engine::canvas {

class Tile {
public:
    static constexpr int TILE_SIZE = 128;

    Tile(int tileX, int tileY)
        : m_tileX(tileX), m_tileY(tileY), m_buffer(TILE_SIZE, TILE_SIZE, {0, 0, 0, 0}) {}

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

    [[nodiscard]] PixelBuffer& getBuffer() noexcept { return m_buffer; }
    [[nodiscard]] const PixelBuffer& getBuffer() const noexcept { return m_buffer; }

    [[nodiscard]] bool isDirty() const noexcept { return m_dirty; }
    void setDirty(bool dirty) noexcept { m_dirty = dirty; }

private:
    int m_tileX{0};
    int m_tileY{0};
    bool m_dirty{true};
    PixelBuffer m_buffer;
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_TILE_HPP
