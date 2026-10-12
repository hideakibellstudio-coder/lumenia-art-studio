# `ui/core/` — núcleo compartilhado

**Responsabilidade:** o núcleo que casca e plugins compartilham: catálogo de ferramentas e suas opções, atalhos; subpastas com estado, documento, contrato do motor, cor, geometria, plugins, componentes, widgets e telas, e as regras da distribuição (`diagnostics/`, `updates/`).

## Porta de entrada

Os módulos da raiz são importados diretamente (não há reexportação central):
`ui.core.tools` (`TOOL_META`, `DEFAULT_TOOLS`, `get_tool_name`, `ToolCommand`),
`ui.core.tool_settings` (`default_tool_settings`, `normalize_tool_settings`),
`ui.core.shortcut_registry`. Serviços técnicos (tema, ícones, idioma,
configuração, caminhos) ficam em `ui/infrastructure/` desde 2026-09-24.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote (sem reexportação). |
| `shortcut_bindings.py` | Estado efetivo dos atalhos, compartilhado pelos comandos locais do canvas. |
| `shortcut_catalog.py` | Canonical IDs and factory keyboard shortcuts. |
| `shortcut_registry.py` | One application point for menu and tool shortcuts, with collision checks. |
| `tool_settings.py` | Contrato das opções de cada ferramenta: valores padrão e validação (`normalize_tool_settings`). |
| `tools.py` | Catálogo de ferramentas (`TOOL_META`, nomes traduzidos) e o enum `ToolCommand` (Aplicar, Desmarcar, Inserir texto...). |

## Regras

- É o KERNEL: nada aqui importa `ui/plugins/` (a exceção é o carregador, `plugins/`, que lê a lista dos embutidos).
- Opção de ferramenta nova nasce em `tool_settings.py` (padrão + validador) e
  mora no `ToolState` (`ui/core/state`), nunca num widget.
- Comando pontual novo sobre a ferramenta em uso: um valor em `ToolCommand`
  e um caso em `ToolManager.run_command` (canvas).

## Dívida conhecida (medida em 2026-09-24)

- `shortcut_registry.py` importa `MenuBar` (de `components/`) só para anotar
  tipo: o núcleo depende de um componente de tela.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/components/menu_bar`
- `ui/infrastructure/i18n`
<!-- /arccc:deps -->
