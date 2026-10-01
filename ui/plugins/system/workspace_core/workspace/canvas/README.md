# `ui/plugins/system/workspace_core/workspace/canvas/` — canvas

**Responsabilidade:** o `RenderWidget`: mostra os pixels do motor e recebe ponteiro/teclado. Compõe colaboradores com estado próprio (câmera, roteador de entrada, cursor, traço, renderizador da viewport, ferramentas) e o editor de texto sobreposto.

## Porta de entrada

`from .canvas import CanvasWidget` (apelido de `RenderWidget`), usado pelo `WorkspaceContainer`. Métodos públicos: `publish_view`, `run_tool_command`, `apply_cursor_settings`, `canvas_transform`, `to_canvas`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `CanvasWidget`. |
| `render_widget.py` | RenderWidget — o canvas: apresenta os pixels do motor e recebe o ponteiro. |

## Regras

- O canvas não guarda estado de documento (Lei do rio nº 1): pixels estão no
  motor, camadas no `LocalLayerManager`, papel no `Document` (as propriedades
  `paper_color`/`paper_visible` leem o documento ativo).
- Cor, tamanho e pressão chegam do `BrushState` (via `CanvasBrushBinding`);
  ferramenta e opções do `ToolState` (via `CanvasToolBinding`).
- Colaboradores leem o widget por atributos públicos; nenhum escreve atributo
  privado dele.
- O motor chega aos colaboradores por uma porta só, `RenderWidget.backend`
  (o único pedido ao registro global nesta pasta). Cada colaborador declara no
  contrato dele com o canvas (`StrokeCanvas`, `SelectionCanvas`...) só o papel
  do motor que usa (`StrokeProtocol`, `SelectionTransformProtocol`...); nenhum
  chama `EngineRegistry` nem importa o `EngineBackend` inteiro.
- A janela principal usa o canvas só pelo contrato `ShellCanvas`
  (`ui/boundary/orchestrator/workspace_port.py`): `run_as_stroke`,
  `forward_key`, `is_busy`, `toggle_grid`, `toggle_rulers`, seleção e câmera.

## Dívida conhecida (medida em 2026-09-25)

Os dois ciclos pai ↔ filha (`tools/` e `viewport/` importavam o
`RenderWidget` só para anotar tipo) acabaram em 2026-09-25: cada colaborador
declara o contrato que usa (`tests/test_canvas_contracts.py`). O contrato do
roteador de ponteiro (`RouterCanvas`) tem 34 membros — ele ainda conhece quase
todo o widget; estreitá-lo é dividir o `RenderWidget` por responsabilidade, com a
rede de `tests/test_canvas_input_router.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/document`
- `ui/core/engine`
- `ui/core/state`
- `ui/infrastructure/i18n`
- `ui/plugins/system/workspace_core/workspace/canvas/renderers`
- `ui/plugins/system/workspace_core/workspace/canvas/tools`
- `ui/plugins/system/workspace_core/workspace/canvas/viewport`
<!-- /arccc:deps -->
