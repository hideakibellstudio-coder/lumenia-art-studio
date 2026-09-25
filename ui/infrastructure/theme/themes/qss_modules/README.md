# `ui/infrastructure/theme/themes/qss_modules/` — folha de estilo em módulos

**Responsabilidade:** o QSS da aplicação dividido por área, concatenado em ordem alfabética e compilado com os tokens do tema ativo.

## Porta de entrada

`ThemeManager` lê os `.qss` em ordem (prefixo numérico) e troca `@TOKEN` pelo valor do tema.

## Arquivos

| Arquivo | Área |
|---|---|
| `01_globals.qss` | Base global. |
| `02_layout.qss` | Layout e molduras. |
| `03_navigation.qss` | Menus e navegação. |
| `04_buttons.qss` | Botões. |
| `05_inputs.qss` | Campos de entrada. |
| `06_tables.qss` | Tabelas e listas. |
| `07_scrollbars.qss` | Barras de rolagem. |
| `08_workspace_core.qss` | Workspace (docas, canvas, barras). |
| `09_plugins_window.qss` | Janela de plugins. |
| `10_advanced_windows.qss` | Janelas flutuantes avançadas. |

## Regras

- Só tokens (`@COR`, `@ASSETS_DIR`...): cor literal aqui escapa do tema (`tests/test_theme_system.py` confere tokens não resolvidos).
