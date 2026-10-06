#ifndef ALADYN_ENGINE_STROKE_INK_LEDGER_HPP
#define ALADYN_ENGINE_STROKE_INK_LEDGER_HPP

#include "../canvas/Tile.hpp"
#include "../canvas/TileGrid.hpp"
#include "../../utils/ColorRGBA.hpp"
#include "../../utils/ColorRGBA16.hpp"
#include "../../utils/Rect2D.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <memory>
#include <vector>

namespace aladyn::engine::raster {

// ─── A MEMÓRIA DE UM TRAÇO, PIXEL A PIXEL ───────────────────────────────────
//
// Tinta translúcida (marcador, aquarela) não pode ser composta carimbo sobre carimbo: cada carimbo
// leria o resultado do anterior como se fosse papel e a cor se multiplicaria por ela mesma dezenas de
// vezes, escurecendo o miolo até o preto. Medido em 2026-10-02, azul (30, 90, 170) numa aquarela
// concentrada saía (2, 7, 31) no miolo.
//
// O livro-razão guarda, para cada pixel que o traço tocou, o que havia lá ANTES do primeiro carimbo
// (`base`) e quanto do traço já o cobre (`coverage`, 0 = nenhum carimbo tocou). Com isso o motor
// calcula a cor a partir da base e da cobertura: o miolo de um traço tem a cor da tinta, uma vez, e só
// um traço novo por cima escurece o que o anterior deixou.
//
// Uso: `clear()` ao começar e ao terminar o traço; a cada carimbo, `prepare()` (em série, antes do laço
// paralelo) e `at()` dentro do laço. Os tiles rodam em paralelo, cada um mexe só nas células do seu
// plano, então nenhuma trava é necessária. Um plano custa 192 KB; só existe para tile que o traço tocou.
template <class Pixel = utils::ColorRGBA>
class StrokeInkLedger {
public:
    struct Cell {
        Pixel base{0, 0, 0, 0};  // o pixel antes do primeiro carimbo do traço
        float coverage{0.0f};    // 0 até o primeiro carimbo tocar o pixel
        float shade{0.0f};       // a luz do relevo já aplicada ao pixel (óleo); 0 = nenhuma
    };

    void clear() noexcept {
        m_planes.clear();
        m_tilesX = 0;
        m_tilesY = 0;
    }

    // Cria os planos dos tiles que `area` (em pixels do canvas) alcança em `grid`. Em série.
    void prepare(const utils::Rect2D& area, const canvas::TileGrid& grid) {
        const int tilesX = grid.getTilesCountX();
        const int tilesY = grid.getTilesCountY();
        if (tilesX <= 0 || tilesY <= 0) return;
        if (tilesX != m_tilesX || tilesY != m_tilesY) {
            m_planes.clear();
            m_planes.resize(static_cast<std::size_t>(tilesX) * static_cast<std::size_t>(tilesY));
            m_tilesX = tilesX;
            m_tilesY = tilesY;
        }

        constexpr int kSize = canvas::Tile::TILE_SIZE;
        const auto tileOf = [&](double pixel, int count) {
            return std::clamp(static_cast<int>(std::max(0.0, pixel)) / kSize, 0, count - 1);
        };
        const int firstX = tileOf(std::floor(area.getLeft()), tilesX);
        const int lastX = tileOf(std::ceil(area.getRight()), tilesX);
        const int firstY = tileOf(std::floor(area.getTop()), tilesY);
        const int lastY = tileOf(std::ceil(area.getBottom()), tilesY);
        for (int ty = firstY; ty <= lastY; ++ty) {
            for (int tx = firstX; tx <= lastX; ++tx) {
                std::unique_ptr<Plane>& plane = m_planes[static_cast<std::size_t>(ty) * static_cast<std::size_t>(tilesX)
                                                         + static_cast<std::size_t>(tx)];
                if (!plane) plane = std::make_unique<Plane>();
            }
        }
    }

    // A célula do pixel (x, y) do canvas; só vale em pixel de um tile já preparado.
    [[nodiscard]] Cell& at(int x, int y) noexcept {
        constexpr int kSize = canvas::Tile::TILE_SIZE;
        Plane& plane = *m_planes[static_cast<std::size_t>(y / kSize) * static_cast<std::size_t>(m_tilesX)
                                 + static_cast<std::size_t>(x / kSize)];
        return plane.cells[static_cast<std::size_t>(y % kSize) * kSize + static_cast<std::size_t>(x % kSize)];
    }

private:
    struct Plane {
        std::array<Cell, static_cast<std::size_t>(canvas::Tile::TILE_SIZE) * canvas::Tile::TILE_SIZE> cells{};
    };

    std::vector<std::unique_ptr<Plane>> m_planes;
    int m_tilesX{0};
    int m_tilesY{0};
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_STROKE_INK_LEDGER_HPP
