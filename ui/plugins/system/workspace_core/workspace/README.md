# `ui/plugins/system/workspace_core/workspace/` — workspace (área de trabalho)

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
| `document_view_sync.py` | `DocumentViewSync`: mostra o documento ativo no canvas (contexto do motor, câmera, guias, papel, cor) e converte a câmera ↔ navegador; fala com os painéis por sinais. |
| `floating_toolbar.py` | `FloatingToolbar`: barra de ferramentas flutuante e magnética; view do `ToolState`; emite `sizeChanged` para o workspace reposicionar. |
| `floating_toolbar_button.py` | FloatingToolbarButton — botão de ferramenta da barra flutuante. |
| `panel_connections.py` | `PanelConnections`: painéis registrados por `add_panel` e as conexões que caem junto com eles. |
| `pill_handle.py` | PillHandle — Indicador de Reativação de Sidebar. |
| `stroke_preview_sync.py` | StrokePreviewSync — atualiza as miniaturas depois de cada traço. |
| `viewport_container.py` | `TabbedViewportContainer`: abas de documento acima do canvas (trocar, fechar, reordenar). |
| `workspace_container.py` | `WorkspaceContainer`: monta canvas, abas, docas e barras, liga os colaboradores e expõe o contrato do `WorkspaceService` e da janela principal (painéis, desfazer, zoom, status). |
| `workspace_layout.py` | `WorkspaceLayout`: gavetas despinadas, pílulas, barra flutuante (encaixe magnético) e barra secundária; configurações das docas e da barra. |

## Regras

- O `WorkspaceContainer` não tem mixins: cada assunto é um colaborador com
  estado próprio (`WorkspaceLayout`, `DocumentViewSync`, `PanelConnections`,
  `CanvasBrushBinding`, `CanvasToolBinding`, `StrokePreviewSync`).
- Painéis de plugins recebem dados por sinais ligados em `add_panel` (pelo
  `PanelConnections`, que desfaz as conexões no `remove_panel`); o workspace
  não guarda referência a painel nem escreve dentro dele.
- O papel é do `Document` (`set_paper`); o canvas e o painel de camadas só o
  mostram.
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

- `add_panel` conhece dois ids de painéis de plugins (`navigator`, `layers`)
  e a forma de ligar cada um (contrato implícito do `WorkspaceService`). O de
  geometria saiu em 2026-09-24: o painel recebe o `GeometryState` do plugin.
- `floating_toolbar.py` (366 linhas) guarda animações e arrasto no mesmo
  widget.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/dialogs`
- `ui/core/document`
- `ui/core/engine`
- `ui/core/plugins`
- `ui/core/screens`
- `ui/core/state`
- `ui/infrastructure/i18n`
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
- `ui/plugins/system/workspace_core/workspace/canvas`
- `ui/plugins/system/workspace_core/workspace/dock`
- `ui/plugins/system/workspace_core/workspace/secondary_tool_bar`
<!-- /arccc:deps -->
