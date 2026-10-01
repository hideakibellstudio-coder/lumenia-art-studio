#ifndef ALADYN_ENGINE_DOCUMENT_INTERNAL_LAYER_COMPOSITE_PASS_HPP
#define ALADYN_ENGINE_DOCUMENT_INTERNAL_LAYER_COMPOSITE_PASS_HPP

#include "CompositeRegionSupport.hpp"
#include "FilterLayer.hpp"
#include "Layer.hpp"
#include "../canvas/PixelBuffer.hpp"
#include "../canvas/TileGrid.hpp"

namespace aladyn::engine::document::internal {

// As duas escolhas em que `compositeRegion` e `compositeRegionWithScratch` sempre divergiram
// (ver CompositeRegionSupport.hpp): alinhar a região ao bloco de pixelize e o limiar de
// paralelização do fundo.
struct CompositePolicy {
    bool snapToBlockSize;
    int parallelRowThreshold;
};

// A grade de um traço ativo, composta logo acima da camada `target` com o modo e a opacidade
// do traço.
struct ScratchOverlay {
    const canvas::TileGrid& grid;
    const Layer* target;
    LayerBlendMode mode;
    double opacity;
};

// Uma passada de composição: recebe as camadas de baixo para cima e as compõe no buffer de saída,
// com o estado de grupo isolado e de filtro que a passada carrega de uma camada para a seguinte.
// Antes de 2026-10-01 este laço existia duas vezes, uma em cada sobrecarga do compositor.
class LayerCompositePass {
public:
    LayerCompositePass(canvas::PixelBuffer& outputBuffer, const RegionBounds& bounds, bool linearGamma, bool deepColor);

    // Compõe `layer` (nada se estiver invisível ou sem opacidade). `scratch` é composto logo
    // depois da camada que ele sobrepõe.
    void add(const Layer* layer, const ScratchOverlay* scratch);

    // Fecha o grupo isolado que ainda estiver aberto.
    void finish();

private:
    void enterGroupOf(const Layer* layer);
    void applyFilter(const FilterLayer& filter);
    void composeLayer(const Layer& layer, const ScratchOverlay* scratch);

    canvas::PixelBuffer& m_outputBuffer;
    const RegionBounds& m_bounds;
    GroupBlender m_blender;
    const Layer* m_activeGroup{nullptr};
};

} // namespace aladyn::engine::document::internal

#endif // ALADYN_ENGINE_DOCUMENT_INTERNAL_LAYER_COMPOSITE_PASS_HPP
