#include "PaintEngineFacade.hpp"
#include <algorithm>
#include <stdexcept>
#include "../orchestrator/DocumentContext.hpp"
#include "../orchestrator/RasterExportOrchestrator.hpp"

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

void PaintEngineFacade::setColorProfile(int profileId) noexcept {
    if (!color::ColorProfileManager::isProfileValid(profileId)) return;
    if (m_colorProfileId == profileId) return;
    m_colorProfileId = profileId;
    touchDocument();
    // O perfil muda cada pixel da tela sem o compositor escrever nada: a piramide inteira.
    m_mipmapPyramid.markDirty();
}

uint8_t* PaintEngineFacade::getDisplayRawPixelData() noexcept {
    return orchestrator::RasterExportOrchestrator::resolveDisplayBuffer(m_colorProfileId, m_outputBuffer, m_displayBuffer);
}
void PaintEngineFacade::copyDisplayRegion(int x, int y, int w, int h, uint8_t* dst, size_t dstSize) const {
    orchestrator::RasterExportOrchestrator::copyDisplayRegion(m_colorProfileId, m_outputBuffer, x, y, w, h, dst, dstSize);
}
std::vector<uint8_t> PaintEngineFacade::getLayerPixelBuffer(int layerIndex) const {
    return orchestrator::RasterExportOrchestrator::getLayerPixelBuffer(m_layerStack, layerIndex, m_width, m_height);
}
std::vector<uint8_t> PaintEngineFacade::getLayerThumbnailBuffer(int layerIdx, int thumbW, int thumbH) const {
    return orchestrator::RasterExportOrchestrator::getLayerThumbnailBuffer(m_layerStack, layerIdx, thumbW, thumbH);
}
std::string PaintEngineFacade::transformRgbaForProfile(const std::string& buffer, int profileId) const {
    return orchestrator::RasterExportOrchestrator::transformRgbaForProfile(buffer, profileId);
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
    // O que o compositor escreveu desde a ultima leitura e' o que a piramide refaz. Ate
    // 2026-10-01 isto olhava as bandeiras de tile sujo da camada ativa, que ninguem
    // limpava: depois do primeiro traco a piramide inteira era refeita a cada leitura,
    // mesmo sem mudanca nenhuma (D18).
    const canvas::DamageRect damage = m_compositor.takeDamage();
    m_mipmapPyramid.markDirtyRegion(damage.x0(), damage.y0(), damage.x1(), damage.y1());
    // Build from the same buffer returned to the display.  With the
    // default sRGB profile getDisplayRawPixelData() aliases outputBuffer;
    // using the untouched display scratch buffer would otherwise yield a
    // stale white pyramid.
    const auto& displayBase = (m_colorProfileId == 0) ? m_outputBuffer : m_displayBuffer;
    return m_mipmapPyramid.getLODData(level, displayBase, outW, outH);
}

void PaintEngineFacade::copyDisplayLodRegion(int level, int x, int y, int w, int h, uint8_t* dst, size_t dstSize) {
    if (level < 1 || level > canvas::MipmapPyramid::MAX_LOD_LEVELS) {
        throw std::invalid_argument("LOD level must be between 1 and the number of pyramid levels");
    }
    int levelW = 0, levelH = 0;
    const uint8_t* data = getDisplayPixelBufferLOD(level, levelW, levelH);
    orchestrator::RasterExportOrchestrator::copyBufferRegion(data, levelW, levelH, x, y, w, h, dst, dstSize);
}

void PaintEngineFacade::getLodSize(int level, int& outW, int& outH) const noexcept {
    canvas::MipmapPyramid::levelSize(std::clamp(level, 0, canvas::MipmapPyramid::MAX_LOD_LEVELS), m_width, m_height, outW, outH);
}

} // namespace aladyn::engine::boundary
