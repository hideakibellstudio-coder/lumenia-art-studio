#pragma once

#include "../../core/document/LayerStack.hpp"
#include "../../core/canvas/PixelBuffer.hpp"
#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>

namespace aladyn::engine::boundary::orchestrator {

// Orquestrador de saida raster: tudo que converte o estado interno do
// documento em bytes para fora do motor (buffer de uma camada, miniatura,
// buffer de display com perfil de cor aplicado, conversao avulsa de RGBA).
//
// Extraido de PaintEngineFacade.cpp (Achado #6). Sao rotinas de leitura pura
// -- nao mutam camadas nem historico e nao marcam o documento como alterado --
// e por isso recebem apenas os buffers e dimensoes de que precisam.
class RasterExportOrchestrator {
public:
    // Os pixels de 8 bits da camada (w*h*4 bytes). Numa camada de 16 bits e' a visao estreitada ao inteiro de 8 bits
    // mais proximo de cada canal; os 16 bits inteiros saem por `copyLayerPixels16`.
    static std::vector<uint8_t> getLayerPixelBuffer(
        const document::LayerStack& stack, int layerIndex, int width, int height
    );

    // Os pixels de 16 bits de uma camada de um documento de 16 bits em `dst` (w*h*8 bytes, canais uint16 na ordem da
    // maquina, linhas contiguas). Camada sem pixels, documento de 8 bits ou `dstSize` errado: std::invalid_argument.
    static void copyLayerPixels16(
        const document::LayerStack& stack, int layerIndex, int width, int height, uint8_t* dst, size_t dstSize
    );

    static std::vector<uint8_t> getLayerThumbnailBuffer(
        const document::LayerStack& stack, int layerIdx, int thumbW, int thumbH
    );

    static std::string transformRgbaForProfile(const std::string& buffer, int profileId);

    static void applyColorProfile(uint8_t* targetBuffer, size_t numPixels, int colorProfileId) noexcept;

    // O buffer de exibicao nasce 0x0 e so ganha o tamanho do canvas quando um perfil de cor que nao e' sRGB
    // pede uma copia convertida (ate 2026-10-02 eram 1 GiB sempre alocados em 16384x16384, sem uso no sRGB).
    // Conteudo novo e' transparente: quem pede converte tudo (a piramide trata tamanho novo como "refaz tudo").
    static void ensureDisplayBuffer(const canvas::PixelBuffer& outputBuffer, canvas::PixelBuffer& displayBuffer);

    // Devolve o buffer que a UI deve ler. Com o perfil sRGB (id 0) nao ha
    // conversao e o proprio outputBuffer e' devolvido; nos demais perfis o
    // conteudo e' copiado para displayBuffer e convertido la.
    static uint8_t* resolveDisplayBuffer(
        int colorProfileId, canvas::PixelBuffer& outputBuffer, canvas::PixelBuffer& displayBuffer
    );

    // Atualiza em displayBuffer so o retangulo [x0, x1) x [y0, y1) a partir do buffer de saida,
    // com o perfil de cor aplicado (o resto de displayBuffer fica como estava). A piramide de LOD
    // le o buffer de exibicao so dentro do que mudou, entao converter o canvas inteiro a cada
    // leitura custava 390 ms em 4K com um perfil que nao e' sRGB.
    static void convertDisplayRegion(
        int colorProfileId, const canvas::PixelBuffer& outputBuffer, canvas::PixelBuffer& displayBuffer,
        int x0, int y0, int x1, int y1
    );

    // Copia o retangulo [x, x+w) x [y, y+h) do buffer de saida para `dst`
    // (w*h*4 bytes, linhas contiguas), ja com o perfil de cor aplicado. O custo e'
    // proporcional ao retangulo e nao ao canvas: e' o que a tela pede a cada
    // repintura em zoom de trabalho. Retangulo vazio, fora do canvas ou `dstSize`
    // diferente de w*h*4 e' erro de quem chama (std::invalid_argument), nao um
    // recorte silencioso.
    static void copyDisplayRegion(
        int colorProfileId, const canvas::PixelBuffer& outputBuffer,
        int x, int y, int w, int h, uint8_t* dst, size_t dstSize
    );

    // O mesmo recorte, sem perfil de cor, de um buffer RGBA qualquer de srcW x srcH
    // (um nivel da piramide de LOD, que ja nasce do buffer de exibicao). Mesmos erros.
    // `pixelBytes` e' 4 (8 bits por canal) ou 8 (o buffer composto de 16 bits); `dstSize` e' w*h*pixelBytes.
    static void copyBufferRegion(
        const uint8_t* src, int srcW, int srcH,
        int x, int y, int w, int h, uint8_t* dst, size_t dstSize, size_t pixelBytes = 4
    );
};

} // namespace aladyn::engine::boundary::orchestrator
