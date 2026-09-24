# `ui/core/components/menu_bar/` — barra de menus

**Responsabilidade:** a barra de menus principal e um arquivo por menu. Os menus só expõem ações e sinais; quem liga cada item à ação é a `MainWindow` (`main_window_menu_builder.py`).

## Porta de entrada

`from ui.core.components.menu_bar import MenuBar`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `MenuBar`. |
| `edit_menu.py` | EditMenu — Menu Editar (Padrão Profissional da Indústria) — ARCcC i18n. |
| `file_menu.py` | FileMenu — Menu de Arquivo (Padrão Profissional da Indústria) — ARCcC i18n. |
| `filter_menu.py` | FilterMenu — Menu Filtros (Padrão Profissional da Indústria) — ARCcC i18n. |
| `help_menu.py` | HelpMenu — Menu Ajuda — ARCcC i18n. |
| `image_menu.py` | ImageMenu — Menu Imagem (Padrão Profissional da Indústria) — ARCcC i18n. |
| `layer_menu.py` | LayerMenu — Menu Camada (Padrão Profissional da Indústria) — ARCcC i18n. |
| `menu_bar.py` | MenuBar — Barra de Menus Principal Profissional da Lumenia UI. |
| `settings_menu.py` | `SettingsMenu`: idioma, renderização, curvas, cursor, atalhos, tema e plugins. |
| `select_menu.py` | SelectMenu — Menu Seleção (Padrão Profissional da Indústria) — ARCcC i18n. |
| `view_menu.py` | ViewMenu — Menu Exibir (Padrão Profissional da Indústria) — ARCcC i18n. |
| `window_menu.py` | `WindowMenu`: painéis (por `PanelId`), barras laterais, gavetas, barra flutuante, tela cheia e escala. |

## Regras

- Menu não executa ação nem conhece plugin: emite sinal ou expõe `QAction`. Textos por `tr()`.
- Painel no menu Janela usa o id canônico (`ui.core.plugins.panel_ids.PanelId`) e o título de `PANEL_TITLES`;
  a marca do item acompanha a gaveta (`MenuBar.set_panel_checked`, ligado pela janela principal).

## Dívida conhecida (medida em 2026-09-24)

`MenuBar` repassa ~70 sinais dos submenus um a um (fachada única para a janela principal).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/i18n`
- `ui/core/plugins`
- `ui/core/theme`
<!-- /arccc:deps -->
