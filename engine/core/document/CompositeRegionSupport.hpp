#ifndef ALADYN_ENGINE_DOCUMENT_INTERNAL_COMPOSITE_REGION_SUPPORT_HPP
#define ALADYN_ENGINE_DOCUMENT_INTERNAL_COMPOSITE_REGION_SUPPORT_HPP

#include "Layer.hpp"
#include "FilterLayer.hpp"
#include "../canvas/PixelBuffer.hpp"
#include "../canvas/TileGrid.hpp"
#include "../../utils/Rect2D.hpp"
#include <cstdint>
#include <vector>

namespace aladyn::engine::document::internal {

// Extraido de Compositor::compositeRegion / compositeRegionWithScratch
// (Zona Vermelha ARCcC, 544 LOC) para eliminar a duplicacao byte a byte do
// bloco de isolamento de grupo entre as duas sobrecargas. Nenhuma linha de
// logica foi alterada nesta extracao — apenas movida — e as duas divergencias
// de comportamento pre-existentes entre as sobrecargas (alinhamento de bloco
// de pixelize e o limiar de paralelizacao do preenchimento de fundo) foram
// preservadas como parametros explicitos em vez de unificadas.

// Alcance espacial (em pixels) que um filtro pode "vazar" para fora da regiao
// suja nominal antes de compor (usado para inflar a regiao efetiva).
int filterSpatialReach(const FilterLayer& filter);

const Layer* resolveClipBase(const Layer& layer);
const Layer* getIsolatedGroupAncestor(const LayerNode* node);
double getRelativeOpacity(const LayerNode* node, const LayerNode* isolatedAncestor);

struct BackgroundAndReach {
    utils::ColorRGBA bgFill{0, 0, 0, 0};
    int totalReach{0};
    int maxBlockSize{0};
};

// Determina a cor de fundo efetiva (so visivel se alguma camada de fundo
// estiver visivel) e o alcance espacial total somado de todos os filtros
// visiveis, mais o maior bloco de pixelize (usado para o alinhamento opcional
// de regiao).
BackgroundAndReach computeBackgroundAndReach(
    const std::vector<const Layer*>& layers,
    const utils::ColorRGBA& bgColor
);

struct RegionBounds {
    int minX{0};
    int maxX{-1};
    int minY{0};
    int maxY{-1};
    int regW{0};
    int regH{0};
    int startTileX{0};
    int endTileX{-1};
    int startTileY{0};
    int endTileY{-1};
    bool empty{true};
};

// Calcula os limites inteiros finais (ja recortados ao canvas) da regiao a
// compor, a partir da regiao logica solicitada inflada pelo alcance de
// filtros. `snapToBlockSize` preserva o comportamento historico de
// `compositeRegion` (alinha minX/minY/maxX/maxY ao maior bloco de pixelize
// ativo); `compositeRegionWithScratch` sempre passa false, como fazia antes
// desta extracao.
RegionBounds computeRegionBounds(
    const utils::Rect2D& region,
    int totalReach,
    int maxBlockSize,
    int canvasWidth,
    int canvasHeight,
    bool snapToBlockSize
);

// Preenche outputBuffer com bgFill dentro de bounds, com fast-path de memset
// quando a regiao cobre o canvas inteiro e a cor e transparente.
// `parallelRowThreshold` preserva o limiar de `#pragma omp` historico de cada
// chamador (256 em compositeRegion, 64 em compositeRegionWithScratch).
void fillBackground(
    canvas::PixelBuffer& outputBuffer,
    const RegionBounds& bounds,
    const utils::ColorRGBA& bgFill,
    int canvasWidth,
    int canvasHeight,
    int parallelRowThreshold
);

// Concentra o par blendGroupToDestination/composeTileGrid que
// compositeRegion e compositeRegionWithScratch duplicavam: compoe tiles de
// camada para o buffer de saida ou para o acumulador de um grupo isolado, e
// funde esse acumulador contra o destino quando o grupo fecha.
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
    uint32_t* m_outData32;
    int m_outStride;
    std::vector<uint32_t> m_groupPixels;
};

} // namespace aladyn::engine::document::internal

#endif // ALADYN_ENGINE_DOCUMENT_INTERNAL_COMPOSITE_REGION_SUPPORT_HPP
