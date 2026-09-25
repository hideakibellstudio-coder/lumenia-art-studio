# `plugins/ui/brush_plugin/components/` — peças do painel de pincel

**Responsabilidade:** a coluna de seleção de ferramentas e a seção de sliders rápidos (pináveis).

## Porta de entrada

`from .components import ToolSelectionColumn, QuickSlidersSection`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `ToolSelectionColumn` e `QuickSlidersSection`. |
| `quick_sliders_section.py` | QuickSlidersSection — sliders rápidos (e pináveis) do painel de pincel. |
| `tool_selection_column.py` | ToolSelectionColumn — Vertical toolbar column for brush & canvas tools. |

## Regras

Views puras: emitem o que o usuário mexeu (`paramEdited`, `toolActivated`) e mostram o que recebem (`show_value`, `set_tool_active`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/state`
- `ui/core/widgets`
- `ui/infrastructure/i18n`
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
