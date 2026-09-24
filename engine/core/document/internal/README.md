# `engine/core/document/internal/` — apoio do compositor

**Responsabilidade:** o cálculo compartilhado pelas duas composições por região (limites, fundo, alcance dos filtros, grupos isolados e recorte).

## Porta de entrada

`CompositeRegionSupport.hpp` (usado só por `../Compositor.cpp`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `CompositeRegionSupport.hpp` | Limites da região, fundo e alcance, `GroupBlender` (declaração); extraído do `Compositor` para eliminar código duplicado. |
| `CompositeRegionSupport.cpp` | Implementação. |

## Regras

- Apoio privado do `Compositor`: nenhuma outra pasta inclui daqui.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
- `engine/core/document`
- `engine/core/document/blending`
- `engine/core/math`
<!-- /arccc:deps -->
