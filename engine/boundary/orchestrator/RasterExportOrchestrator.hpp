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
    static std::vector<uint8_t> getLayerPixelBuffer(
        const document::LayerStack& stack, int layerIndex, int width, int height
    );

    static std::vector<uint8_t> getLayerThumbnailBuffer(
        const document::LayerStack& stack, int layerIdx, int thumbW, int thumbH
    );

    static std::string transformRgbaForProfile(const std::string& buffer, int profileId);

    static void applyColorProfile(uint8_t* targetBuffer, size_t numPixels, int colorProfileId) noexcept;

    // Devolve o buffer que a UI deve ler. Com o perfil sRGB (id 0) nao ha
    // conversao e o proprio outputBuffer e' devolvido; nos demais perfis o
    // conteudo e' copiado para displayBuffer e convertido la.
    static uint8_t* resolveDisplayBuffer(
        int colorProfileId, canvas::PixelBuffer& outputBuffer, canvas::PixelBuffer& displayBuffer
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
    static void copyBufferRegion(
        const uint8_t* src, int srcW, int srcH,
        int x, int y, int w, int h, uint8_t* dst, size_t dstSize
    );
};

} // namespace aladyn::engine::boundary::orchestrator
