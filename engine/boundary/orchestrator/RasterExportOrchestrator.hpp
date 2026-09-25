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
};

} // namespace aladyn::engine::boundary::orchestrator
