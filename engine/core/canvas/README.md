# `engine/core/canvas/` — armazenamento de pixels

**Responsabilidade:** onde os pixels moram: tiles com cópia-na-escrita e compressão, a grade de tiles de cada camada, o histórico por tile, a paginação em disco e as pirâmides de mipmap.

## Porta de entrada

`TileGrid.hpp` (grade de uma camada); histórico em `TileUndoManager.hpp`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `CanvasTexture.hpp` | Textura do papel aplicada à pintura (relevo, escala, contraste). |
| `MipmapPyramid.hpp` | Níveis 1/2, 1/4, 1/8 de um buffer para exibição com zoom afastado (declaração). |
| `MipmapPyramid.cpp` | Reconstrução dos níveis quando o buffer base muda. |
| `PixelBuffer.hpp` | Buffer RGBA contíguo (preencher, limpar). |
| `ScratchDiskManager.hpp` | Arquivo de rascunho em disco para paginar blocos do histórico (declaração). |
| `ScratchDiskManager.cpp` | Gravação/leitura de blocos com checksum e purga. |
| `SpatialCuller.hpp` | Quais tiles um retângulo cruza (declaração). |
| `SpatialCuller.cpp` | Implementação do recorte espacial. |
| `Tile.hpp` | Um tile: pixels com COW e compressão sob demanda (declaração). |
| `Tile.cpp` | Descompressão e cópia única (`ensureUnique`). |
| `TileGrid.hpp` | Grade de tiles de uma camada: obter/criar, redimensionar preservando, podar vazios, comprimir inativos. |
| `TileGrid.cpp` | Implementação da grade. |
| `TileHistoryRestore.cpp` | Restauração de tiles a partir do histórico, alocando tudo antes de publicar o estado. |
| `TileUndoManager.hpp` | Histórico por tile: passos, estruturas (camadas), limites de memória e paginação em disco. |
| `TileUndoManager.cpp` | Implementação do histórico. |

## Regras

- Lei do rio nº 5: pixel que não está num `TileGrid` não é salvo nem desfeito.
- Alteração de pixel passa por `TileUndoManager::recordTileBefore` antes de escrever.

## Dívida conhecida (medida em 2026-09-24)

Ciclos de pasta: `TileUndoManager.hpp` inclui `document/LayerStack.hpp` e `raster/SelectionMask.hpp`, enquanto `document/` e `raster/` incluem esta pasta. `PixelBuffer.hpp` e `CanvasTexture.hpp` dependem de `raster/Dab.hpp` só pelo tipo de cor.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/compression`
- `engine/core/document`
- `engine/core/math`
- `engine/core/raster`
- `engine/core/texture`
<!-- /arccc:deps -->
