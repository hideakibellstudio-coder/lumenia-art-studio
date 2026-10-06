#ifndef ALADYN_ENGINE_DOCUMENT_INTERNAL_COMPOSITE_REGION_SUPPORT_HPP
#define ALADYN_ENGINE_DOCUMENT_INTERNAL_COMPOSITE_REGION_SUPPORT_HPP

#include "Layer.hpp"
#include "FilterLayer.hpp"
#include "../canvas/Tile.hpp"
#include "../../utils/Rect2D.hpp"
#include <cstdint>
#include <vector>

namespace aladyn::engine::document::internal {

// A geometria de uma composicao por regiao: alcance dos filtros, camada-base de recorte, grupo isolado, fundo e
// limites. Nada aqui le ou escreve pixel; o buffer de saida e' de `RegionBuffer.hpp` e o par grupo/tile de
// `GroupBlender.hpp`. Extraido de Compositor::compositeRegion / compositeRegionWithScratch (Zona Vermelha ARCcC,
// 544 LOC) sem alterar a logica; as duas divergencias de comportamento entre as sobrecargas (alinhamento de bloco de
// pixelize e limiar de paralelizacao do fundo) ficaram como parametros explicitos em vez de unificadas.

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

} // namespace aladyn::engine::document::internal

#endif // ALADYN_ENGINE_DOCUMENT_INTERNAL_COMPOSITE_REGION_SUPPORT_HPP
