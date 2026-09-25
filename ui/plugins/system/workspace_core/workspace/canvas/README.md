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
- A janela principal usa o canvas só pelo contrato `ShellCanvas`
  (`ui/boundary/orchestrator/workspace_port.py`): `run_as_stroke`,
  `forward_key`, `is_busy`, `toggle_grid`, `toggle_rulers`, seleção e câmera.

## Dívida conhecida (medida em 2026-09-25)

`tools/` e `viewport/` importam o `RenderWidget` desta pasta só para anotar o
tipo do dono (`if TYPE_CHECKING:` em `tool_manager.py`,
`text_tool_controller.py`, `canvas_stroke_pipeline.py`, `cursor_controller.py`,
`input_router.py`, `viewport_renderer.py`): são os dois ciclos pai ↔ filha que
sobram no pilar Python. Um contrato (Protocol) por colaborador resolveria, mas o
`input_router.py` usa 37 membros do widget — ele ainda é parte do widget, e o
passo certo é dividir o `RenderWidget` por responsabilidade antes do contrato.

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
