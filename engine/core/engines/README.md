# `engine/core/engines/` — mini-motores de pincel

**Responsabilidade:** a física de cada tipo de pincel — como um dab deposita, apaga, borra ou arrasta tinta nos tiles da camada.

## Porta de entrada

`IBrushEngine.hpp` (interface comum); a lista concreta de motores fica em `engine/boundary/orchestrator/BrushEngineFactory.hpp`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `IBrushEngine.hpp` | Interface polimórfica de todo mini-motor (inclui `reachScale`: quantas vezes o raio do dab o motor alcança, para a área suja). |
| `PencilEngine.hpp` | Lápis/grafite/giz: contato com o micro-relevo do papel (declaração). |
| `PencilEngine.cpp` | Implementação. |
| `InkerEngine.hpp` | Caneta/nanquim/G-pen: fluxo contínuo sobre papel liso (declaração). |
| `InkerEngine.cpp` | Implementação. |
| `MarkerEngine.hpp` | Marcador de álcool: tinta que se funde com traços anteriores, não com os próprios carimbos (declaração; guarda a memória do traço). |
| `MarkerEngine.cpp` | A cor sai da base do traço e da cobertura (`StrokeInkLedger`): o miolo tem a cor escolhida; um traço novo por cima multiplica, com piso de 70% da tinta. |
| `WatercolorEngine.hpp` | Aquarela: pigmento em água sobre meio poroso (declaração; guarda a memória do traço). |
| `WatercolorEngine.cpp` | Anel de secagem, granulação e sangramento molhado-no-molhado; o pigmento filtra a base do traço uma vez só (`StrokeInkLedger`), diluído pela água. |
| `OilBristles.hpp` | O feixe de cerdas do Óleo: cada cerda lembra a cor e a carga que leva, a altura e a capacidade; ruído de inteiros (o mesmo traço em qualquer máquina). Só o cabeçalho. |
| `OilLight.hpp` | A luz fixa do relevo do Óleo, calculada a partir do declive da superfície e aplicada de um jeito que se desfaz exatamente (o brilho de um pixel não acumula). Só o cabeçalho. |
| `OilSurface.hpp` | O que um pixel do carimbo de Óleo vê: os seis controles limitados, a curva que reescala a cobertura ao espaçamento e a superfície (forma do pincel + feixe + direção do traço). Só leitura. |
| `OilImpastoEngine.hpp` | Óleo/impasto: um feixe de cerdas que carrega tinta (declaração; guarda o estado do traço: cerdas, direção e a memória do relevo). |
| `OilImpastoEngine.cpp` | A direção do traço, o avanço das cerdas a cada carimbo (esgotam, pegam a cor da tela como estava antes do traço, são repostas pela reserva) e a composição de cada pixel com a luz do relevo. |
| `EraserEngine.hpp` | Borracha: reduz o alfa na área do dab (declaração). |
| `EraserEngine.cpp` | Implementação (respeita Alpha Lock). |
| `BlurEngine.hpp` | Desfoque local por vizinhança (declaração). |
| `BlurEngine.cpp` | Implementação. |
| `SmearPatch.hpp` | O que o Borrar carrega: um pedaço da imagem do tamanho do dab (cada célula é um deslocamento em relação ao centro), em alfa pré-multiplicado e ponto flutuante (`PremultColor`). Só o cabeçalho. |
| `SmudgeEngine.hpp` | Borrar: carrega um pedaço da imagem e o arrasta como um dedo (declaração). |
| `SmudgeEngine.cpp` | Cada pixel mistura o que há com o carregado (força por distância, não por carimbo) e o carregado se mistura ao que o pincel pisa (comprimento do arrasto em diâmetros). |

## Regras

- Motor novo: herda `IBrushEngine`, entra no `BrushEngineFactory` e no `EngineType` de `brush/BrushProfile.hpp`. O `renderDab` não escreve laço de tiles nem bloco de seleção/recorte: monta uma `raster::DabFootprint`, uma `raster::PixelPermission` e passa um `kernel` (a cor de um pixel) para `forEachPixel`; a física do motor mora numa classe pequena do `.cpp` (como `GraphiteDeposit` no Lápis).
- O `kernel` roda em várias threads (um tile por vez): não escreve em estado compartilhado; só o `Smudge`, o feixe de cerdas do Óleo e a `StrokeInkLedger` do Marcador, da Aquarela e do Óleo guardam estado entre dabs; o estado do motor é atualizado em série, uma vez por dab, e cada pixel mexe só na sua célula.
- Estado de traço (Borrar, Óleo): começa em `onBeginStroke`, termina em `onEndStroke` e zera ao trocar de motor. Com simetria ou espalhamento cada dab vem de um lugar diferente e o movimento deixa de significar um traço: o Borrar e o Óleo continuam funcionando, mas sem direção estável (a pré-visualização não chama os ganchos e constrói um motor novo).
- Textura de pincel e de ponta: só o Pincel, o Lápis, a Borracha (forma) e a Aquarela (papel) a leem. O Nanquim, o Marcador e o Óleo **não a leem de propósito** (decisão do dono em 2026-10-03: se não leem, melhor sem): o Nanquim e o Marcador são traço limpo, e a superfície do Óleo vem das cerdas e do relevo, não de uma textura. Quem passar a ler uma textura muda `IGNORED_BY_DESIGN` em `tests/test_brush_engines_characterization.py` de propósito, no mesmo commit.
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
