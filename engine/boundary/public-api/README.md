# `engine/boundary/public-api/` — API pública do motor

**Responsabilidade:** o contrato do motor com a ponte: a `PaintEngineFacade` (um objeto por documento aberto, com as operações que a UI pode pedir), as prévias do painel de pincel e a lista dos tipos de valor expostos ao Python.

## Porta de entrada

`AladynEngine.hpp`: o único arquivo que a ponte (`bridge/core/bindings`) inclui.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `AladynEngine.hpp` | Porta única: inclui a fachada, as prévias e os tipos de valor que a ponte liga ao Python (tipo novo exposto entra aqui). |
| `PaintEngineFacade.hpp` | Declaração da fachada: o formato de pixel do documento (`PaintEngineFacade(w, h, formato)`, 8 bits por padrão), traço, camadas, seleção, transformação, guias/snap, histórico, exportação e telemetria (`TelemetryData`). |
| `PaintEngineFacade.cpp` | Implementação: monta os contextos e delega aos orquestradores de `../orchestrator/` (tradução, não lógica). |
| `PaintEngineFacadeDisplay.cpp` | Saída para a tela: perfil de cor (o buffer de exibição só existe com perfil que não é sRGB e é devolvido ao voltar ao sRGB), buffer de exibição inteiro ou por região, níveis de detalhe (LOD) por região e `clearHistory`; separado em 2026-09-24 pelo teto de 450 linhas. É também onde moram os portões do buffer composto (S3): cada leitor (`getRawPixelData`, `getDisplayRawPixelData`, `copyDisplayRegion`, os dois LODs) recompõe os tiles velhos da área que lê antes de ler (`ensureAllFresh`), e a janela de LOD recompõe só o retângulo do nível 0 que ela cobre. |
| `LayerSnapshot.hpp` | As camadas de um documento congeladas num instante (S1.2): custa o número de tiles (compartilha buffers copy-on-write) e pode ser lido de outra thread enquanto o artista pinta. Entrada da gravação em segundo plano. |
| `LayerSnapshot.cpp` | Tira o instantâneo e codifica uma camada em bloco de tiles. |
| `DecodedLayer.hpp` | Os pixels de uma camada já decodificados de um bloco de tiles, fora de qualquer documento (S1.2): nasce em qualquer thread e `adoptDecodedLayer` o coloca numa camada em tempo constante. |
| `DecodedLayer.cpp` | Decodifica o bloco (validação e descompressão paralela) e entrega a grade uma vez só. |
| `PaintEngineFacadePersistence.cpp` | Persistência da fachada: `snapshotLayers`, `restoreLayerTiles` e o par `beginBatch`/`endBatch`, que desde a S3 não adia nada (o motor só compõe o que alguém lê) e fica como contrato: `endBatch` sem `beginBatch` é erro. |
| `PaintEngineFacadeRgba16.cpp` | Leitura dos 16 bits de um documento de 16 bits (S5): `copyComposite16` (a composição, só o retângulo pedido e já em dia) e `copyLayer16` (uma camada inteira). A tela segue em 8 bits; quem precisa dos 16 (exportação, conta-gotas, histograma) lê por aqui. Num documento de 8 bits não há o que ler (`std::logic_error`/`std::invalid_argument`). |
| `PaintEngineFacadeLayers.cpp` | Operações de camadas e máscaras de camada (S9): delegações ao LayerStackOrchestrator para adição, remoção, reordenação, atributos e máscaras raster da fachada. Separado para manter a fachada sob o teto ARCcC. |
| `BrushPreviews.hpp` | Prévias do painel de pincel: `renderStrokePreview` e `renderRoundTipMask` (declaração). |
| `BrushPreviews.cpp` | Delegação para `orchestrator/StrokePreviewRenderer`. |

## Regras

- Método público novo: declarado aqui, implementado num orquestrador de `../orchestrator/`, exposto em `bridge/core/bindings` e descrito em `bridge/boundary/contracts/aladyn_engine_native.pyi`.
- A fachada não guarda regra de negócio: monta o contexto e chama o orquestrador.
- Os contextos dos orquestradores (`DocumentContext`, `EngineStateContext`, `RawStrokeContext`) são só declarados aqui; o cabeçalho público não inclui `orchestrator/`.

## Dívida conhecida (medida em 2026-10-03)

- `PaintEngineFacade.hpp` tem 426 linhas (zona amarela, a 4 da parede dos 430: com 430 o teste de
  governança reprova). Passou de 427 em 2026-10-01 quando a pose da caneta (`m_lastPose`) entrou ao
  lado do último carimbo; na S5 (2026-10-03) o formato de pixel e a leitura de 16 bits entraram, e para
  caber condensei os comentários do snap curvilíneo e de perspectiva (a leitura de 16 bits mora em
  `PaintEngineFacadeRgba16.cpp`, não aqui). **Nenhum membro nem método novo entra aqui antes de uma extração.** Há dois
  candidatos, e o primeiro dá mais folga:
  1. O estado da sessão de traço: `m_lastDab`, `m_lastPose`, `m_strokeStartPoint`, `m_lastRawPoint`,
     `m_lastRawPressure`, `m_hasLastRawPoint`, `m_distanceCarryover`, `m_timeCarryover`,
     `m_lastTimestamp`, `m_segmentsRenderedInStroke`, `m_pendingFirstSegment`, `m_firstSample` e a
     janela da spline (`m_splineP0`..`m_splineP2`, `m_splineCount`). São dezesseis membros que só os
     orquestradores de traço usam (a fachada os liga ao `RawStrokeContext` em `strokeContext()` e
     reinicia alguns ao começar um traço bruto); viram um `StrokeSessionState` (em `engine/core/stroke/`,
     como `PenPose`) que a fachada guarda por valor, e `RawStrokeContext` passa a referenciá-lo em vez
     de uma referência por membro.
  2. A saída para a tela (perfil de cor, buffer de exibição, pirâmide de LOD, retângulo danificado)
     cresceu três vezes em S1.1 e tem dono implícito espalhado pela fachada: um colaborador
     `DisplayOutput` com esse estado (e não mover corpos para o `.cpp`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/boundary/orchestrator`
- `engine/core/brush`
- `engine/core/canvas`
- `engine/core/color`
- `engine/core/document`
- `engine/core/engines`
- `engine/core/history`
- `engine/core/math`
- `engine/core/raster`
- `engine/core/selection`
- `engine/core/stroke`
- `engine/core/texture`
- `engine/infrastructure/crash`
- `engine/infrastructure/licensing`
- `engine/infrastructure/telemetry`
- `engine/utils`
<!-- /arccc:deps -->
