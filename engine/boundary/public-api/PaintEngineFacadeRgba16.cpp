#include "PaintEngineFacade.hpp"
#include "../orchestrator/RasterExportOrchestrator.hpp"
#include <cstring>
#include <stdexcept>

// ─────────────────────────────────────────────────────────────────────────────
// PaintEngineFacade — leitura dos pixels de 16 bits (S5).
//
// Um documento de 16 bits compõe as camadas num buffer interno de 16 bits (Compositor::composite16) e entrega à tela
// o resultado estreitado a 8. Quem precisa dos 16 bits (exportação, conta-gotas, o histograma) lê por aqui: a
// composição, só o retângulo pedido e já em dia, e uma camada inteira. Num documento de 8 bits não há o que ler.
// ─────────────────────────────────────────────────────────────────────────────

namespace aladyn::engine::boundary {

void PaintEngineFacade::copyComposite16(int x, int y, int w, int h, uint8_t* dst, size_t dstSize) {
    if (m_layerStack.getPixelFormat() != canvas::PixelFormat::RGBA16) throw std::logic_error("the document is not 16-bit");
    // Só os tiles velhos que o retângulo toca: o buffer de 16 bits está em dia nesse retângulo quando a composição acaba.
    if (w > 0 && h > 0) {
        m_compositor.ensureFresh(
            m_layerStack.getAllLayersForComposition(),
            utils::Rect2D{static_cast<double>(x), static_cast<double>(y), static_cast<double>(w), static_cast<double>(h)},
            m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    const canvas::PixelBuffer* wide = m_compositor.composite16();
    constexpr size_t kPixelBytes = 8;
    if (wide == nullptr) {
        // Nada foi composto ainda (pilha sem camadas visíveis): o canvas é transparente.
        orchestrator::RasterExportOrchestrator::copyBufferRegion(dst, m_width, m_height, x, y, w, h, dst, dstSize, kPixelBytes);
        std::memset(dst, 0, dstSize);
        return;
    }
    orchestrator::RasterExportOrchestrator::copyBufferRegion(wide->getData(), m_width, m_height, x, y, w, h, dst, dstSize, kPixelBytes);
}

void PaintEngineFacade::copyLayer16(int layerIndex, uint8_t* dst, size_t dstSize) const {
    orchestrator::RasterExportOrchestrator::copyLayerPixels16(m_layerStack, layerIndex, m_width, m_height, dst, dstSize);
}

} // namespace aladyn::engine::boundary
