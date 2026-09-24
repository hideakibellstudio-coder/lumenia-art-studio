# `ui/core/screens/` — telas e janelas da casca

**Responsabilidade:** janelas completas abertas pela casca: sobre, novo documento, fechar documento, preferências de cursor, curvas de pressão, gavetas, barra flutuante, atalhos; subpastas de filtros, plugins e aparência.

## Porta de entrada

`from ui.core.screens import ThemeDialog, PluginsWindow, NewDocumentDialog, CloseDocumentDialog`; as demais por módulo.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta as telas mais usadas. |
| `about_dialog.py` | AboutDialog — Diálogo Moderno 'Sobre o Lumenia' (ARCcC i18n). |
| `close_document_dialog.py` | CloseDocumentDialog — Diálogo Moderno de Confirmação para Salvar/Descartar Alterações. |
| `cursor_settings_dialog.py` | Cursor Settings Dialog — Diálogo de Personalização e Preferências de Cursores. |
| `curve_window.py` | CurveWindow — Janela de Configuração de Curvas LUT / Bézier do ALADYN ENGINE. |
| `dock_settings_dialog.py` | DockBarsSettingsDialog — Configurações do Sistema de Gavetas. |
| `floating_toolbar_components.py` | FloatingToolbarComponents — Componentes Visuais para Configurações da Barra Flutuante. |
| `floating_toolbar_settings_dialog.py` | FloatingToolbarSettingsDialog — Central de Configurações da Barra Rápida Flutuante (Lumenia V2). |
| `keyboard_shortcuts_dialog.py` | Keyboard Shortcuts Dialog — Diálogo de Gerenciamento e Personalização de Atalhos. |
| `new_document_dialog.py` | `NewDocumentDialog`: formulário do novo documento (nome, medidas, DPI, perfil, papel) ao lado do `PresetGallery`. |

## Regras

Tela devolve o resultado (sinal ou `exec()`); quem aplica é a casca ou o estado. Cores pelo `ThemeManager`, textos por `tr()`.

## Dívida conhecida (medida em 2026-09-24)

`NewDocumentDialog` criado sem pai e coletado pelo GC do Python junto com outro derruba o PySide 6.11.1 (ver `tests/qt_windows.py`); na aplicação ele é criado com pai.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/config`
- `ui/core/dialogs`
- `ui/core/engine`
- `ui/core/i18n`
- `ui/core/screens/new_document`
- `ui/core/screens/plugins`
- `ui/core/screens/settings`
- `ui/core/theme`
- `ui/core/widgets/toggle`
<!-- /arccc:deps -->
