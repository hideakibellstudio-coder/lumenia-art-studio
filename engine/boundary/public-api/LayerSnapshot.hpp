#ifndef ALADYN_ENGINE_LAYER_SNAPSHOT_HPP
#define ALADYN_ENGINE_LAYER_SNAPSHOT_HPP

#include "../../core/canvas/TileGrid.hpp"
#include "../../core/document/LayerStack.hpp"
#include <cstdint>
#include <memory>
#include <vector>

namespace aladyn::engine::boundary {

// Os pixels de todas as camadas de um documento, congelados num instante (S1.2).
//
// Gravar um documento grande leva segundos; fazer isso na thread da interface trava a
// tela, e fazer em outra thread sobre as camadas vivas dá corrida com o próximo traço.
// O instantâneo resolve os dois: é tirado na thread dona do documento e custa só o
// número de tiles (compartilha os buffers copy-on-write, nenhum pixel é copiado), e
// depois pode ser lido de qualquer thread enquanto o artista continua pintando. Quando
// o traço seguinte escreve num tile compartilhado, o tile vivo é clonado e o do
// instantâneo continua como estava.
//
// Só lê. Nunca toca o documento de onde veio.
class LayerSnapshot {
public:
    LayerSnapshot(const document::LayerStack& stack, int width, int height);

    [[nodiscard]] int width() const noexcept { return m_width; }
    [[nodiscard]] int height() const noexcept { return m_height; }
    // Camadas na ordem do motor (a mesma de get_layer_pixel_buffer), grupos e filtros incluídos.
    [[nodiscard]] int layerCount() const noexcept { return static_cast<int>(m_grids.size()); }
    // Falso para grupo e filtro: não têm pixels.
    [[nodiscard]] bool hasPixels(int index) const noexcept {
        return index >= 0 && index < layerCount() && m_grids[static_cast<size_t>(index)] != nullptr;
    }

    // A camada como bloco de tiles (core/canvas/TileGridCodec.hpp). Camada sem pixels ou
    // índice fora do intervalo: std::invalid_argument.
    [[nodiscard]] std::vector<uint8_t> encodeLayer(int index) const;

private:
    int m_width;
    int m_height;
    std::vector<std::unique_ptr<canvas::TileGrid>> m_grids;  // nulo para grupo e filtro
};

} // namespace aladyn::engine::boundary

#endif // ALADYN_ENGINE_LAYER_SNAPSHOT_HPP
