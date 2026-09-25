# `ui/plugins/system/workspace_core/` — plugin de sistema do workspace

**Responsabilidade:** o plugin de prioridade máxima que cria o `WorkspaceContainer` (canvas, abas, docas, barras flutuantes), o põe no centro da janela e registra a implementação de `WorkspaceService`.

## Porta de entrada

Carregado pelo `PluginManager`; outros plugins usam o workspace pelo `WorkspaceService` (`ui/core/plugins/workspace_contract.py`), nunca importando daqui.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | `WorkspaceCore` (plugin): cria o `WorkspaceContainer` com o estado injetado e registra o `WorkspaceService`. |

## Regras

O estado compartilhado (`BrushState`, `ToolState`, `BrushEngineSync`) é pedido ao `ServiceRegistry` com `require` e injetado no `WorkspaceContainer`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/plugins/system/workspace_core/workspace`
- `ui/plugins/system/workspace_core/workspace/canvas/renderers`
- `ui/core/plugins`
- `ui/core/state`
<!-- /arccc:deps -->
