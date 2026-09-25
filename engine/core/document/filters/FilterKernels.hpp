#ifndef ALADYN_ENGINE_FILTER_KERNELS_HPP
#define ALADYN_ENGINE_FILTER_KERNELS_HPP

// Cabecalho INTERNO da decomposicao do FilterApplier. Nao faz parte do contrato
// publico: o unico ponto de entrada continua sendo FilterApplier::apply, chamado
// por Compositor.cpp e CompositeRegionSupport.cpp com FilterLayer::settings().
//
// Motivo da decomposicao: FilterApplier.cpp tinha 431 linhas (19 do teto ARCcC
// de 450) e concentrava 22 dos 52 sitios de aritmetica `* 4` do motor. As duas
// coisas tem a mesma causa — os sete filtros repetiam acesso cru a pixel por
// falta de uma camada para chamar.
//
// FilterRegion e essa camada. Hoje ela carrega o ponteiro cru, exatamente como
// antes; quando o pipeline migrar para RGBA16/RGBA32F (ver
// docs/COLOR_PIPELINE_ARCHITECTURE.md secao 4), ela e o UNICO lugar onde o
// formato precisa ser decidido, em vez de sete.

#include "FilterSettings.hpp"
#include "../../canvas/PixelBuffer.hpp"

#include <cstdint>

namespace aladyn::engine::document::filters {

/// Recorte de buffer ja validado, compartilhado pelos sete nucleos de filtro.
struct FilterRegion {
    uint8_t* ptr{nullptr};
    int w{0};
    int h{0};
    int startX{0};
    int endX{0};
    int startY{0};
    int endY{0};
    double opacity{1.0};
    bool isFullOpacity{true};
};

// Filtros ponto-a-ponto: cada pixel depende apenas de si mesmo.
void applyBrightnessContrast(const FilterSettings& filter, const FilterRegion& region);
void applyColorBalance(const FilterSettings& filter, const FilterRegion& region);
void applyInvertThreshold(const FilterSettings& filter, const FilterRegion& region);
void applyHueSat(const FilterSettings& filter, const FilterRegion& region);

// Filtros de area: cada pixel depende da vizinhanca, exigindo buffer auxiliar.
void applyPixelate(const FilterSettings& filter, const FilterRegion& region);
void applyGaussianBlur(const FilterSettings& filter, const FilterRegion& region);
void applySharpenVignette(const FilterSettings& filter, const FilterRegion& region);

} // namespace aladyn::engine::document::filters

#endif // ALADYN_ENGINE_FILTER_KERNELS_HPP
