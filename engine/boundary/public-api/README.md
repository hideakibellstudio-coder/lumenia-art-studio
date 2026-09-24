# `engine/boundary/public-api/` — API pública do motor

**Responsabilidade:** a `PaintEngineFacade`, um objeto por documento aberto, com todas as operações que a UI pode pedir ao motor.

## Porta de entrada

`PaintEngineFacade.hpp`. A ponte (`bridge/core/bindings`) expõe esta classe ao Python como `PaintEngineFacade`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `PaintEngineFacade.hpp` | Declaração da fachada: traço, camadas, seleção, transformação, guias/snap, histórico, exportação e telemetria (structs `DocumentContext`, `EngineStateContext`, `RawStrokeContext`, `TelemetryData`). |
| `PaintEngineFacade.cpp` | Implementação: camada de tradução que monta os contextos e delega aos orquestradores de `internal/` (o próprio arquivo avisa: tradução, não lógica). |
| `PaintEngineFacadeDisplay.cpp` | Saída para a tela: buffer de exibição, níveis de detalhe (LOD) e `clearHistory`; separado em 2026-09-24 para o `.hpp`/`.cpp` principal ficar abaixo de 450 linhas. |

## Regras

- Método público novo: declarado aqui, implementado num orquestrador de `internal/`, exposto em `bridge/core/bindings` e descrito em `bridge/boundary/contracts/aladyn_engine_native.pyi`.
- A fachada não guarda regra de negócio: monta o contexto e chama o orquestrador.

## Dívida conhecida (medida em 2026-09-24)

`internal/` é uma pasta de implementação dentro de `public-api/`: pelo ARCcC a API pública deveria conter só o contrato, e os orquestradores morariam em `engine/boundary/orchestrator/` (ou `engine/core/`). A ponte inclui arquivos de `internal/` diretamente (ver `bridge/core/bindings/README.md`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/boundary/public-api/internal`
- `engine/core/brush`
- `engine/core/canvas`
- `engine/core/color`
- `engine/core/document`
- `engine/core/engines`
- `engine/core/math`
- `engine/core/raster`
- `engine/core/stroke`
- `engine/core/telemetry`
- `engine/core/texture`
<!-- /arccc:deps -->
