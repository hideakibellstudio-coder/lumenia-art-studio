# `engine/core/document/` — documento e camadas

**Responsabilidade:** a estrutura de camadas do documento (camada, grupo, camada de ajuste), a pilha com o papel na camada 0, mesclar e achatar, e o compositor que junta tudo num buffer.

## Porta de entrada

`LayerStack.hpp` (pilha) e `Compositor.hpp` (composição).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `Compositor.hpp` | Compositor: modos de mesclagem, filtros, opções do pipeline (declaração). |
| `Compositor.cpp` | Composição total e por região, delegando limites e grupos a `CompositeRegionSupport`. |
| `CompositeRegionSupport.hpp` | Parte privada do compositor (namespace `document::internal`): alcance dos filtros, base de recorte, fundo, grupos isolados (declaração). |
| `CompositeRegionSupport.cpp` | Implementação; veio da antiga subpasta `internal/`, que incluía esta pasta (ciclo). |
| `FilterLayer.hpp` | Camada de ajuste: tipo de filtro, parâmetros e `settings()` para `filters/` (declaração). |
| `FilterLayer.cpp` | Valores padrão de cada filtro. |
| `Layer.hpp` | Camada raster: nó + `TileGrid` + compressão de tiles inativos. |
| `LayerMerger.hpp` | Achatar grupo e mesclar para baixo (declaração). |
| `LayerMerger.cpp` | Implementação, reassociando pais e validando índices. |
| `LayerNode.hpp` | Nó comum da árvore de camadas: tipo, modo de mesclagem, opacidade, visibilidade, travas, recorte. |
| `LayerStack.hpp` | Pilha de camadas (camada 0 = papel): adicionar, remover, redimensionar, restaurar (declaração). |
| `LayerStack.cpp` | Implementação; aloca tudo antes de mexer na pilha viva. |

| Pasta | Responsabilidade |
|---|---|
| `blending/` | Equações de mesclagem de pixel e o enum `LayerBlendMode`. |
| `filters/` | Filtros das camadas de ajuste (`FilterApplier`, `FilterType`, núcleos). |

## Regras

- A árvore de camadas do motor espelha o `LocalLayerManager` da UI; quem sincroniza é `ui/core/document/layer_backend_sync.py` (escritor único).
- As subpastas não incluem esta pasta: os enums que as duas lados usam moram nelas (`blending/LayerBlendMode.hpp`, `filters/FilterSettings.hpp`) e o documento os reexporta como `document::LayerBlendMode` e `document::FilterType`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
- `engine/core/document/blending`
- `engine/core/document/filters`
- `engine/utils`
<!-- /arccc:deps -->
