#include "PaintEngineFacade.hpp"
#include "internal/DocumentContext.hpp"
#include "internal/RasterExportOrchestrator.hpp"

// ─────────────────────────────────────────────────────────────────────────────
// PaintEngineFacade — saida para a tela.
//
// Opcoes de render (baixa latencia, gama linear, cor profunda), buffer de
// exibicao com perfil de cor, pixels e miniaturas de camada, tiles sujos e a
// piramide de LOD da viewport. Separado de PaintEngineFacade.cpp/.hpp em
// 2026-09-24: os dois estavam na parede dos 450 linhas (445 e 437) e o
// header carregava os corpos de LOD e tiles sujos inline.
// ─────────────────────────────────────────────────────────────────────────────

namespace aladyn::engine::boundary {

// ─── OPCOES DE RENDER E SAIDA RASTER ──────────────────────────────────────

void PaintEngineFacade::setLowLatency(bool enabled) noexcept { m_lowLatency = enabled; }
void PaintEngineFacade::setLinearGamma(bool enabled) { setRenderOptions(m_lowLatency, enabled, m_deepColor); }
void PaintEngineFacade::setDeepColor(bool enabled) { setRenderOptions(m_lowLatency, m_linearGamma, enabled); }

void PaintEngineFacade::setRenderOptions(bool lowLatency, bool linearGamma, bool deepColor) {
    const bool compositionChanged = (m_linearGamma != linearGamma) || (m_deepColor != deepColor);
    m_lowLatency = lowLatency;
    m_linearGamma = linearGamma;
    m_deepColor = deepColor;
    m_compositor.setLinearGamma(linearGamma);
    m_compositor.setDeepColor(deepColor);
    if (compositionChanged) {
        const auto ctx = docContext();
        ctx.compositeAll();
        ctx.touch();
    }
}

uint8_t* PaintEngineFacade::getDisplayRawPixelData() noexcept {
    return internal::RasterExportOrchestrator::resolveDisplayBuffer(m_colorProfileId, m_outputBuffer, m_displayBuffer);
}
std::vector<uint8_t> PaintEngineFacade::getLayerPixelBuffer(int layerIndex) const {
    return internal::RasterExportOrchestrator::getLayerPixelBuffer(m_layerStack, layerIndex, m_width, m_height);
}
std::vector<uint8_t> PaintEngineFacade::getLayerThumbnailBuffer(int layerIdx, int thumbW, int thumbH) const {
    return internal::RasterExportOrchestrator::getLayerThumbnailBuffer(m_layerStack, layerIdx, thumbW, thumbH);
}
std::string PaintEngineFacade::transformRgbaForProfile(const std::string& buffer, int profileId) const {
    return internal::RasterExportOrchestrator::transformRgbaForProfile(buffer, profileId);
}

// ─── TILES SUJOS E LOD DA VIEWPORT ────────────────────────────────────────

std::vector<std::pair<int, int>> PaintEngineFacade::getDirtyTileIndices() const {
    if (const auto* layer = m_layerStack.getActiveLayer()) {
        return layer->getTileGrid().getDirtyTileIndices();
    }
    return {};
}

void PaintEngineFacade::clearDirtyTiles() noexcept {
    if (auto* layer = m_layerStack.getActiveLayer()) {
        layer->getTileGrid().clearDirtyFlags();
    }
}

uint8_t* PaintEngineFacade::getDisplayPixelBufferLOD(int level, int& outW, int& outH) noexcept {
    // Resolve o buffer de exibicao (aplica o perfil de cor) antes de ler.
    (void)getDisplayRawPixelData();
    if (const auto* layer = m_layerStack.getActiveLayer()) {
        if (!layer->getTileGrid().getDirtyTileIndices().empty()) {
            m_mipmapPyramid.markDirty();
        }
    }
    // Build from the same buffer returned to the display.  With the
    // default sRGB profile getDisplayRawPixelData() aliases outputBuffer;
    // using the untouched display scratch buffer would otherwise yield a
    // stale white pyramid.
    const auto& displayBase = (m_colorProfileId == 0) ? m_outputBuffer : m_displayBuffer;
    return m_mipmapPyramid.getLODData(level, displayBase, outW, outH);
}

} // namespace aladyn::engine::boundary
