# `ui/infrastructure/bridge_client/` — fachada antiga do motor

**Responsabilidade:** `BridgeClient`, fachada que repassa chamadas ao `EngineBackend` ativo (inicializar a superfície, atualizar a vista, mapear coordenadas).

## Porta de entrada

`from ui.infrastructure.bridge_client import BridgeClient` (`BridgeClient.instance()`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | ui.infrastructure.bridge_client — Cliente Canônico de Comunicação com a Bridge (ARCcC). |
| `client.py` | BridgeClient — Fachada Engine-Agnóstica da Casca. |

## Regras

Código novo usa `EngineRegistry.instance().get_backend()` (`ui/core/engine`), não esta fachada.

## Dívida conhecida (medida em 2026-09-24)

Caminho paralelo ao `EngineRegistry`: hoje só o canvas (`init_renderer`, `update_view` dentro de `RenderWidget.publish_view`) e o `PluginContext` a usam. Candidata a sair.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/engine`
<!-- /arccc:deps -->
