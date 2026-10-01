#ifndef ALADYN_ENGINE_DECODED_LAYER_HPP
#define ALADYN_ENGINE_DECODED_LAYER_HPP

#include "../../core/canvas/TileGrid.hpp"
#include <cstddef>
#include <cstdint>

namespace aladyn::engine::boundary {

// Os pixels de uma camada já decodificados de um bloco de tiles, fora de qualquer documento (S1.2).
//
// Abrir um arquivo grande leva centenas de milissegundos só para descomprimir os tiles. O
// objeto nasce de um bloco (`TileGridCodec`) em qualquer thread, sem tocar no motor, e depois
// `PaintEngineFacade::adoptDecodedLayer` o coloca numa camada em tempo constante: a thread da
// interface não paga a descompressão.
class DecodedLayer {
public:
    // std::invalid_argument se o bloco for malformado ou se o tamanho do canvas for ilegal.
    DecodedLayer(int width, int height, const uint8_t* data, size_t size);

    [[nodiscard]] int width() const noexcept { return m_grid.getWidth(); }
    [[nodiscard]] int height() const noexcept { return m_grid.getHeight(); }
    // Entrega os pixels, uma vez só: depois disto o objeto está vazio (std::logic_error se repetir).
    [[nodiscard]] canvas::TileGrid take();

private:
    canvas::TileGrid m_grid;
    bool m_taken{false};
};

} // namespace aladyn::engine::boundary

#endif // ALADYN_ENGINE_DECODED_LAYER_HPP
