#ifndef ALADYN_ENGINE_STROKE_OPACITY_MIX_HPP
#define ALADYN_ENGINE_STROKE_OPACITY_MIX_HPP

#include "../canvas/TileGrid.hpp"
#include <memory>

namespace aladyn::engine::raster {

// Opacidade do traço como TETO (o "Opacity" do Photoshop/Krita/Clip Studio; o "Flow" é o que cada carimbo
// deposita e continua nos próprios dabs).
//
// Com opacidade abaixo de 100%, o mini-motor não pinta na camada: pinta numa cópia de trabalho dela, com a
// mesma lógica de sempre (fluxo, trava de alfa, seleção, multiplicar, borracha, borrar...). Depois de cada
// segmento, a camada recebe a MISTURA entre o que ela era no início do traço (a base) e a cópia de trabalho:
//
//     camada = base + (trabalho - base) * opacidade        (em alfa pré-multiplicado, arredondado)
//
// O teto vale para qualquer motor porque a conta não olha para o que o motor fez, só para o quanto ele
// mudou o pixel. A base e o trabalho são cópias Copy-on-Write da grade: custam só os tiles que o traço toca.
//
// Com opacidade 100% (`needed()` falso) nada disto existe e o traço segue o caminho direto de sempre.
class StrokeOpacityMix {
public:
    // Opacidade a partir da qual o teto não muda nada (fora do alcance do 8 bits).
    static constexpr double kFullOpacity = 0.998;

    [[nodiscard]] static bool needed(double opacity) noexcept { return opacity < kFullOpacity; }

    // Tira a base e a cópia de trabalho de `layerGrid` (pelo índice da camada, para o orquestrador conferir
    // que o traço continua na mesma camada).
    void begin(const canvas::TileGrid& layerGrid, double opacity, int layerIndex);
    void end() noexcept;

    [[nodiscard]] bool active() const noexcept { return m_work != nullptr; }
    [[nodiscard]] int layerIndex() const noexcept { return m_layerIndex; }
    [[nodiscard]] canvas::TileGrid& work() noexcept { return *m_work; }

    // Reescreve em `layerGrid` os tiles [firstX..lastX] x [firstY..lastY] com a mistura. Tile que o trabalho
    // ainda não tocou (mesmo buffer da base) é pulado sem olhar um pixel.
    void mergeInto(canvas::TileGrid& layerGrid, int firstTileX, int firstTileY, int lastTileX, int lastTileY);

private:
    std::unique_ptr<canvas::TileGrid> m_base;
    std::unique_ptr<canvas::TileGrid> m_work;
    double m_opacity{1.0};
    int m_layerIndex{-1};
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_STROKE_OPACITY_MIX_HPP
