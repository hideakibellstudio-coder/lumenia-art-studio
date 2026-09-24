# `ui/core/state/` — estado de aplicação compartilhado

**Em uma frase:** guarda o estado que mais de um componente mostra ou edita
(hoje: cor ativa, parâmetros rápidos e preset por ferramenta do pincel) e
avisa todo mundo por sinal quando ele muda.

## Por que existe

Até 2026-09-24 a cor e os parâmetros do pincel viviam em seis lugares
(workspace, canvas, painel de pincel, painel avançado, dropdown de presets,
perfil do motor). Um mediador (`WorkspaceBrushMixin`) mantinha tudo em
sincronia à mão, lendo e escrevendo os widgets internos dos outros plugins
com `hasattr(dock, "qs_size")`, `d._adv_panel.slider_size.setValue(...)`.
O painel avançado escrevia no motor direto **e** avisava o painel principal,
que avisava o workspace, que escrevia no motor de novo. Ao trocar de aba, só o
preset era reaplicado e o tamanho ajustado à mão se perdia.

## Porta de entrada

Tudo é importado de `ui.core.state` (o `__init__.py`). Os módulos internos
podem mudar sem aviso.

| Símbolo | O que é |
|---|---|
| `BrushState` | QObject com a cor, os parâmetros rápidos e o preset lembrado por ferramenta. |
| `BrushParam` | Enum canônico dos parâmetros rápidos (Lei do Rio nº 4). Unidades no docstring de `brush_params.py`. |
| `BrushEngineSync` | Único caminho `BrushState → motor`. Também `resync(tool)` após trocar a facade nativa. |
| `install_app_state(registry, backend_provider)` | Cria e registra os serviços acima no `ServiceRegistry`. Chamado pela casca. |
| `require(registry, Tipo)` | Busca um serviço obrigatório com mensagem de erro clara. |

## Fluxo

```
widget que edita ──set_color / set_value / select_preset──► BrushState
                                                                │ colorChanged / paramChanged / presetSelected
                     ┌──────────────────────────────────────────┼─────────────────────────────┐
                     ▼                                          ▼                             ▼
       views (painel de pincel, roda de cor,        BrushEngineSync ──► EngineBackend    CanvasBrushBinding
       painel avançado, barra secundária)           (único escritor no motor)           (canvas: cursor, balde,
                                                                                         conta-gotas → estado)
```

## Regras do contrato

1. **Quem edita chama o estado; quem mostra escuta o estado.** Um widget pode
   fazer as duas coisas (a roda de cor edita e mostra).
2. **Valor igual não emite.** Por isso nenhuma view precisa de guarda de
   reentrância ou de laço de `blockSignals` para não entrar em loop.
3. **Ninguém chama `set_brush_size/opacity/color/...` no backend** para os
   parâmetros que `BrushParam` conhece. Parâmetros que só o painel avançado
   mostra (jitter, ângulo, textura...) continuam indo direto ao motor pelo
   `PanelEngineBridgeMixin` — e passam a vir para cá no dia em que uma
   segunda tela precisar mostrá-los.
4. **Injeção pelo construtor.** Widgets recebem o `BrushState` como
   argumento. Plugins o obtêm com
   `require(self.context.service_registry, BrushState)`. Nenhum widget faz
   busca global.
5. **Troca de documento:** quem troca o contexto do motor
   (`set_active_document_context`) chama `brush_sync.resync(ferramenta)` em
   seguida. Hoje: `WorkspaceDocSyncMixin._on_active_document_changed` e
   `MainWindow` ao criar documento.
6. A cor salva por documento (`Document.saved_color`) é gravada ao sair da aba
   e aplicada ao estado ao voltar; o estado continua sendo a fonte única.

## Consumidores atuais

- `plugins/ui/brush_plugin/panel.py`, `brush_dropdown.py`, `advanced_panel/`
- `plugins/ui/color_plugin/panel.py`
- `plugins/system/workspace_core/workspace/canvas_brush_binding.py`
- `plugins/system/workspace_core/workspace/workspace_document_sync.py`
- `ui/boundary/orchestrator/main_window.py`, `main_window_menu_actions.py`

## Testes

`tests/test_brush_state.py` (contrato do estado e da sincronização com o
motor) e `tests/test_brush_panel_structure.py` (painel como view do estado).

## Dependências permitidas

`PySide6.QtCore/QtGui`, `ui.core.engine.backend` (contrato do motor, só para
tipo), `ui.core.plugins.registry` (ServiceRegistry). Nada de `plugins.*`,
nada de widgets.
