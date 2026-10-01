#ifndef ALADYN_ENGINE_PIXEL_PERMISSION_HPP
#define ALADYN_ENGINE_PIXEL_PERMISSION_HPP

#include "PixelContext.hpp"
#include "../canvas/TileGrid.hpp"
#include "../document/Layer.hpp"

namespace aladyn::engine::raster {

// O quanto a seleção e a camada-base de uma máscara de recorte deixam um pixel ser pintado.
//
// Os nove motores repetiam este bloco (a seleção zera ou atenua; o recorte só deixa pintar onde a
// camada de baixo tem alfa e na proporção dele). Alpha Lock é outra regra, que cada motor aplica
// do seu jeito ao compor, e não passa por aqui.
class PixelPermission {
public:
    explicit PixelPermission(const PixelContext& context) noexcept
        : m_selection((context.selectionMask && context.selectionMask->hasSelection()) ? context.selectionMask : nullptr),
          m_clipBase(context.clipBaseLayer) {}

    // Multiplica `strength` pela seleção e pelo alfa da camada-base. false: o pixel não pode ser
    // pintado (fora da seleção, ou sem camada-base embaixo).
    [[nodiscard]] bool apply(int globalX, int globalY, double& strength) const {
        if (m_selection) {
            const uint8_t selected = m_selection->getValue(globalX, globalY);
            if (selected == 0) return false;
            if (selected < 255) strength *= static_cast<double>(selected) / 255.0;
        }
        if (m_clipBase) {
            const canvas::Tile* baseTile = const_cast<canvas::TileGrid&>(m_clipBase->getTileGrid())
                .getTile(globalX / canvas::Tile::TILE_SIZE, globalY / canvas::Tile::TILE_SIZE);
            if (!baseTile) return false;
            const double baseAlpha = static_cast<double>(baseTile->getBuffer().getPixel(
                globalX % canvas::Tile::TILE_SIZE, globalY % canvas::Tile::TILE_SIZE).a) / 255.0;
            if (baseAlpha <= 0.0) return false;
            strength *= baseAlpha;
        }
        return true;
    }

private:
    const selection::SelectionMask* m_selection;
    const document::Layer* m_clipBase;
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_PIXEL_PERMISSION_HPP
