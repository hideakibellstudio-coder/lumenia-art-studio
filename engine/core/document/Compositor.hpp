#ifndef ALADYN_ENGINE_COMPOSITOR_HPP
#define ALADYN_ENGINE_COMPOSITOR_HPP

#include "Layer.hpp"
#include "../canvas/DamageRect.hpp"
#include "../canvas/PixelBuffer.hpp"
#include "../canvas/TileGrid.hpp"
#include "projection/CompositeProjection.hpp"
#include <vector>
#include <memory>

namespace aladyn::engine::document {

class FilterLayer;

namespace internal {
struct CompositePolicy;
struct ScratchOverlay;
} // namespace internal

class Compositor {
public:
    // `format` é o formato de pixel das camadas que ele compõe (o do documento). Num documento de 16 bits a pilha é
    // composta num buffer interno de 16 bits (`composite16`), e o buffer de saída que quem chama passa (sempre de
    // 8 bits: a tela, a pirâmide, os leitores) recebe esse resultado estreitado ao inteiro mais próximo.
    Compositor(int width, int height, canvas::PixelFormat format = canvas::PixelFormat::RGBA8);

    [[nodiscard]] canvas::PixelFormat getPixelFormat() const noexcept { return m_format; }

    // O buffer composto de 16 bits (a resolução inteira, sem estreitar), ou nullptr num documento de 8 bits ou
    // antes da primeira composição. Só vale nos pixels que estão frescos: quem lê chama `ensureFresh` antes
    // (`PaintEngineFacade::getRawPixelData()` fresca o canvas inteiro).
    [[nodiscard]] const canvas::PixelBuffer* composite16() const noexcept { return m_composite16.get(); }

    static utils::ColorRGBA blendPixel(utils::ColorRGBA src, double layerOpacity, utils::ColorRGBA dst, LayerBlendMode mode);
    static utils::ColorRGBA blendPixel(utils::ColorRGBA src, double layerOpacity, utils::ColorRGBA dst, LayerBlendMode mode, bool linearGamma, bool deepColor);
    static void applyFilterToBuffer(const FilterLayer& filter, canvas::PixelBuffer& buffer, int minX = 0, int maxX = -1, int minY = 0, int maxY = -1);

    // Opções do pipeline são propriedades do compositor, e não apenas
    // preferências da interface. A composição seguinte já usa os valores.
    void setLinearGamma(bool enabled) noexcept { m_linearGamma = enabled; }
    [[nodiscard]] bool isLinearGamma() const noexcept { return m_linearGamma; }
    void setDeepColor(bool enabled) noexcept { m_deepColor = enabled; }
    [[nodiscard]] bool isDeepColor() const noexcept { return m_deepColor; }

    void composite(const std::vector<const Layer*>& layers, canvas::PixelBuffer& outputBuffer, const utils::ColorRGBA& bgColor = {255, 255, 255, 255});
    void composite(const std::vector<std::unique_ptr<Layer>>& layers, canvas::PixelBuffer& outputBuffer, const utils::ColorRGBA& bgColor = {255, 255, 255, 255});

    void compositeRegion(const std::vector<const Layer*>& layers, const utils::Rect2D& region, canvas::PixelBuffer& outputBuffer, const utils::ColorRGBA& bgColor = {255, 255, 255, 255});
    void compositeRegion(const std::vector<std::unique_ptr<Layer>>& layers, const utils::Rect2D& region, canvas::PixelBuffer& outputBuffer, const utils::ColorRGBA& bgColor = {255, 255, 255, 255});

    // Sobrecarga com scratch layer: durante um traço ativo, insere o scratchGrid
    // como overlay imediatamente acima da camada ativa correspondente (activeLayerTarget),
    // usando o blendMode e opacity configurados. A camada ativa original é composta
    // normalmente (conteúdo pré-existente) e o scratch aparece sobre ela.
    void compositeRegionWithScratch(
        const std::vector<const Layer*>& layers,
        const utils::Rect2D& region,
        canvas::PixelBuffer& outputBuffer,
        const utils::ColorRGBA& bgColor,
        const canvas::TileGrid& scratchGrid,
        const Layer* activeLayerTarget,
        LayerBlendMode scratchBlendMode,
        double scratchOpacity
    );

    // ─── Projeção: o que do buffer de saída está velho (document/projection/) ───
    // `invalidate` marca como velho, sem compor, o que `compositeRegion(layers, region)` escreveria (a
    // região mais o alcance dos filtros de área); `invalidateAll` marca o canvas inteiro. Quem lê pixels do
    // buffer de saída chama `ensureFresh` na área que vai ler: só os tiles velhos que ela toca são compostos.
    // As composições por região (traço, colagem, transformação, balde) deixam frescos os tiles que cobrem
    // inteiros, e refazem inteiros os tiles velhos que tocam (o overlay do traço nunca fica pela metade).
    void invalidate(const std::vector<const Layer*>& layers, const utils::Rect2D& region);
    void invalidateAll() noexcept { m_projection.markAllStale(); }
    void ensureFresh(
        const std::vector<const Layer*>& layers,
        const utils::Rect2D& region,
        canvas::PixelBuffer& outputBuffer,
        const utils::ColorRGBA& bgColor = {255, 255, 255, 255}
    );
    // O canvas inteiro: para quem lê o buffer todo (exportação, balde e varinha sobre todas as camadas).
    void ensureAllFresh(
        const std::vector<const Layer*>& layers,
        canvas::PixelBuffer& outputBuffer,
        const utils::ColorRGBA& bgColor = {255, 255, 255, 255}
    ) {
        ensureFresh(layers, utils::Rect2D{0, 0, static_cast<double>(m_width), static_cast<double>(m_height)}, outputBuffer, bgColor);
    }
    [[nodiscard]] size_t staleTileCount() const noexcept { return m_projection.staleTileCount(); }

    // Os pixels do buffer de saída que mudaram desde a última chamada. Toda escrita no
    // buffer de saída passa por uma das funções acima, então este é o único lugar que
    // sabe o que mudou: a pirâmide de LOD refaz só isso (D18). Devolve e zera.
    [[nodiscard]] canvas::DamageRect takeDamage() noexcept {
        const canvas::DamageRect damage = m_damage;
        m_damage.clear();
        return damage;
    }

private:
    void compositeLayers(
        const std::vector<const Layer*>& layers,
        const utils::Rect2D& region,
        canvas::PixelBuffer& outputBuffer,
        const utils::ColorRGBA& bgColor,
        const internal::CompositePolicy& policy,
        const internal::ScratchOverlay* scratch
    );

    int m_width{0};
    int m_height{0};
    canvas::PixelFormat m_format{canvas::PixelFormat::RGBA8};
    std::unique_ptr<canvas::PixelBuffer> m_composite16;  // alocado na primeira composição de um documento de 16 bits
    canvas::DamageRect m_damage;
    projection::CompositeProjection m_projection;
    // Mantém o comportamento histórico (mistura linear) para facades
    // construídas diretamente; a camada de configuração aplica o perfil
    // escolhido pelo usuário assim que cria o contexto do documento.
    bool m_linearGamma{true};
    bool m_deepColor{false};
};

} // namespace aladyn::engine::document

#endif // ALADYN_ENGINE_COMPOSITOR_HPP
