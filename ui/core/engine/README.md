# `ui/core/engine/` — contrato do motor

**Responsabilidade:** a fronteira entre interface e motor: o contrato `EngineBackend` (e os `Protocol`s por papel), o `EngineRegistry` que guarda o backend ativo, o DTO de telemetria e as exceções. A interface conversa com o motor só por aqui.

## Porta de entrada

`from ui.core.engine.registry import EngineRegistry` (15 consumidores;
`EngineRegistry.instance().get_backend()`), `backend.EngineBackend`,
`backend.PointerEvent`, `telemetry_dto.TelemetrySnapshot`,
`telemetry_tracker.TelemetryTracker`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | ui.core.engine — Contratos de Motor (Shell Engine-Agnóstica). |
| `backend.py` | ui.core.engine.backend — Contrato Canônico EngineBackend + PointerEvent. |
| `backend_protocols.py` | ui.core.engine.backend_protocols -- EngineBackend decomposto em Protocols por papel. |
| `backend_protocols_selection.py` | ui.core.engine.backend_protocols_selection -- papel "SelectionTransform". |
| `commands.py` | ui.core.engine.commands — Comandos de Motor como Dataclasses Puras. |
| `errors.py` | ui.core.engine.errors — Exceções padronizadas da camada de motor. |
| `registry.py` | ui.core.engine.registry — EngineRegistry. |
| `telemetry_dto.py` | ui.core.engine.telemetry_dto — DTO Canônico de Telemetria Universal. |
| `telemetry_tracker.py` | TelemetryTracker — Centralizador Global de Diagnóstico, Transições de Estado e Relatórios. |

## Regras

- Lei nº 2/3: fora de `ui/engine_backends` ninguém importa
  `aladyn_engine_native` nem acessa `_facade`/`_native`. Precisa de algo do
  motor? Declare o método em `EngineBackend` e implemente no backend.
- Método novo no contrato: adicione em `backend.py` (com implementação padrão
  segura quando fizer sentido) e no `Protocol` do papel em
  `backend_protocols*.py`.

## Dívida conhecida (medida em 2026-09-24)

`commands.py` (dataclasses de comando) só é usado pelo despacho antigo (`aladyn_dispatch.py`) e pela reexportação em `ui/core/plugins/contracts.py`: caminho paralelo aos métodos do `EngineBackend`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
