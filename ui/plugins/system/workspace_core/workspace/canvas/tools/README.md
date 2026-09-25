# `ui/plugins/system/workspace_core/workspace/canvas/tools/` — ferramentas do canvas

**Responsabilidade:** `ToolManager` e um controlador por ferramenta (seleção, forma, transformação, conta-gotas, geometria/guias, texto). Recebem as opções do `ToolState` por `ToolManager.apply_tool_settings` e comandos por `ToolManager.run_command`.

## Porta de entrada

`ToolManager` (criado pelo `RenderWidget`, exposto como `canvas.tool_mgr`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote. |
| `eyedrop_tool_controller.py` | Eyedropper Tool and Color Sampling Controller. |
| `geometry_engine_sync.py` | `push_guides`/`push_symmetry`: escritor único de guias e simetria no motor (contrato `EngineBackend`, sem `hasattr`). |
| `geometry_native_snap.py` | `NativeGeometrySnap`: snap de perspectiva e curvilíneo pelo motor C++ (toggle `LUMENIA_SNAP_NATIVE_*`), com o próprio estado de trava e âncoras. |
| `geometry_snapping_engine.py` | Pure Analytical Geometry Snapping Engine. |
| `geometry_tool_controller.py` | `GeometryToolController`: alças, arrasto e snap das guias e da simetria sobre o `GeometryState` compartilhado; escritor único no motor e no documento ativo (`Document.store_*_state`). |
| `selection_tool_controller.py` | Selection Tool Controller (Magic Wand, Rect, Ellipse, Lasso). |
| `shape_paths.py` | Geometria das formas (linha, retângulo, elipse, polígono, estrela) com Shift e Alt: funções puras, `build_shape_path`. |
| `shape_tool_controller.py` | Vector and Geometric Shape Tool Controller. |
| `text_tool_controller.py` | TextToolController — Controlador de Edição e Inserção de Texto no Canvas. |
| `tool_manager.py` | ToolManager — Centralized Life-Cycle Manager for Canvas Tools. |
| `transform_distort.py` | Transformar -> Distorcer: geometria do quadrilátero de destino. |
| `transform_tool_controller.py` | Free Transform 2D Interactive Tool Controller. |
| `text_overlay_editor.py` | Editor de texto sobre o canvas (caixa editável no lugar), usado só pela ferramenta de texto; veio de `canvas/` em 2026-09-25. |

## Regras

- Não importa o `RenderWidget` (pasta mãe): cada colaborador declara no próprio
  arquivo o contrato que usa do canvas (`TextCanvas`, `ToolCanvas`), e
  `tests/test_canvas_contracts.py` confere que o `RenderWidget` cumpre. Membro
  novo usado entra no contrato. Até 2026-09-25 a anotação de tipo importava a
  pasta mãe: o ciclo canvas ↔ tools.
- Opção nova: validada em `ui/core/tool_settings.py`, entregue por
  `apply_tool_settings` — nunca escrita direto no dicionário do controlador por
  quem está de fora.
- Comando pontual (Aplicar, Desmarcar...): valor em `ui.core.tools.ToolCommand`
  e um caso em `run_command`.
- Guias e simetria moram no `GeometryState` (`ui/core/state`); `guide_state` e
  `sym_state` do controlador são os dois dicionários dele. Quem escreve neles
  (alças, menu, painel de geometria) não chama sync: o controlador escuta o
  estado e leva ao motor e ao documento.

## Dívida conhecida (medida em 2026-09-24)

`ToolManager` e `TextToolController` recebem o canvas pelo contrato (`ToolCanvas`, `TextCanvas`); os demais controladores (seleção, forma, transformação, conta-gotas, geometria) recebem o mesmo objeto sem contrato declarado e usam o que precisam dele (sem ciclo de import).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/document`
- `ui/core/engine`
- `ui/core/geometry`
- `ui/core/state`
- `ui/infrastructure/theme`
- `ui/plugins/system/workspace_core/workspace/canvas/math`
<!-- /arccc:deps -->
