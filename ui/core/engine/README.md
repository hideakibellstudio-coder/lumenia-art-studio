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
| `engine_type.py` | `EngineType`: id canônico do motor de pincel (Brush, Pencil, Inker, Eraser, Marker, Blur, Smudge, Watercolor, OilImpasto), igual ao enum nativo; contrato em `tests/test_engine_type_contract.py`. |
| `errors.py` | ui.core.engine.errors — Exceções padronizadas da camada de motor (`EngineContextError`: o motor não criou o contexto de um documento). |
| `limits.py` | `max_canvas_dimension()`: o maior lado de canvas, perguntado ao motor (valor de modo casca se não há motor). Diálogos e ações usam isto; ninguém repete o número. |
| `registry.py` | ui.core.engine.registry — EngineRegistry. |
| `telemetry_dto.py` | `TelemetrySnapshot`: DTO da telemetria; lê a struct nativa campo a campo sem valor padrão (contrato em `tests/test_telemetry_contract.py`). |
| `telemetry_meters.py` | Os 20 medidores (chave, título, leitura com nível semântico), usados pelo cockpit e pelo relatório. |
| `telemetry_report.py` | `build_report`: texto único do relatório de telemetria (os três botões "Copiar"). |
| `telemetry_tracker.py` | `TelemetryTracker`: fonte única da sessão de telemetria (diagnóstico, transições, picos, última caneta). |

## Regras

- Id de motor de pincel é `EngineType`, nunca número com comentário: a catraca
  `tests/test_engine_type_contract.py` barra literal em `ui/` (a ponta borracha
  da caneta pedia o id 6, que é o Borrar, até 2026-10-01).
- Lei nº 2/3: fora de `ui/infrastructure/bridge_client` ninguém importa
  `aladyn_engine_native` nem acessa `_facade`/`_native`. Precisa de algo do
  motor? Declare o método em `EngineBackend` e implemente no backend.
- Método novo no contrato: adicione em `backend.py` (com implementação padrão
  segura quando fizer sentido) e no `Protocol` do papel em
  `backend_protocols*.py`.
- Motor → documento: o backend não conhece o modelo de documentos; avisa
  `EngineRegistry.notify_document_modified(uid, motivo)` e o `DocumentManager`
  (que escuta) suja o documento. Um caminho só até o motor: não há fachada
  paralela nem comandos em dataclass (saíram em 2026-09-24, sem chamadores).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
