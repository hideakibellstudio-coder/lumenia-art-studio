# `plugins/system/workspace_core/workspace/` — workspace (área de trabalho)

**Responsabilidade:** a área central da janela: abas de documento com o canvas, docas laterais com os painéis dos plugins, barra de ferramentas flutuante, barra de opções da ferramenta, e as ligações entre o estado compartilhado e o canvas.

## Porta de entrada

`WorkspaceContainer` (criado só pelo `WorkspaceCore`). Plugins usam o `WorkspaceService`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `WorkspaceContainer` e peças do workspace. |
| `canvas_brush_binding.py` | CanvasBrushBinding — mostra o BrushState no canvas. |
| `canvas_overlay.py` | CanvasOverlay — Overlay de Interceptação de Eventos (Totalmente Invisível). |
| `canvas_tool_binding.py` | CanvasToolBinding — aplica o ToolState ao canvas. |
| `dock_system.py` | AdvancedDockSystem — Sistema de Gavetas Dinâmicas com Auto-Recolhimento (ARCcC v2). |
| `floating_toolbar.py` | `FloatingToolbar`: barra de ferramentas flutuante e magnética; view do `ToolState`; emite `sizeChanged` para o workspace reposicionar. |
| `floating_toolbar_button.py` | FloatingToolbarButton — botão de ferramenta da barra flutuante. |
| `panel_bindings.py` | Registro reversível das conexões criadas por painéis dinâmicos. |
| `pill_handle.py` | PillHandle — Indicador de Reativação de Sidebar. |
| `stroke_preview_sync.py` | StrokePreviewSync — atualiza as miniaturas depois de cada traço. |
| `viewport_container.py` | `TabbedViewportContainer`: abas de documento acima do canvas (trocar, fechar, reordenar). |
| `workspace_actions.py` | WorkspaceActionsMixin — Ações de Visualização, Histórico e Limpeza do Canvas. |
| `workspace_container.py` | WorkspaceContainer. |
| `workspace_document_sync.py` | Document and Camera synchronization mixin for WorkspaceContainer. |
| `workspace_layout_manager.py` | Layout and Dock management mixin for WorkspaceContainer. |

## Regras

- Ligações estado → canvas são colaboradores com estado próprio:
  `CanvasBrushBinding` (cor, tamanho, pressão; cor capturada → estado) e
  `CanvasToolBinding` (ferramenta ativa e opções → canvas). Nenhum mixin do
  workspace escreve em widget de plugin.
- Barras flutuantes pedem reposicionamento por sinal (`sizeChanged`), nunca
  procurando `update_toolbar_position` no pai.
- Câmera: quem muda zoom/pan/rotação chama `canvas.publish_view()`.
- A janela principal usa o `WorkspaceContainer` só pelo contrato
  `ui/boundary/orchestrator/workspace_port.py` (`ShellWorkspace`); método que
  a casca passe a usar entra lá e no teste da porta.
- Mensagens para a barra de status: `show_status(...)` emite `statusMessage`,
  que a janela liga (nada de `self.window().statusBar()`). Painéis de plugin
  usam `WorkspaceService.show_status`.

## Dívida conhecida (medida em 2026-09-24)

- `WorkspaceContainer` ainda é composto por mixins (`workspace_actions`,
  `workspace_document_sync`, `workspace_layout_manager`, `panel_bindings`)
  que leem e escrevem atributos uns dos outros por `self`.
- `add_panel` conhece ids de painéis de plugins (navegador, camadas,
  geometria) e `workspace_document_sync` alcança `_layers_panel.paper_widget`.
- `dock_system.py` é o arquivo com mais acesso a privados alheios do pacote.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `plugins/system/workspace_core/workspace/canvas`
- `plugins/system/workspace_core/workspace/dock`
- `plugins/system/workspace_core/workspace/secondary_tool_bar`
- `ui/core`
- `ui/core/dialogs`
- `ui/core/document`
- `ui/core/engine`
- `ui/core/i18n`
- `ui/core/screens`
- `ui/core/state`
- `ui/core/theme`
<!-- /arccc:deps -->
