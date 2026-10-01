#ifndef ALADYN_ENGINE_COMPOSITOR_HPP
#define ALADYN_ENGINE_COMPOSITOR_HPP

#include "Layer.hpp"
#include "../canvas/DamageRect.hpp"
#include "../canvas/PixelBuffer.hpp"
#include "../canvas/TileGrid.hpp"
#include <vector>
#include <memory>

namespace aladyn::engine::document {

class FilterLayer;

class Compositor {
public:
    Compositor(int width, int height);

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

    // Os pixels do buffer de saída que mudaram desde a última chamada. Toda escrita no
    // buffer de saída passa por uma das funções acima, então este é o único lugar que
    // sabe o que mudou: a pirâmide de LOD refaz só isso (D18). Devolve e zera.
    [[nodiscard]] canvas::DamageRect takeDamage() noexcept {
        const canvas::DamageRect damage = m_damage;
        m_damage.clear();
        return damage;
    }

private:
    int m_width{0};
    int m_height{0};
    canvas::DamageRect m_damage;
    // Mantém o comportamento histórico (mistura linear) para facades
    // construídas diretamente; a camada de configuração aplica o perfil
    // escolhido pelo usuário assim que cria o contexto do documento.
    bool m_linearGamma{true};
    bool m_deepColor{false};
};

} // namespace aladyn::engine::document

#endif // ALADYN_ENGINE_COMPOSITOR_HPP
