# `ui/core/components/` — peças fixas da janela principal

**Responsabilidade:** componentes da moldura da janela: barra de menus, barra de status, barra rápida de ferramentas e a tela de abertura (splash).

## Porta de entrada

`from ui.core.components import MenuBar, ToolSidebar, StatusBar`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `MenuBar`, `ToolSidebar`, `StatusBar` e `ThemeDialog`. |
| `splash_screen.py` | LumeniaSplashScreen — Banner de Inicialização Moderno e Dinâmico. |

## Dívida conhecida (medida em 2026-09-24)

`__init__.py` reexporta `ThemeDialog`, que é uma tela (`ui/core/screens/settings`): componente dependendo de tela.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/components/menu_bar`
- `ui/core/components/status_bar`
- `ui/core/components/tool_sidebar`
- `ui/core/screens/settings`
- `ui/infrastructure`
<!-- /arccc:deps -->
