# `engine/core/document/blending/` — mesclagem e filtros

**Responsabilidade:** a matemática de mesclar um pixel sobre outro (alpha over e modos) e a aplicação dos filtros das camadas de ajuste.

## Porta de entrada

`BlendEquations.hpp` (mesclagem) e `FilterApplier.hpp` (filtros).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `BlendEquations.hpp` | Conversão RGB ↔ HSV e equações de mesclagem por modo. |
| `FilterApplier.hpp` | Ponto único de entrada dos filtros: `FilterApplier::apply` (declaração). |
| `FilterApplier.cpp` | Despacha para os núcleos de `filters/` conforme o `FilterType`. |

## Regras

- Filtro novo: núcleo em `filters/`, caso em `FilterApplier::apply`, tipo em `../FilterLayer.hpp`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
- `engine/core/color`
- `engine/core/document`
- `engine/core/document/blending/filters`
- `engine/core/raster`
<!-- /arccc:deps -->
