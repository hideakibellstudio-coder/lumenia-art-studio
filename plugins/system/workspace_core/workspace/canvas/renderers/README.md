# `plugins/system/workspace_core/workspace/canvas/renderers/` — pintores do canvas

**Responsabilidade:** desenham por cima dos pixels do motor: fundo xadrez, seleção (formigas), gizmo de transformação, prévia de forma, lupa do conta-gotas, guias (simetria, perspectiva, réguas) e o anel/cursor da ferramenta.

## Porta de entrada

Importar por módulo; os mais usados: `geometry_overlay_renderer.GeometryOverlayRenderer`, `tool_cursor_renderer.ToolCursorRenderer`, `overlay_renderer.OverlayRenderer`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote. |
| `canvas_background_renderer.py` | Canvas Background and Transparency Pattern Renderer. |
| `geometry_overlay_renderer.py` | Geometry Overlay Renderer Facade. |
| `overlay_renderer.py` | Canvas Overlays Renderer (Selection Marching Ants, Transform Gizmo, Shape Preview, Loupe HUD). |
| `perspective_grid_renderer.py` | Perspective and Curvilinear 6P Grid Renderer. |
| `ruler_grid_renderer.py` | Straight and Curve Ruler Renderer. |
| `symmetry_overlay_renderer.py` | Symmetry Guide and Axis Renderer. |
| `tool_cursor_renderer.py` | Tool Cursor Renderer — Renderizador de Cursores de Precisão e Anéis de Contorno. |

## Regras

Pintor recebe `QPainter` e dados; não guarda estado entre pinturas e não altera o widget. Quem decide o que pintar é o `ViewportRenderer` (`canvas/viewport`).

## Dívida conhecida (medida em 2026-09-24)

Os pintores são classes de métodos estáticos que recebem o widget inteiro em vez dos dados que usam.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `plugins/system/workspace_core/workspace/canvas/math`
- `plugins/system/workspace_core/workspace/canvas/tools`
- `ui/core`
- `ui/core/config`
- `ui/core/theme`
<!-- /arccc:deps -->
