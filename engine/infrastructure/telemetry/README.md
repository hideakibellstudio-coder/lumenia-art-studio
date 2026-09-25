# `engine/infrastructure/telemetry/` — telemetria do traço

**Responsabilidade:** medir o traço em tempo real (latência por etapa, dabs, tiles, memória) para o painel de telemetria.

## Porta de entrada

`EngineTelemetry.hpp` (`EngineTelemetryManager`, `RealTimeStrokeMetrics`; namespace `telemetry`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `EngineTelemetry.hpp` | Métricas por etapa e do traço, e o gerenciador que as acumula; `simdActive` reflete o build (AVX2 ou escalar). |

## Regras

- A UI lê estas métricas pelo DTO `ui/core/engine/telemetry_dto.py`, conferido campo a campo por `tests/test_telemetry_contract.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
