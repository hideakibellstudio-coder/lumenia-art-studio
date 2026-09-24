# `plugins/system/workspace_core/workspace/canvas/` — canvas

**Responsabilidade:** o `RenderWidget`: mostra os pixels do motor e recebe ponteiro/teclado. Compõe colaboradores com estado próprio (câmera, roteador de entrada, cursor, traço, renderizador da viewport, ferramentas) e o editor de texto sobreposto.

## Porta de entrada

`from .canvas import CanvasWidget` (apelido de `RenderWidget`), usado pelo `WorkspaceContainer`. Métodos públicos: `publish_view`, `run_tool_command`, `apply_cursor_settings`, `canvas_transform`, `to_canvas`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `CanvasWidget`. |
| `render_widget.py` | RenderWidget — o canvas: apresenta os pixels do motor e recebe o ponteiro. |
| `text_overlay_editor.py` | In-place Text Overlay Editor Widget for Canvas. |

## Regras

- O canvas não guarda estado de documento (Lei do rio nº 1): pixels estão no
  motor, camadas no `LocalLayerManager`.
- Cor, tamanho e pressão chegam do `BrushState` (via `CanvasBrushBinding`);
  ferramenta e opções do `ToolState` (via `CanvasToolBinding`).
- Colaboradores leem o widget por atributos públicos; nenhum escreve atributo
  privado dele.
- A janela principal usa o canvas só pelo contrato `ShellCanvas`
  (`ui/boundary/orchestrator/workspace_port.py`): `run_as_stroke`,
  `forward_key`, `is_busy`, `toggle_grid`, `toggle_rulers`, seleção e câmera.

## Dívida conhecida (medida em 2026-09-24)

`render_widget.py` ainda usa a `BridgeClient` (fachada antiga) para `init_renderer` e `update_view`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `plugins/system/workspace_core/workspace/canvas/renderers`
- `plugins/system/workspace_core/workspace/canvas/tools`
- `plugins/system/workspace_core/workspace/canvas/viewport`
- `ui/core/engine`
- `ui/core/i18n`
- `ui/core/theme`
- `ui/infrastructure/bridge_client`
<!-- /arccc:deps -->
