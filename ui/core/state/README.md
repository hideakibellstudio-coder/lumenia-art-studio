# `ui/core/state/` — estado de aplicação compartilhado

**Em uma frase:** guarda o estado que mais de um componente mostra ou edita
(hoje: o pincel — cor, parâmetros rápidos, preset por ferramenta —, a
ferramenta ativa com as opções de cada ferramenta e as guias/simetria do
documento ativo) e avisa todo mundo por sinal quando ele muda.

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
| `BrushEngineSync` | Único caminho `BrushState → motor`. Também `resync()` após trocar a facade nativa. |
| `ToolState` | QObject com a ferramenta ativa e as opções normalizadas de cada ferramenta (`ui.core.tool_settings`). |
| `ToolEngineSync` | Único caminho `ToolState → motor` para opções que o motor consome (hoje: Smudge). |
| `GeometryState` | QObject com as guias (`guide`) e a simetria (`symmetry`) do documento ativo, dois `SyncedDict` que emitem `guideChanged`/`symmetryChanged` a cada escrita. Escritor único no motor e no documento: o `GeometryToolController` do canvas. |
| `ShapeColorLink` | Regra "as formas usam a cor do pincel": contorno = cor nova; fundo = cor nova com a opacidade de fundo atual. |
| `options_key(tool)` / `is_shape_tool(tool)` | `shape_*` compartilham as opções de `"shapes"`. |
| `install_app_state(registry, backend_provider)` | Cria e registra os serviços acima no `ServiceRegistry` (devolve `AppState(brush, brush_sync, tools, tool_sync, geometry, shape_colors)`). Idempotente. Chamado pela casca. |
| `require(registry, Tipo)` | Busca um serviço obrigatório com mensagem de erro clara. |

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Porta de entrada: `AppState`, `install_app_state`, `require` e os tipos públicos. |
| `brush_params.py` | Enum `BrushParam`, tipos e valores padrão dos parâmetros rápidos; `quick_params_from_preset`. |
| `brush_state.py` | `BrushState`: cor, parâmetros rápidos e preset lembrado por ferramenta. |
| `brush_engine_sync.py` | `BrushEngineSync`: único escritor `BrushState → motor`; `resync()` após trocar de documento. |
| `geometry_state.py` | `GeometryState`: guias e simetria do documento ativo; regras de ângulo por modo, campos do diálogo avançado (`apply_advanced`), centro no documento e troca de documento (`load`). |
| `tool_state.py` | `ToolState`: ferramenta ativa e opções normalizadas por ferramenta; `options_key`, `is_shape_tool`. |
| `state_links.py` | Regras entre estados: `ShapeColorLink` (formas usam a cor do pincel) e `ToolEngineSync` (Smudge → motor). |

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

### Ferramenta ativa e opções

```
barra flutuante ─┐                                         ┌─► CanvasToolBinding (texto, cursor, transformar,
painel de pincel ├─ set_active_tool / update_options ──► ToolState ─┤     opções → ToolManager.apply_tool_settings)
barra secundária │                                         ├─► views: barra flutuante, painel, barra secundária,
atalhos / menu ──┘                                         │   barra lateral da janela
                                                           └─► mensagem de status (traduzida)
```

Antes de 2026-09-24: quatro caminhos escreviam a ferramenta em cada view à
mão, dois com guarda de reentrância; o canvas trocava `shape_rect` por
`shapes` sozinho; a barra secundária mantinha um cache de opções que ninguém
lia e mandava opções de forma ao canvas por dois caminhos.

Telas de opções (páginas do painel de pincel e views da barra secundária)
herdam `ui.core.widgets.tool_options.ToolOptionsView`: mostram o estado em
`show_options`, publicam só o campo editado e nunca republicam ao mostrar.

### Guias e simetria

```
alças do canvas ─┐                                           ┌─► GeometryToolController ──► motor + Document.store_*_state
menu Grade/Réguas├── guide[...] / set_symmetry_mode / ──► GeometryState ─┤     (escritor único)
painel, diálogo ─┘   apply_advanced                          ├─► canvas redesenha
                                                             └─► painel de geometria e diálogo aberto mostram
```

Antes de 2026-09-24 o painel guardava uma cópia própria e a empurrava inteira
para o canvas: a simetria de um documento vazava para o outro e o diálogo
desfazia o ângulo arrastado no canvas (`tests/test_geometry_state.py`).

### Regras entre estados (`state_links.py`)

Quando mudar um estado deve mudar outro (ou o motor), a regra fica aqui, num
lugar só — nunca em cada tela que a conhece. Até 2026-09-24 "formas usam a
cor do pincel" estava implementada três vezes (canvas, barra secundária,
painel) e uma das cópias zerava a opacidade do fundo.

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
   (`set_active_document_context`) chama `brush_sync.resync()` em
   seguida. Hoje: `WorkspaceDocSyncMixin._on_active_document_changed` e
   `MainWindow` ao criar documento.
6. A cor salva por documento (`Document.saved_color`) é gravada ao sair da aba
   e aplicada ao estado ao voltar; o estado continua sendo a fonte única.

## Consumidores atuais

- `plugins/ui/brush_plugin/panel.py`, `brush_dropdown.py`, `advanced_panel/`
- `plugins/ui/color_plugin/panel.py`
- `plugins/system/workspace_core/workspace/canvas_brush_binding.py`,
  `canvas_tool_binding.py`, `floating_toolbar.py`, `secondary_tool_bar/`,
  `workspace_document_sync.py`
- `ui/core/widgets/tool_options/` (páginas de opções, via `ToolOptionsView`)
- `ui/boundary/orchestrator/main_window.py`, `main_window_menu_actions.py`,
  `main_window_tool_camera_actions.py`

## Testes

`tests/test_brush_state.py`, `tests/test_tool_state.py` e
`tests/test_state_links.py` (contratos dos estados e das regras), `tests/test_brush_panel_structure.py` (painel como view),
`tests/test_tool_settings_contract.py` (opções chegando aos controladores).

## Dependências internas

`ui/core/engine` (contrato `EngineBackend`, só para tipo), `ui/core/plugins`
(`ServiceRegistry`) e `ui/core` (`tool_settings`, `tools`). Nada de
`plugins/*`, nada de widgets. Medidas pelo teste
`tests/test_arccc_package_docs.py`:

<!-- arccc:deps -->
- `ui/core`
- `ui/core/engine`
- `ui/core/geometry`
- `ui/core/plugins`
<!-- /arccc:deps -->
