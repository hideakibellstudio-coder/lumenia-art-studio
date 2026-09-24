# `ui/core/components/tool_sidebar/` — barra rápida de ferramentas

**Responsabilidade:** a barra superior de acesso rápido (pincel, borracha, formas, histórico, zoom).

## Porta de entrada

`from ui.core.components.tool_sidebar import ToolSidebar`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `ToolSidebar`. |
| `sidebar.py` | ToolSidebar — Barra Superior de Ferramentas Rápidas (ARCcC i18n). |

## Regras

Mostra a ferramenta ativa do `ToolState` (a `MainWindow` marca o botão ao receber `activeToolChanged`); não guarda ferramenta própria.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/i18n`
- `ui/core/theme`
<!-- /arccc:deps -->
