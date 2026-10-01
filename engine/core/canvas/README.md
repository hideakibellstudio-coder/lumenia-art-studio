# `engine/core/canvas/` — armazenamento de pixels

**Responsabilidade:** onde os pixels moram: tiles com cópia-na-escrita e compressão, a grade de tiles de cada camada, o recorte espacial, as pirâmides de mipmap e a textura do papel.

## Porta de entrada

`TileGrid.hpp` (grade de uma camada).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `CanvasLimits.hpp` | O maior lado de canvas (`kMaxCanvasDimension`, 16384) e `checkedCanvasDimension`, que recusa com `std::invalid_argument` antes de alocar. A interface pergunta o valor ao motor e não o repete. |
| `CanvasTexture.hpp` | Textura do papel aplicada à pintura (relevo, escala, contraste). |
| `DamageRect.hpp` | A união dos pixels que mudaram desde a última leitura (um retângulo ou vazio): o compositor soma o que escreve, a pirâmide de LOD lê, refaz só isso e limpa. Errar para mais custa trabalho; errar para menos mostraria pixel velho. Só o cabeçalho. |
| `GridSnapshot.hpp` | Foto de um retângulo da `TileGrid` tirada antes de escrever. O pincel que lê o que ele mesmo pinta (Borrar) lê dela e não da grade viva, e o resultado deixa de depender da ordem em que os tiles são varridos. Só o cabeçalho. |
| `MipmapPyramid.hpp` | Níveis 1/2, 1/4, 1/8 de um buffer para exibição com zoom afastado; refaz só a região avisada por `markDirtyRegion` e tudo se avisada por `markDirty` (declaração). |
| `MipmapPyramid.cpp` | Reconstrução dos níveis: inteira (tamanho novo, cor de tela nova) ou só a região danificada, nível a nível. |
| `PixelBuffer.hpp` | Buffer RGBA contíguo (preencher, limpar). |
| `SpatialCuller.hpp` | Quais tiles um retângulo cruza (declaração). |
| `SpatialCuller.cpp` | Implementação do recorte espacial. |
| `Tile.hpp` | Um tile: pixels com COW e compressão sob demanda (declaração). |
| `Tile.cpp` | Descompressão e cópia única (`ensureUnique`). |
| `TileGrid.hpp` | Grade de tiles de uma camada: obter/criar, redimensionar preservando, podar vazios, comprimir inativos. |
| `TileGrid.cpp` | Implementação da grade. |

## Regras

- Lei do rio nº 5: pixel que não está num `TileGrid` não é salvo nem desfeito.
- Não conhece camadas nem histórico: o histórico (`engine/core/history`) é que registra tiles daqui. Saíram em 2026-09-25 o `TileUndoManager` (para `history/`) e o disco de rascunho (para `engine/infrastructure/storage`), que criavam os ciclos `canvas` ↔ `document` e `canvas` ↔ `raster`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/math`
- `engine/core/texture`
- `engine/infrastructure/compression`
- `engine/utils`
<!-- /arccc:deps -->
