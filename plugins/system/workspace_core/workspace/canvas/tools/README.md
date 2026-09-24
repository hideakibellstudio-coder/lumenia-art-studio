# `plugins/system/workspace_core/workspace/canvas/tools/` — ferramentas do canvas

**Responsabilidade:** `ToolManager` e um controlador por ferramenta (seleção, forma, transformação, conta-gotas, geometria/guias, texto). Recebem as opções do `ToolState` por `ToolManager.apply_tool_settings` e comandos por `ToolManager.run_command`.

## Porta de entrada

`ToolManager` (criado pelo `RenderWidget`, exposto como `canvas.tool_mgr`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `eyedrop_tool_controller.py` | Eyedropper Tool and Color Sampling Controller. |
| `geometry_snapping_engine.py` | Pure Analytical Geometry Snapping Engine. |
| `geometry_tool_controller.py` | Tool Controller for Symmetry, Guides, and Snapping Interactions. |
| `selection_tool_controller.py` | Selection Tool Controller (Magic Wand, Rect, Ellipse, Lasso). |
| `shape_tool_controller.py` | Vector and Geometric Shape Tool Controller. |
| `text_tool_controller.py` | TextToolController — Controlador de Edição e Inserção de Texto no Canvas. |
| `tool_manager.py` | ToolManager — Centralized Life-Cycle Manager for Canvas Tools. |
| `transform_distort.py` | Transformar -> Distorcer: geometria do quadrilátero de destino. |
| `transform_tool_controller.py` | Free Transform 2D Interactive Tool Controller. |

## Regras

- Opção nova: validada em `ui/core/tool_settings.py`, entregue por
  `apply_tool_settings` — nunca escrita direto no dicionário do controlador por
  quem está de fora.
- Comando pontual (Aplicar, Desmarcar...): valor em `ui.core.tools.ToolCommand`
  e um caso em `run_command`.

## Dívida conhecida (medida em 2026-09-24)

`geometry_tool_controller.py` está na parede dos 450 linhas. Os controladores recebem o widget inteiro (dependência de mão dupla com `canvas/`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `plugins/system/workspace_core/workspace/canvas`
- `plugins/system/workspace_core/workspace/canvas/math`
- `ui/core`
- `ui/core/document`
- `ui/core/engine`
- `ui/core/geometry`
<!-- /arccc:deps -->
