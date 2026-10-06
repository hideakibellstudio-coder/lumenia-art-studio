# `engine/core/document/filters/` — filtros de camada de ajuste

**Responsabilidade:** aplicar o filtro de uma camada de ajuste a um buffer: o ponto de entrada, o contrato de configuração e os núcleos de cada filtro (ponto a ponto e de área).

## Porta de entrada

`FilterApplier.hpp` (`FilterApplier::apply(FilterSettings, PixelBuffer, ...)`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `FilterSettings.hpp` | Enum `FilterType` e `FilterSettings` (tipo, parâmetros, opacidade): o que o filtro precisa da camada. |
| `FilterApplier.hpp` | Ponto único de entrada dos filtros (declaração). |
| `FilterApplier.cpp` | Recorta a região e despacha para o núcleo do `FilterType`, no conjunto de 8 ou de 16 bits conforme o formato do buffer. |
| `FilterKernels.hpp` | Cabeçalho interno: declaração dos núcleos e da `FilterRegion`. |
| `PointFilters.cpp` | Ponto a ponto: brilho/contraste, balanço de cor, inverter/limiar, matiz/saturação. |
| `AreaFilters.cpp` | Por vizinhança: pixelizar, desfoque gaussiano, nitidez/vinheta. |
| `FilterKernels16.hpp` | Cabeçalho interno dos sete núcleos de 16 bits por canal (S5): as mesmas fórmulas e parâmetros dos de 8 bits (unidades de 8 bits, pular o pixel de alfa 0, alfa intocado), mas arredondam em vez de truncar e misturam com a opacidade da camada em 16 bits. |
| `PointFilters16.cpp` | Ponto a ponto em 16 bits: brilho/contraste (tabela de 65536 entradas guardada por thread, para que um traço sob uma camada de ajuste a monte uma vez), balanço de cor, inverter/limiar, matiz/saturação. |
| `AreaFilters16.cpp` | Por vizinhança em 16 bits: pixelizar, desfoque gaussiano, nitidez/vinheta, com a conta em float arredondada ao nível de 16 bits. |

## Regras

- Não conhece `FilterLayer` (pasta-mãe): recebe `FilterSettings`, montado por `FilterLayer::settings()`.
- Filtro novo: valor em `FilterType`, núcleo em `PointFilters.cpp` e `PointFilters16.cpp` (ou nos dois `AreaFilters`), caso em `FilterApplier::apply`, padrão em `../FilterLayer.cpp`. O de 16 bits é testado contra o de 8 bits em entrada idêntica (`tests/native/filter16_checks.cpp`: no máximo 2 níveis de 8 bits, e só no Matiz/Saturação, no Brilho/Contraste e no Desfoque; os outros em 1).
- Veio de `blending/filters/` em 2026-09-25: filtro não é mesclagem, e a subpasta incluía as duas pastas acima dela.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
- `engine/core/color`
- `engine/utils`
<!-- /arccc:deps -->
