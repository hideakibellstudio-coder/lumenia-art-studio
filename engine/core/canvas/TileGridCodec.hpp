#ifndef ALADYN_ENGINE_TILE_GRID_CODEC_HPP
#define ALADYN_ENGINE_TILE_GRID_CODEC_HPP

#include "TileGrid.hpp"
#include <cstddef>
#include <cstdint>
#include <vector>

namespace aladyn::engine::canvas {

// Formato em bytes de UMA camada, para o arquivo .lmn (versão 3). Só os tiles que têm
// algum pixel visível entram; um tile 100% transparente é um buraco, não um registro.
// Cada tile é guardado em LZ4 (ou cru, quando LZ4 não ajuda), de modo que o custo de
// gravar e de abrir é proporcional ao que está pintado, não ao tamanho do canvas.
//
//   cabeçalho (24 bytes, little-endian)
//     "LMNT" | u16 formato=1 | u16 lado do tile=128 | u32 largura | u32 altura
//            | u32 quantidade de tiles | u32 formato de pixel (0 = RGBA8, 1 = RGBA16)
//   quantidade de registros, em ordem (ty, tx) estritamente crescente
//     u16 tx | u16 ty | u8 codec (0 cru, 1 LZ4) | 3 bytes reservados=0 | u32 bytes guardados
//     | bytes guardados
//
// O campo que era "reservado=0" passou a ser o formato de pixel, e 0 é RGBA8: o bloco de uma camada de 8 bits tem
// os mesmos bytes de antes, e um build que só conhece 8 bits recusa um bloco de 16 (campo diferente de zero) em
// vez de ler 131072 bytes por tile como se fossem 65536. Cada tile guarda `Tile::bytesFor(formato)` bytes.
//
// A integridade do que foi gravado é do contêiner ZIP (CRC32 por entrada); aqui se valida
// a estrutura: nada fora da grade, nada fora de ordem, nenhum tamanho que não bata, e o
// arquivo termina exatamente no último registro. Dado malformado é erro de quem chama
// (std::invalid_argument), nunca um tile em branco no lugar.
namespace TileGridCodec {

constexpr uint16_t kFormat = 1;
constexpr size_t kHeaderBytes = 24;
constexpr size_t kEntryHeaderBytes = 12;

// Lê só os tiles da grade (sem alterá-la) e devolve o blob. Seguro de chamar de outra
// thread sobre uma grade que ninguém mais está alterando (um instantâneo copy-on-write).
[[nodiscard]] std::vector<uint8_t> encode(const TileGrid& grid);

// O formato de pixel gravado no cabeçalho de um blob (para criar a grade certa antes de decodificar).
// Cabeçalho ausente ou inválido: std::invalid_argument.
[[nodiscard]] PixelFormat peekFormat(const uint8_t* data, size_t size);

// Troca o conteúdo de `grid` pelo do blob. A grade precisa ter a mesma largura, altura e formato de pixel
// gravados. Se o blob for inválido a grade fica como estava.
void decode(const uint8_t* data, size_t size, TileGrid& grid);

} // namespace TileGridCodec

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_TILE_GRID_CODEC_HPP
