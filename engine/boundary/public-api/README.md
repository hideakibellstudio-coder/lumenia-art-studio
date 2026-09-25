# `engine/boundary/public-api/` — API pública do motor

**Responsabilidade:** o contrato do motor com a ponte: a `PaintEngineFacade` (um objeto por documento aberto, com as operações que a UI pode pedir), as prévias do painel de pincel e a lista dos tipos de valor expostos ao Python.

## Porta de entrada

`AladynEngine.hpp`: o único arquivo que a ponte (`bridge/core/bindings`) inclui.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `AladynEngine.hpp` | Porta única: inclui a fachada, as prévias e os tipos de valor que a ponte liga ao Python (tipo novo exposto entra aqui). |
| `PaintEngineFacade.hpp` | Declaração da fachada: traço, camadas, seleção, transformação, guias/snap, histórico, exportação e telemetria (`TelemetryData`). |
| `PaintEngineFacade.cpp` | Implementação: monta os contextos e delega aos orquestradores de `../orchestrator/` (tradução, não lógica). |
| `PaintEngineFacadeDisplay.cpp` | Saída para a tela: buffer de exibição, níveis de detalhe (LOD) e `clearHistory`; separado em 2026-09-24 pelo teto de 450 linhas. |
| `BrushPreviews.hpp` | Prévias do painel de pincel: `renderStrokePreview` e `renderRoundTipMask` (declaração). |
| `BrushPreviews.cpp` | Delegação para `orchestrator/StrokePreviewRenderer`. |

## Regras

- Método público novo: declarado aqui, implementado num orquestrador de `../orchestrator/`, exposto em `bridge/core/bindings` e descrito em `bridge/boundary/contracts/aladyn_engine_native.pyi`.
- A fachada não guarda regra de negócio: monta o contexto e chama o orquestrador.
- Os contextos dos orquestradores (`DocumentContext`, `EngineStateContext`, `RawStrokeContext`) são só declarados aqui; o cabeçalho público não inclui `orchestrator/`.

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
- `engine/infrastructure/telemetry`
- `engine/utils`
<!-- /arccc:deps -->
