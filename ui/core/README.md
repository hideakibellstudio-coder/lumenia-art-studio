# `ui/core/` — núcleo compartilhado

**Responsabilidade:** o que casca e plugins compartilham: ícones, catálogo de ferramentas e suas opções, atalhos, caminhos de recursos; subpastas com estado, documento, contrato do motor, plugins, tema, idioma, configuração, widgets e telas.

## Porta de entrada

Os módulos da raiz são importados diretamente (não há reexportação central):
`ui.core.icons.get_icon` (27 consumidores), `ui.core.runtime_paths.resource_path`,
`ui.core.tools` (`TOOL_META`, `DEFAULT_TOOLS`, `get_tool_name`, `ToolCommand`),
`ui.core.tool_settings` (`default_tool_settings`, `normalize_tool_settings`).
`ui.core` reexporta só `ThemeManager` e `get_icon`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `ThemeManager` e `get_icon`. |
| `icon_svg_catalog.py` | ui.core.icon_svg_catalog — Catálogo Centralizado de Ícones SVG e Aliases. |
| `icon_svg_tools.py` | ui.core.icon_svg_tools — Catálogo SVG de Ferramentas Artísticas e Camadas. |
| `icons.py` | ui.core.icons — Catálogo Centralizado de Ícones Vetoriais SVG Dinâmicos. |
| `logger.py` | Atalho de compatibilidade: reexporta `ui.infrastructure.logging`. |
| `runtime_paths.py` | Deterministic paths for source execution and a standalone Windows bundle. |
| `shortcut_bindings.py` | Estado efetivo dos atalhos, compartilhado pelos comandos locais do canvas. |
| `shortcut_catalog.py` | Canonical IDs and factory keyboard shortcuts. |
| `shortcut_registry.py` | One application point for menu and tool shortcuts, with collision checks. |
| `tool_settings.py` | Contrato das opções de cada ferramenta: valores padrão e validação (`normalize_tool_settings`). |
| `tools.py` | Catálogo de ferramentas (`TOOL_META`, nomes traduzidos) e o enum `ToolCommand` (Aplicar, Desmarcar, Inserir texto...). |

## Regras

- É o KERNEL: nada aqui importa `plugins/`.
- Opção de ferramenta nova nasce em `tool_settings.py` (padrão + validador) e
  mora no `ToolState` (`ui/core/state`), nunca num widget.
- Comando pontual novo sobre a ferramenta em uso: um valor em `ToolCommand`
  e um caso em `ToolManager.run_command` (canvas).

## Dívida conhecida (medida em 2026-09-24)

- `shortcut_registry.py` importa `MenuBar` (de `components/`) só para anotar
  tipo: o núcleo depende de um componente de tela.
- `logger.py` é atalho duplicado de `ui/infrastructure/logging`, que por sua
  vez importa `ui.core.runtime_paths`: ciclo entre as duas pastas.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/components/menu_bar`
- `ui/core/i18n`
- `ui/core/theme`
- `ui/infrastructure/logging`
<!-- /arccc:deps -->
