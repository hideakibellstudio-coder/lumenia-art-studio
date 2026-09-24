# `plugins/system/` — plugins de sistema

**Responsabilidade:** os plugins sem os quais a aplicação não funciona (o workspace com canvas, docas e barras).

## Porta de entrada

Registrados em `plugins/builtin_registry.py`; carregados pelo `PluginManager` antes dos plugins de interface (prioridade 100).

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `workspace_core/` | Workspace: canvas, docas, abas, barras de ferramentas; publica o `WorkspaceService`. |

## Regras

- Plugin de sistema não depende de plugin de interface; a comunicação é pelo `WorkspaceService` e pelo estado em `ui/core/state`.
