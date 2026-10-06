#ifndef ALADYN_ENGINE_COMPOSITE_PROJECTION_HPP
#define ALADYN_ENGINE_COMPOSITE_PROJECTION_HPP

#include "../../canvas/Tile.hpp"
#include <cstddef>
#include <cstdint>
#include <vector>

namespace aladyn::engine::document::projection {

// Um retângulo de pixels [x0, x1) x [y0, y1); vazio quando não tem área.
struct PixelRect {
    int x0{0};
    int y0{0};
    int x1{0};
    int y1{0};

    [[nodiscard]] bool empty() const noexcept { return x0 >= x1 || y0 >= y1; }
    [[nodiscard]] bool operator==(const PixelRect& other) const noexcept {
        return x0 == other.x0 && y0 == other.y0 && x1 == other.x1 && y1 == other.y1;
    }
};

// ─── A PROJEÇÃO: O QUE DO BUFFER COMPOSTO ESTÁ VELHO ─────────────────────────
//
// O buffer composto tem o tamanho do canvas e, até 2026-10-03, era refeito inteiro (ou na caixa da camada)
// a cada operação de camada, mesmo quando a tela mostrava um pedaço dele: reordenar, duplicar ou mesclar
// 20 camadas em 4096² custava ~250 ms (1 s antes do kernel de mesclagem) para o que cabia numa janela de
// 1080p. A projeção lembra, por tile de 128x128, se o buffer composto naquele tile ainda é o que a
// composição das camadas daria. Quem muda o documento MARCA o que mudou como velho (barato: um byte por
// tile); quem precisa de pixels (a tela, a pirâmide de LOD, a varinha, a exportação) pede `staleRects` da
// área que vai ler e recompõe só isso.
//
// Invariante: tile fresco => o buffer composto nele é igual ao da composição inteira. Marcar a mais só
// custa trabalho; marcar a menos mostraria um pixel velho. Por isso `markFresh` só aceita tiles INTEIROS
// dentro do retângulo que acabou de ser composto.
//
// Não sabe nada de camadas nem de pixels: quem compõe é o `Compositor`, que é dono de uma projeção.
class CompositeProjection {
public:
    static constexpr int kTileSize = canvas::Tile::TILE_SIZE;

    CompositeProjection() = default;
    // Nasce tudo velho: nada foi composto ainda.
    CompositeProjection(int width, int height);

    void markAllStale() noexcept;
    // Todo tile que o retângulo toca fica velho.
    void markStale(const PixelRect& rect);
    // Só os tiles cuja extensão (cortada ao canvas) cabe inteira no retângulo ficam frescos.
    void markFresh(const PixelRect& rect);

    [[nodiscard]] bool anyStale() const noexcept { return m_staleCount > 0; }
    [[nodiscard]] size_t staleTileCount() const noexcept { return m_staleCount; }
    [[nodiscard]] size_t tileCount() const noexcept { return m_stale.size(); }

    // O retângulo que envolve `rect` e os tiles velhos que ele toca (inteiros): compor isso deixa fresco
    // tudo o que `rect` tocava. Sem tile velho no caminho devolve o próprio `rect`.
    [[nodiscard]] PixelRect expandToStale(const PixelRect& rect) const;

    // Os tiles velhos que `rect` toca, em retângulos alinhados a tile (cortados ao canvas), juntando
    // vizinhos em poucas caixas: um canvas inteiro velho dá uma caixa.
    [[nodiscard]] std::vector<PixelRect> staleRects(const PixelRect& rect) const;

    [[nodiscard]] int width() const noexcept { return m_width; }
    [[nodiscard]] int height() const noexcept { return m_height; }

private:
    // Faixa de tiles [tx0, tx1] x [ty0, ty1] que `rect` toca; falso se não toca nenhum.
    struct TileSpan {
        int tx0, ty0, tx1, ty1;
    };
    [[nodiscard]] bool touchedTiles(const PixelRect& rect, TileSpan& span) const noexcept;
    [[nodiscard]] PixelRect tileExtent(int tx, int ty) const noexcept;
    void setTile(int tx, int ty, bool stale) noexcept;

    int m_width{0};
    int m_height{0};
    int m_tilesX{0};
    int m_tilesY{0};
    std::vector<uint8_t> m_stale;
    size_t m_staleCount{0};
};

} // namespace aladyn::engine::document::projection

#endif // ALADYN_ENGINE_COMPOSITE_PROJECTION_HPP
