# `ui/boundary/orchestrator/` — boot e janela principal

**Responsabilidade:** inicializa a aplicação (logging, splash, ícones, estado compartilhado, motor, plugins) e monta a `MainWindow`, que liga menus e atalhos a colaboradores de ação.

## Porta de entrada

`from ui.boundary.orchestrator import MainWindow`; o boot completo é `app_runner.launch()` (chamado por `main.py`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `MainWindow`. |
| `app_runner.py` | Boot: logging, splash, ícones e troca para a `MainWindow`. |
| `main_window.py` | `MainWindow`: cria MenuBar, ToolSidebar e StatusBar, instala o estado compartilhado antes dos plugins, recebe o workspace, cria os colaboradores e cuida de Desfazer/Refazer, câmera, tela cheia e eventos de janela. |
| `workspace_port.py` | Contrato (`ShellWorkspace`, `ShellCanvas`): tudo que a casca usa do workspace e do canvas, conferido por teste. |
| `shell_actions.py` | `ShellActions`: base dos colaboradores (sinal `statusMessage`) e `backend_ready`. |
| `document_actions.py` | `DocumentActions`: novo, abrir (imagem ou `.lmn`), salvar, salvar como, fechar com confirmação, fechar tudo ao sair. |
| `edit_actions.py` | `EditActions`: copiar, recortar, colar, preencher, selecionar tudo, inverter, desmarcar, modificar seleção. |
| `layer_actions.py` | `LayerActions`: menu Camada sobre o `LayerCommands` do documento ativo + diálogo de propriedades. |
| `image_actions.py` | `ImageActions`: exportar, tamanho do canvas/imagem, recorte, rotação da camada, rotação/espelho da vista, grade, réguas, prova de cores. |
| `dialog_actions.py` | `DialogActions`: diálogos e janelas auxiliares (filtros, atalhos, cursor, idioma, escala, tema, plugins, renderização, docas, barra flutuante, curvas, telemetria, ajuda). |
| `recovery_controller.py` | `RecoveryController`: cópias periódicas de recuperação e a oferta de reabri-las no início. |
| `menu_wiring.py` | Liga os sinais da MenuBar e da ToolSidebar aos colaboradores (só conecta). |

## Regras

- A casca chama `ui.core.state.install_app_state(...)` antes de descobrir
  os plugins: eles recebem o estado pelo `ServiceRegistry`.
- Cada colaborador recebe pelo construtor o que usa e fala com a barra de
  status pelo sinal `statusMessage`; nenhum lê atributo de outro nem da
  janela. Ação nova entra no colaborador do assunto; assunto novo vira
  colaborador novo (nunca mixin da `MainWindow`).
- Workspace e canvas só pelo contrato de `workspace_port.py`; método novo que
  a casca precise entra lá e no teste `tests/test_main_window_actions.py`.
  Nada de `hasattr`/`getattr` nesta pasta (o mesmo teste confere).
- Comandos de camada são os do painel de camadas
  (`ui.core.document.layer_commands.LayerCommands`): um caminho só.
- Edição de pixels vinda do menu roda por `canvas.run_as_stroke(...)`.
- Ferramentas passam pelo `ToolState`; cor de preenchimento vem do `BrushState`.

## Dívida conhecida (medida em 2026-09-24)

- Mensagens de status em português fixo (sem `tr()`) na maioria das ações.
- O DPI do diálogo de novo documento é coletado mas não é guardado no
  `Document` (aparece só na mensagem).

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
