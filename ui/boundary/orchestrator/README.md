# `ui/boundary/orchestrator/` — boot e janela principal

**Responsabilidade:** inicializa a aplicação (logging, splash, ícones, estado compartilhado, motor, plugins) e monta a `MainWindow`, que liga menus e atalhos às ações.

## Porta de entrada

`from ui.boundary.orchestrator import MainWindow`; o boot completo é `app_runner.launch()` (chamado por `main.py`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `MainWindow`. |
| `app_runner.py` | Boot: logging, splash, ícones e troca para a `MainWindow`. |
| `main_window.py` | `MainWindow`: instala o estado compartilhado (`install_app_state`) antes dos plugins, descobre os plugins e compõe os mixins de ações. |
| `main_window_dialog_actions.py` | Mixin: abre diálogos (filtros, guia, relatório de testes, preferências de cursor, atalhos). |
| `main_window_document_actions.py` | Mixin: novo, abrir, salvar e fechar documento. |
| `main_window_image_actions.py` | Mixin: tamanho do canvas/imagem, recorte, rotação e espelhamento da vista, grade e réguas. |
| `main_window_menu_actions.py` | Mixin: handlers dos itens de menu (editar, camada, seleção, preenchimento...). |
| `main_window_menu_builder.py` | Monta a MenuBar e registra atalhos de teclado. |
| `main_window_recovery.py` | Mixin: recuperação periódica e escolha de recuperação no início. |
| `main_window_tool_camera_actions.py` | Mixin: seleção de ferramenta (via `ToolState`), zoom/reset de câmera e tela cheia. |

## Regras

- A casca chama `ui.core.state.install_app_state(...)` antes de descobrir
  os plugins: eles recebem o estado pelo `ServiceRegistry`.
- Ações de ferramenta passam pelo `ToolState` (`app_state.tools.set_active_tool`);
  cor de preenchimento vem do `BrushState`. A janela não escreve em widgets de
  plugins.
- O canvas é alcançado por `self.canvas_widget` (público, pode ser `None` sem
  plugins); nunca por `workspace._alguma_coisa`.

## Dívida conhecida (medida em 2026-09-24)

- `MainWindow` ainda é composta por seis mixins que se leem uns aos outros por
  `self` (decomposição por tamanho de arquivo, não por responsabilidade).
- `main_window_menu_actions.py` está perto da parede dos 450 linhas e é o que
  mais usa `hasattr` no pacote (ver `tests/arccc_coupling_baseline.json`).
- Mensagens de status em português fixo (sem `tr()`) em várias ações.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/components`
- `ui/core/config`
- `ui/core/dialogs`
- `ui/core/document`
- `ui/core/engine`
- `ui/core/i18n`
- `ui/core/plugins`
- `ui/core/screens`
- `ui/core/screens/filters`
- `ui/core/state`
- `ui/core/theme`
- `ui/engine_backends`
<!-- /arccc:deps -->
