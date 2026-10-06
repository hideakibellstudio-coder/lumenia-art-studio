#ifndef ALADYN_ENGINE_DOCUMENT_INTERNAL_GROUP_BLENDER_HPP
#define ALADYN_ENGINE_DOCUMENT_INTERNAL_GROUP_BLENDER_HPP

#include "CompositeRegionSupport.hpp"
#include "FilterLayer.hpp"
#include "Layer.hpp"
#include "../canvas/PixelBuffer.hpp"
#include "../canvas/TileGrid.hpp"
#include "../../utils/ColorRGBA.hpp"
#include "../../utils/ColorRGBA16.hpp"
#include <vector>

namespace aladyn::engine::document::internal {

// Concentra o par blendGroupToDestination/composeTileGrid que
// compositeRegion e compositeRegionWithScratch duplicavam: compoe tiles de
// camada para o buffer de saida ou para o acumulador de um grupo isolado, e
// funde esse acumulador contra o destino quando o grupo fecha.
//
// `Pixel` e' o pixel do formato do documento (`ColorRGBA` ou `ColorRGBA16`): o buffer de destino, os tiles e o
// acumulador do grupo sao desse formato; uma camada de outro formato e' recusada (`std::logic_error`) antes de
// qualquer escrita. As duas instancias moram em GroupBlender.cpp.
template <typename Pixel>
class GroupBlender {
public:
    GroupBlender(canvas::PixelBuffer& outputBuffer, const RegionBounds& bounds, bool linearGamma, bool deepColor);

    // Reinicia (ou aloca, na primeira vez) o acumulador do grupo isolado que
    // esta comecando.
    void beginGroup();

    // Compoe um tile grid de camada para dentro do buffer de saida
    // (isToGroup == false) ou do acumulador de grupo corrente (true).
    void composeTileGrid(
        const canvas::TileGrid& grid,
        double opacity,
        LayerBlendMode mode,
        const Layer* clipBase,
        const canvas::TileGrid* maskGrid,
        bool isToGroup
    );

    // Aplica um filtro sobre o acumulador de grupo corrente (usado quando uma
    // FilterLayer aparece dentro de um grupo isolado ativo).
    void applyFilterToGroup(const FilterLayer& filter);

    // Funde o acumulador de grupo corrente contra o buffer de saida usando a
    // opacidade/blend mode do proprio grupo, e encerra o grupo.
    void blendGroupToDestination(const Layer* group);

private:
    canvas::PixelBuffer& m_outputBuffer;
    const RegionBounds& m_bounds;
    bool m_linearGamma;
    bool m_deepColor;
    Pixel* m_outData;
    int m_outStride;
    std::vector<Pixel> m_groupPixels;
};

extern template class GroupBlender<utils::ColorRGBA>;
extern template class GroupBlender<utils::ColorRGBA16>;

} // namespace aladyn::engine::document::internal

#endif // ALADYN_ENGINE_DOCUMENT_INTERNAL_GROUP_BLENDER_HPP
