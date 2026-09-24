# `engine/core/document/blending/filters/` — núcleos de filtro

**Responsabilidade:** os algoritmos de cada filtro de camada de ajuste, separados em filtros ponto a ponto e filtros de área.

## Porta de entrada

`FilterKernels.hpp` — cabeçalho interno; o contrato público continua sendo `FilterApplier::apply`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `FilterKernels.hpp` | Declaração dos núcleos e da `FilterRegion`. |
| `PointFilters.cpp` | Ponto a ponto: brilho/contraste, balanço de cor, inverter/limiar, matiz/saturação. |
| `AreaFilters.cpp` | Por vizinhança: pixelizar, desfoque gaussiano, nitidez/vinheta. |

## Regras

- Só `../FilterApplier.cpp` inclui esta pasta.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
- `engine/core/document`
- `engine/core/document/blending`
<!-- /arccc:deps -->
