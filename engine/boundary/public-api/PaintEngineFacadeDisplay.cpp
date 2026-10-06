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
    // O buffer de exibição (1 GiB em 16384²) só serve a um perfil que não é sRGB: de volta ao sRGB, devolve a memória.
    if (profileId == 0) m_displayBuffer.release();
    touchDocument();
    // O perfil muda cada pixel da tela sem o compositor escrever nada: a piramide inteira.
    m_mipmapPyramid.markDirty();
}

// ─── O BUFFER COMPOSTO SÓ É REFEITO ONDE ALGUÉM LÊ ────────────────────────
// As operações de camada marcam tiles velhos (Compositor::invalidate) e não compõem; cada leitor abaixo
// recompõe, antes de ler, os tiles velhos da área que lê. Reordenar 20 camadas em 4096² custava ~250 ms
// de composição do canvas inteiro para uma tela que mostra uma janela dele (S3, 2026-10-03).

void PaintEngineFacade::ensureAllFresh() {
    m_compositor.ensureAllFresh(m_layerStack.getAllLayersForComposition(), m_outputBuffer, m_canvasTexture.backgroundColor);
}

uint8_t* PaintEngineFacade::getRawPixelData() {
    ensureAllFresh();
    return m_outputBuffer.getData();
}

uint8_t* PaintEngineFacade::getDisplayRawPixelData() {
    ensureAllFresh();
    return orchestrator::RasterExportOrchestrator::resolveDisplayBuffer(m_colorProfileId, m_outputBuffer, m_displayBuffer);
}
void PaintEngineFacade::copyDisplayRegion(int x, int y, int w, int h, uint8_t* dst, size_t dstSize) {
    // Só os tiles velhos que o retângulo toca; um retângulo fora do canvas não toca nenhum (e é recusado abaixo).
    if (w > 0 && h > 0) {
        m_compositor.ensureFresh(
            m_layerStack.getAllLayersForComposition(),
            utils::Rect2D{static_cast<double>(x), static_cast<double>(y), static_cast<double>(w), static_cast<double>(h)},
            m_outputBuffer, m_canvasTexture.backgroundColor);
    }
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

uint8_t* PaintEngineFacade::getDisplayPixelBufferLOD(int level, int& outW, int& outH) {
    // O nivel inteiro e' devolvido: o buffer composto todo em dia. O nivel 0 e' o buffer de exibicao
    // inteiro: o resolve (aplica o perfil de cor) por completo.
    ensureAllFresh();
    if (level <= 0) (void)getDisplayRawPixelData();
    return refreshLodLevel(level, outW, outH);
}

uint8_t* PaintEngineFacade::refreshLodLevel(int level, int& outW, int& outH) {
    // O que o compositor escreveu desde a ultima leitura e' o que a piramide refaz. Ate
    // 2026-10-01 isto olhava as bandeiras de tile sujo da camada ativa, que ninguem
    // limpava: depois do primeiro traco a piramide inteira era refeita a cada leitura,
    // mesmo sem mudanca nenhuma (D18).
    const canvas::DamageRect damage = m_compositor.takeDamage();
    m_mipmapPyramid.markDirtyRegion(damage.x0(), damage.y0(), damage.x1(), damage.y1());
    // Build from the same buffer returned to the display.  With the default sRGB profile that is
    // the output buffer itself.  With another profile it is the converted copy, and the pyramid
    // reads it only where it is about to rebuild: convert exactly that region (the whole canvas
    // the first time, after a profile or size change, and the damaged rectangle after that).
    // Converting the whole canvas on every read cost 390 ms at 4K.
    if (m_colorProfileId == 0) return m_mipmapPyramid.getLODData(level, m_outputBuffer, outW, outH);
    if (level > 0) {
        orchestrator::RasterExportOrchestrator::ensureDisplayBuffer(m_outputBuffer, m_displayBuffer);
        const canvas::DamageRect pending = m_mipmapPyramid.pendingRegion(level, m_displayBuffer);
        orchestrator::RasterExportOrchestrator::convertDisplayRegion(
            m_colorProfileId, m_outputBuffer, m_displayBuffer, pending.x0(), pending.y0(), pending.x1(), pending.y1());
    }
    return m_mipmapPyramid.getLODData(level, m_displayBuffer, outW, outH);
}

void PaintEngineFacade::copyDisplayLodRegion(int level, int x, int y, int w, int h, uint8_t* dst, size_t dstSize) {
    if (level < 1 || level > canvas::MipmapPyramid::MAX_LOD_LEVELS) {
        throw std::invalid_argument("LOD level must be between 1 and the number of pyramid levels");
    }
    // O retangulo do nivel cobre [x * 2^level, (x + w) * 2^level) do buffer composto: so isso precisa estar em dia
    // (cada pixel do nivel e' a media dos pixels do nivel 0 que ele cobre; tiles velhos fora dali podem ficar).
    if (w > 0 && h > 0) {
        const auto toBase = [level](int origin, int extent, int limit) {
            const long long first = std::max<long long>(0, static_cast<long long>(origin) << level);
            const long long last = std::min<long long>(limit, (static_cast<long long>(origin) + extent) << level);
            return std::pair<double, double>{static_cast<double>(first), static_cast<double>(std::max(first, last) - first)};
        };
        const auto [bx, bw] = toBase(x, w, m_width);
        const auto [by, bh] = toBase(y, h, m_height);
        m_compositor.ensureFresh(m_layerStack.getAllLayersForComposition(), utils::Rect2D{bx, by, bw, bh},
                                 m_outputBuffer, m_canvasTexture.backgroundColor);
    }
    int levelW = 0, levelH = 0;
    const uint8_t* data = refreshLodLevel(level, levelW, levelH);
    orchestrator::RasterExportOrchestrator::copyBufferRegion(data, levelW, levelH, x, y, w, h, dst, dstSize);
}

void PaintEngineFacade::getLodSize(int level, int& outW, int& outH) const noexcept {
    canvas::MipmapPyramid::levelSize(std::clamp(level, 0, canvas::MipmapPyramid::MAX_LOD_LEVELS), m_width, m_height, outW, outH);
}

} // namespace aladyn::engine::boundary
