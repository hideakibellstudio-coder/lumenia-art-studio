# `ui/plugins/system/workspace_core/workspace/canvas/viewport/` — vista do canvas

**Responsabilidade:** os colaboradores do `RenderWidget`: câmera (zoom, pan, rotação, espelhamento), roteamento de eventos, cursor e seu anel, ciclo do traço com regiões sujas, e a pintura da viewport com suas medições.

## Porta de entrada

Criados pelo `RenderWidget` (`camera`, `input_router`, `cursor_ctrl`, `stroke`, `viewport_renderer`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote. |
| `camera_controller.py` | Camera and Viewport 2D Navigation Controller. |
| `camera_proxies.py` | CanvasCameraProxies — zoom/pan/rotação/espelhamento do canvas lidos da câmera. |
| `canvas_stroke_pipeline.py` | CanvasStrokePipeline — ciclo de vida do traço interativo e regiões sujas da tela. |
| `cursor_controller.py` | CanvasCursorController — Controlador Modular do Cursor no Canvas (ARCcC). |
| `input_router.py` | `CanvasInputRouter`: ponteiro (apertar, arrastar, soltar) → ferramentas; contrato `RouterCanvas`. |
| `key_router.py` | `CanvasKeyRouter`: teclado (espaço, Delete, atalhos de seleção, teclas da transformação); contrato `KeyCanvas`. Separado de `input_router.py` em 2026-09-25. |
| `still_pointer.py` | `StillPointerFeeder`: durante o traço, repete a última entrada a cada 16 ms quando nada chega há 20 ms (mouse parado), com o instante avançado; sem isso a linha estabilizada parava atrás do cursor. |
| `pointer_sample.py` | `PointerSample` e `event_time`: posição, pressão, botão, inclinação, rotação, borracha e instante lidos de um evento de mouse ou caneta. |
| `guide_layer_cache.py` | `GuideLayerCache`: a camada estática das guias e da simetria (linhas, curvas, alças) pintada numa imagem e reaproveitada enquanto guia, simetria, câmera, tamanho e tema não mudam; a parte que segue o ponteiro continua ao vivo. Sem ela, cada movimento do mouse retraçava a guia inteira (curvilinear completa: 69 ms por repintura no Windows, 8 ms com o cache; medido em 2026-10-12, `benchmarks/app_guides_paths.py`). Zoom e pan repintam a camada a cada passo. |
| `viewport_renderer.py` | ViewportRenderer — pinta o canvas: papel, pixels do motor, overlays e cursor. |

## Regras

- Não importa o `RenderWidget` (pasta mãe): cada colaborador declara no próprio
  arquivo o contrato que usa do canvas (`RouterCanvas`, `KeyCanvas`, `ViewportCanvas`, `StrokeCanvas`, `CursorCanvas`), e
  `tests/test_canvas_contracts.py` confere que o `RenderWidget` cumpre. Membro
  novo usado entra no contrato. Até 2026-09-25 a anotação de tipo importava a
  pasta mãe: o ciclo canvas ↔ viewport.

Cada colaborador é dono do que lê e escreve (ex.: o anel pintado é do `CanvasCursorController`, o fim do último traço é do `CanvasStrokePipeline`). Até 2026-09-24 eram classes de métodos estáticos que escreviam atributos privados do widget.

## Dívida conhecida (medida em 2026-09-24)

`input_router.py` concentra o roteamento do ponteiro de todas as ferramentas num arquivo só (cadeia de `if`; `handle_pointer_press` com complexidade 47). O teclado saiu para `key_router.py` em 2026-09-25.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/plugins/system/workspace_core/workspace/canvas/renderers`
- `ui/core`
- `ui/core/document`
- `ui/core/engine`
- `ui/infrastructure/i18n`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
