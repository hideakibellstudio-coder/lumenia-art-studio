# `engine/core/document/` — documento e camadas

**Responsabilidade:** a estrutura de camadas do documento (camada, grupo, camada de ajuste), a pilha com o papel na camada 0, mesclar e achatar, e o compositor que junta tudo num buffer.

## Porta de entrada

`LayerStack.hpp` (pilha) e `Compositor.hpp` (composição).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `Compositor.hpp` | Compositor: modos de mesclagem, filtros, opções do pipeline (declaração). |
| `Compositor.cpp` | Composição total e por região, delegando limites e grupos a `internal/`. |
| `FilterLayer.hpp` | Camada de ajuste: tipo de filtro (`FilterType`) e parâmetros (declaração). |
| `FilterLayer.cpp` | Valores padrão de cada filtro. |
| `Layer.hpp` | Camada raster: nó + `TileGrid` + compressão de tiles inativos. |
| `LayerMerger.hpp` | Achatar grupo e mesclar para baixo (declaração). |
| `LayerMerger.cpp` | Implementação, reassociando pais e validando índices. |
| `LayerNode.hpp` | Nó comum da árvore de camadas: tipo, modo de mesclagem, opacidade, visibilidade, travas, recorte. |
| `LayerStack.hpp` | Pilha de camadas (camada 0 = papel): adicionar, remover, redimensionar, restaurar (declaração). |
| `LayerStack.cpp` | Implementação; aloca tudo antes de mexer na pilha viva. |

## Regras

- A árvore de camadas do motor espelha o `LocalLayerManager` da UI; quem sincroniza é `ui/core/document/layer_backend_sync.py` (escritor único).

## Dívida conhecida (medida em 2026-09-24)

Ciclo `document` ↔ `canvas` (`canvas/TileUndoManager.hpp` inclui `LayerStack.hpp`) e com as próprias subpastas `blending/` e `internal/`, que incluem arquivos desta pasta.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
- `engine/core/document/blending`
- `engine/core/document/internal`
<!-- /arccc:deps -->
