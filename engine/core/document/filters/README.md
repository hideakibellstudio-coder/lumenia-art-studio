# `engine/core/document/filters/` — filtros de camada de ajuste

**Responsabilidade:** aplicar o filtro de uma camada de ajuste a um buffer: o ponto de entrada, o contrato de configuração e os núcleos de cada filtro (ponto a ponto e de área).

## Porta de entrada

`FilterApplier.hpp` (`FilterApplier::apply(FilterSettings, PixelBuffer, ...)`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `FilterSettings.hpp` | Enum `FilterType` e `FilterSettings` (tipo, parâmetros, opacidade): o que o filtro precisa da camada. |
| `FilterApplier.hpp` | Ponto único de entrada dos filtros (declaração). |
| `FilterApplier.cpp` | Recorta a região e despacha para o núcleo do `FilterType`. |
| `FilterKernels.hpp` | Cabeçalho interno: declaração dos núcleos e da `FilterRegion`. |
| `PointFilters.cpp` | Ponto a ponto: brilho/contraste, balanço de cor, inverter/limiar, matiz/saturação. |
| `AreaFilters.cpp` | Por vizinhança: pixelizar, desfoque gaussiano, nitidez/vinheta. |

## Regras

- Não conhece `FilterLayer` (pasta-mãe): recebe `FilterSettings`, montado por `FilterLayer::settings()`.
- Filtro novo: valor em `FilterType`, núcleo em `PointFilters.cpp` ou `AreaFilters.cpp`, caso em `FilterApplier::apply`, padrão em `../FilterLayer.cpp`.
- Veio de `blending/filters/` em 2026-09-25: filtro não é mesclagem, e a subpasta incluía as duas pastas acima dela.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
- `engine/core/color`
<!-- /arccc:deps -->
