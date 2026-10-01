#ifndef ALADYN_ENGINE_GRID_SNAPSHOT_HPP
#define ALADYN_ENGINE_GRID_SNAPSHOT_HPP

#include "TileGrid.hpp"
#include "../../utils/ColorRGBA.hpp"
#include <algorithm>
#include <vector>

namespace aladyn::engine::canvas {

// Foto de um retângulo de uma TileGrid, tirada antes de qualquer escrita.
//
// Um pincel que lê o que ele mesmo está pintando (Smudge) lê a grade viva, e
// então o resultado depende da ordem em que os tiles e as linhas são visitados:
// o pixel já escrito pelo dab entra na amostra do pixel seguinte. A foto tira a
// dependência: todo pixel do dab lê a grade como ela estava ao chegar o dab.
//
// Fora da grade, ou num tile que não existe, o pixel é transparente (o mesmo
// que ler a grade viva). O vetor é reaproveitado entre capturas.
class GridSnapshot {
public:
    // Fotografa [x0, x1] x [y0, y1] (inclusivos), recortado ao tamanho da grade.
    void capture(const TileGrid& grid, int x0, int y0, int x1, int y1) {
        m_x0 = std::max(0, x0);
        m_y0 = std::max(0, y0);
        const int cx1 = std::min(grid.getWidth() - 1, x1);
        const int cy1 = std::min(grid.getHeight() - 1, y1);
        m_width  = std::max(0, cx1 - m_x0 + 1);
        m_height = std::max(0, cy1 - m_y0 + 1);
        m_pixels.assign(static_cast<size_t>(m_width) * static_cast<size_t>(m_height), utils::ColorRGBA{0, 0, 0, 0});

        auto& mutableGrid = const_cast<TileGrid&>(grid); // getTile não cria: só lê
        for (int y = 0; y < m_height; ++y) {
            const int gy = m_y0 + y;
            const int ty = gy / Tile::TILE_SIZE;
            const int ly = gy % Tile::TILE_SIZE;
            utils::ColorRGBA* row = m_pixels.data() + static_cast<size_t>(y) * static_cast<size_t>(m_width);
            for (int x = 0; x < m_width; ++x) {
                const int gx = m_x0 + x;
                const Tile* tile = mutableGrid.getTile(gx / Tile::TILE_SIZE, ty);
                if (tile) row[x] = tile->getBuffer().getPixel(gx % Tile::TILE_SIZE, ly);
            }
        }
    }

    // Pixel da foto; o que ficou fora dela é transparente.
    [[nodiscard]] utils::ColorRGBA at(int x, int y) const noexcept {
        const int lx = x - m_x0;
        const int ly = y - m_y0;
        if (lx < 0 || ly < 0 || lx >= m_width || ly >= m_height) return {0, 0, 0, 0};
        return m_pixels[static_cast<size_t>(ly) * static_cast<size_t>(m_width) + static_cast<size_t>(lx)];
    }

private:
    int m_x0{0};
    int m_y0{0};
    int m_width{0};
    int m_height{0};
    std::vector<utils::ColorRGBA> m_pixels;
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_GRID_SNAPSHOT_HPP
