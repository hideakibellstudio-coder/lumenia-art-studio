# `engine/core/canvas/` — armazenamento de pixels

**Responsabilidade:** onde os pixels moram: tiles com cópia-na-escrita e compressão, a grade de tiles de cada camada, o recorte espacial, as pirâmides de mipmap e a textura do papel.

## Porta de entrada

`TileGrid.hpp` (grade de uma camada).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `CanvasLimits.hpp` | O maior lado de canvas por formato de pixel (`kMaxCanvasDimension`, 16384 em 8 bits; `kMaxCanvasDimensionRgba16`, 8192 em 16: o buffer composto de 16384² teria 2³¹ bytes) e `checkedCanvasDimension`, que recusa com `std::invalid_argument` antes de alocar. A interface pergunta o valor ao motor e não o repete. |
| `CanvasTexture.hpp` | Textura do papel aplicada à pintura (relevo, escala, contraste). |
| `DamageRect.hpp` | A união dos pixels que mudaram desde a última leitura (um retângulo ou vazio): o compositor soma o que escreve, a pirâmide de LOD lê, refaz só isso e limpa. Errar para mais custa trabalho; errar para menos mostraria pixel velho. Só o cabeçalho. |
| `MipmapPyramid.hpp` | Níveis 1/2, 1/4, 1/8 de um buffer para exibição com zoom afastado; refaz só a região avisada por `markDirtyRegion` e tudo se avisada por `markDirty` (declaração). |
| `MipmapPyramid.cpp` | Reconstrução dos níveis: inteira (tamanho novo, cor de tela nova) ou só a região danificada, nível a nível. |
| `PixelBuffer.hpp` | Buffer RGBA contíguo em 8 ou 16 bits por canal (`getFormat()`): preencher (um pixel e cópias que dobram, ou memset), limpar, redimensionar, mudar de formato (`reformat`), devolver a memória (`release`). `setPixel`/`getPixel` são a visão de 8 bits (num buffer de 16 bits alargam e estreitam), `setPixel16`/`getPixel16` a de 16. Aloca sem zerar: o `fill` escreve cada byte, e o zero do `std::vector` era uma passada a mais sobre 1 GiB num canvas de 16384². |
| `PixelFormat.hpp` | O formato de pixel de um documento (`RGBA8`, o padrão, ou `RGBA16`), os bytes por pixel e a conversão: 8→16 por ×257 e 16→8 pelo inteiro mais próximo, identidade em 8 bits. `PixelTraits` dá ao código genérico o canal e o fundo de escala de cada tipo de pixel. |
| `SpatialCuller.hpp` | Quais tiles um retângulo cruza (declaração). |
| `SpatialCuller.cpp` | Implementação do recorte espacial. |
| `Tile.hpp` | Um tile no formato do documento (`bytesFor(formato)`: 64 KiB em 8 bits, 128 KiB em 16): pixels com COW e compressão sob demanda; `view(scratch)` lê sem mudar o tile (um tile comprimido continua comprimido; o `scratch` se ajusta ao formato); `zeroTileData()` é o tile de zeros do "antes" de um tile que não existia (declaração). |
| `Tile.cpp` | Descompressão, cópia única (`ensureUnique`) e a leitura que não descomprime de vez (`view`, `isEmpty`: vazio é alfa 0 no canal de 16 bits, e alfa 1 não é vazio mesmo estreitando para 0). |
| `TileGridCodec.hpp` | O bloco de bytes de uma camada para o arquivo `.lmn` v3: só os tiles com pixel visível, cada um em LZ4 (ou cru); o campo que era reservado (0) é o formato de pixel, e 0 é RGBA8, então o bloco de 8 bits tem os mesmos bytes de antes e um build antigo recusa o de 16. `encode` lê uma grade (de um instantâneo, de outra thread); `decode` valida tudo antes de trocar a grade e recusa o malformado inteiro (declaração e formato). |
| `TileGridCodec.cpp` | Implementação: duas passadas no `decode` (estrutura, depois descompressão numa grade própria) para nunca deixar a camada pela metade. |
| `TileGrid.hpp` | Grade de tiles de uma camada, todos no formato dela (`getFormat()`; `copyFrom` adota o da origem): obter/criar/adotar (recusa buffer de outro formato), redimensionar preservando, podar vazios, comprimir inativos. |
| `TileGrid.cpp` | Implementação da grade. `resizePreserve` trabalha por tile: o que cabe inteiro no mesmo lugar é movido (mantém buffer compartilhado ou comprimido), o resto copia por linhas só a parte que cabe e só aloca tile com pixel que não seja transparente-preto (um tile movido que já era só transparente-preto continua alocado; `pruneEmptyTiles` é quem os poda). |

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
