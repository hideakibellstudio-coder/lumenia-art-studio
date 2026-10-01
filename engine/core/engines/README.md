# `engine/core/engines/` — mini-motores de pincel

**Responsabilidade:** a física de cada tipo de pincel — como um dab deposita, apaga, borra ou arrasta tinta nos tiles da camada.

## Porta de entrada

`IBrushEngine.hpp` (interface comum); a lista concreta de motores fica em `engine/boundary/orchestrator/BrushEngineFactory.hpp`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `IBrushEngine.hpp` | Interface polimórfica de todo mini-motor. |
| `PencilEngine.hpp` | Lápis/grafite/giz: contato com o micro-relevo do papel (declaração). |
| `PencilEngine.cpp` | Implementação. |
| `InkerEngine.hpp` | Caneta/nanquim/G-pen: fluxo contínuo sobre papel liso (declaração). |
| `InkerEngine.cpp` | Implementação. |
| `MarkerEngine.hpp` | Marcador de álcool: tinta que se funde com passadas anteriores (declaração). |
| `MarkerEngine.cpp` | Implementação. |
| `WatercolorEngine.hpp` | Aquarela: pigmento em água sobre meio poroso (declaração). |
| `WatercolorEngine.cpp` | Implementação (sangramento molhado-no-molhado). |
| `OilImpastoEngine.hpp` | Óleo/impasto: tinta com massa e ranhuras de cerda (declaração). |
| `OilImpastoEngine.cpp` | Implementação. |
| `EraserEngine.hpp` | Borracha: reduz o alfa na área do dab (declaração). |
| `EraserEngine.cpp` | Implementação (respeita Alpha Lock). |
| `BlurEngine.hpp` | Desfoque local por vizinhança (declaração). |
| `BlurEngine.cpp` | Implementação. |
| `SmudgeEngine.hpp` | Smudge: coleta a cor sob o dab e a arrasta (declaração). |
| `SmudgeEngine.cpp` | Implementação. |

## Regras

- Motor novo: herda `IBrushEngine`, entra no `BrushEngineFactory` e no `EngineType` de `brush/BrushProfile.hpp`. O `renderDab` não escreve laço de tiles nem bloco de seleção/recorte: monta uma `raster::DabFootprint`, uma `raster::PixelPermission` e passa um `kernel` (a cor de um pixel) para `forEachPixel`; a física do motor mora numa classe pequena do `.cpp` (como `GraphiteDeposit` no Lápis).
- O `kernel` roda em várias threads (um tile por vez): não escreve em estado compartilhado; só o `Smudge` guarda estado entre dabs, e o lê já pronto.
- Módulo mais alto de `engine/core`: pode incluir qualquer módulo abaixo, e nenhum módulo do núcleo o inclui.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/brush`
- `engine/core/canvas`
- `engine/core/raster`
- `engine/utils`
<!-- /arccc:deps -->
