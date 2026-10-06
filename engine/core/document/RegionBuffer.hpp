#ifndef ALADYN_ENGINE_DOCUMENT_INTERNAL_REGION_BUFFER_HPP
#define ALADYN_ENGINE_DOCUMENT_INTERNAL_REGION_BUFFER_HPP

#include "CompositeRegionSupport.hpp"
#include "../canvas/PixelBuffer.hpp"
#include <cstdint>
#include <vector>

namespace aladyn::engine::document::internal {

// O buffer em que uma composicao por regiao escreve: o fundo, a margem que o filtro pede e a passagem do buffer
// composto de 16 bits para o de saida de 8 bits. Todas as funcoes servem aos dois formatos de pixel: o formato e'
// o do buffer que recebem.

// Preenche `buffer` com bgFill dentro de bounds (alargada a x257 num buffer de 16 bits), com fast-path de memset
// quando a regiao cobre o canvas inteiro e a cor e transparente.
// `parallelRowThreshold` preserva o limiar de `#pragma omp` historico de cada
// chamador (256 em compositeRegion, 64 em compositeRegionWithScratch).
void fillBackground(
    canvas::PixelBuffer& buffer,
    const RegionBounds& bounds,
    const utils::ColorRGBA& bgFill,
    int canvasWidth,
    int canvasHeight,
    int parallelRowThreshold
);

// Guarda a margem de uma regiao composta: a regiao pedida (`inner`) e' inflada pelo alcance dos filtros
// (`outer`) so para dar vizinhos ao filtro. Na margem o filtro le para fora da regiao e escreve um valor
// errado; ate 2026-10-01 isso ia direto para o buffer de saida e uma pincelada deixava uma faixa de pixels
// diferentes da composicao inteira, ate a proxima recomposicao total. A margem e' salva antes de compor e
// devolvida depois: so o que foi pedido muda.
class RegionMargin {
public:
    RegionMargin(canvas::PixelBuffer& buffer, const RegionBounds& outer, const RegionBounds& inner);

    // Devolve ao buffer os pixels da margem como estavam antes da composicao.
    void restore();

private:
    template <typename Visit>
    void forEachSegment(Visit&& visit) const;

    canvas::PixelBuffer& m_buffer;
    RegionBounds m_outer;
    RegionBounds m_inner;
    std::vector<uint8_t> m_saved;  // os bytes dos trechos, na ordem de `forEachSegment`
};

// A regiao `region` do buffer composto de 16 bits, estreitada ao inteiro de 8 bits mais proximo de cada canal,
// escrita no mesmo lugar do buffer de saida (o unico arredondamento entre as camadas de 16 bits e a tela).
void narrowRegion(const canvas::PixelBuffer& wide, canvas::PixelBuffer& narrowed, const RegionBounds& region);

} // namespace aladyn::engine::document::internal

#endif // ALADYN_ENGINE_DOCUMENT_INTERNAL_REGION_BUFFER_HPP
