# `engine/boundary/orchestrator/` — orquestradores da fachada

**Responsabilidade:** um orquestrador por assunto (traço, camadas, seleção, transformação, snap, memória, exportação, preenchimento, colagem, estado do documento, prévias) que executa o que a `PaintEngineFacade` recebe.

## Porta de entrada

Não há porta única: cada orquestrador é incluído pela `PaintEngineFacade.cpp` (e pelas prévias). Contexto comum: `DocumentContext.hpp`. Namespace `boundary::orchestrator`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `BrushEngineFactory.hpp` | Única lista concreta de motores de pincel: cria o `IBrushEngine` de um `EngineType`. |
| `BufferPasteOrchestrator.hpp` | Colar um buffer RGBA na camada ativa (declaração). |
| `BufferPasteOrchestrator.cpp` | Colar um buffer RGBA na camada ativa, com histórico. |
| `DocumentContext.hpp` | Contrato do que uma operação de documento toca (pilha, grade, histórico, compositor, seleção); `compositeAll`/`compositeRegion` só MARCAM tiles velhos no compositor (`invalidateAll`/`invalidate`); quem lê pixels recompõe o que lê (S3). Não há mais composição em lote. |
| `DocumentStateOrchestrator.hpp` | Operações sobre o documento inteiro: redimensionar, limpar, desfazer/refazer, geometria preparada (declaração, `EngineStateContext`). |
| `DocumentStateOrchestrator.cpp` | Implementação: mantém histórico e grade coerentes quando a geometria do documento muda. |
| `FloodFillOrchestrator.hpp` | Balde de tinta na camada ativa (declaração). |
| `FloodFillOrchestrator.cpp` | Balde de tinta: preenche no espaço da camada (a máscara de recorte continua não destrutiva); sobre todas as camadas, lê a composição e a põe em dia antes (`ensureAllFresh`). |
| `LayerDirtyRegion.hpp` | Cálculo da região visual suja de uma camada (inclui grupos e máscaras de recorte). |
| `LayerSampleSource.hpp` | De onde o balde e a varinha leem a região: a composição ou só a camada ativa (opção "Todas as Camadas"). |
| `LayerStackOrchestrator.hpp` | Mutações da pilha de camadas (adicionar, remover, duplicar, reordenar, agrupar) com recomposição e histórico. |
| `MemoryOrchestrator.hpp` | Compressão de camadas inativas e medidas de memória de tiles (COW). |
| `PixelFormatGuard.hpp` | `requireEightBit`: a recusa limpa (`std::logic_error`, `RuntimeError` no Python) que traço, balde, preencher/apagar seleção, transformar, espelhar, girar e colar fazem num documento de 16 bits até a S6 ensiná-los a escrever 16 bits; roda antes de mexer em qualquer estado, e o documento fica como estava. A varinha não precisa dele: lê a camada estreitada a 8 bits. |
| `RasterExportOrchestrator.hpp` | Saída raster: buffer de camada (num documento de 16 bits, a camada estreitada a 8) e `copyLayerPixels16` (os 16 bits), miniatura, conversão de perfil de cor, buffer de exibição inteiro ou só um retângulo (`copyDisplayRegion`, o que a repintura pede); o buffer de exibição nasce vazio e `ensureDisplayBuffer` o dimensiona na primeira leitura com perfil que não é sRGB; `copyBufferRegion` copia um retângulo de um buffer de 4 ou de 8 bytes por pixel (declaração). |
| `RasterExportOrchestrator.cpp` | Implementação da saída raster; ler uma camada ou a miniatura dela não descomprime os tiles de vez. |
| `SelectionOrchestrator.hpp` | Seleção: varinha, retângulo, elipse, polígono, apagar e preencher a seleção (declaração). |
| `SelectionOrchestrator.cpp` | Implementação sobre `selection/SelectionEngine`, com histórico. |
| `SnapOrchestrator.hpp` | Guias, simetria e snap (reto, curvilíneo, perspectiva) e estimativa de trajetória (declaração). |
| `SnapOrchestrator.cpp` | Implementação; codifica curvas curvilíneas em 11 doubles para cruzar a ponte sem tipo novo. |
| `StrokeLatencyPolicy.hpp` | Regra de baixa latência compartilhada pelos arquivos do `StrokeOrchestrator`. |
| `StrokeOrchestrator.hpp` | Traço a partir de amostras brutas: interpolação por spline e deposição de dabs (declaração, `RawStrokeContext`). |
| `StrokeOrchestrator.cpp` | `updateStrokeRaw`: cada amostra da caneta vira dabs e trechos de spline. |
| `StrokeOrchestratorEnd.cpp` | `endStrokeRaw` (separado em 2026-09-22, teto de 450 linhas). Com estabilização, o fim drena o estabilizador e desenha a cauda pelo caminho, com o afunilamento dentro dela (`renderReleaseTail`, 2026-10-09); antes, um segmento reto até a caneta e uma cauda extrapolada além dela. |
| `StrokeOrchestratorSegment.cpp` | Desenho de um segmento (`renderSegment`, `renderSplineSegment`): interpolação, histórico, rasterização e composição (separado em 2026-09-25, estava na parede dos 450). |
| `StrokePreviewRenderer.hpp` | Prévias fora de documento: pincelada de demonstração e máscara da ponta redonda (declaração). |
| `StrokePreviewRenderer.cpp` | Pincelada com o motor de pincel real do perfil; máscara da ponta com a queda do `LargeBrushOptimizer` (o laço morava na ponte até 2026-09-25). |
| `StrokeSessionOrchestrator.hpp` | Sessão de traço (início, atualização, fim) e amostra de telemetria (declaração). |
| `StrokeSessionOrchestrator.cpp` | Implementação e medidas de memória/tiles do traço. |
| `TransformOrchestrator.hpp` | Transformar livre e distorcer, espelhar e girar a camada ativa (declaração). |
| `TransformOrchestrator.cpp` | Implementação sobre `raster/TransformEngine`, com histórico. |

## Regras

- Um orquestrador por assunto; recebe o contexto (`DocumentContext`/`EngineStateContext`) em vez de ler a fachada.
- Orquestrador coordena: algoritmo de pixel ou geometria vai para `engine/core/`.
- Não é API pública: a ponte não inclui nada daqui (saiu de `public-api/internal/` em 2026-09-25).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/brush`
- `engine/core/canvas`
- `engine/core/color`
- `engine/core/document`
- `engine/core/document/blending`
- `engine/core/engines`
- `engine/core/history`
- `engine/core/math`
- `engine/core/raster`
- `engine/core/selection`
- `engine/core/stroke`
- `engine/infrastructure/telemetry`
- `engine/utils`
<!-- /arccc:deps -->
