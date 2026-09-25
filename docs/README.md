# Documentação técnica — Lumenia Art Studio & ALADYN ENGINE

Reorganizada em 2026-09-20 por prioridade de uso: primeiro o que precisa ser
corrigido nesta fase, depois referência estável, depois o que é só visão de
futuro, por último o histórico já fechado. A numeração das pastas é ordem de
leitura, não importância absoluta — mas se você só vai ler uma pasta, leia a `01-`.

## Mapa

### `01-correcao-da-base/` — ativo, leia primeiro
O que vale a pena aplicar **agora**, nesta fase de correção da base (sem
features novas). Começa por `01-pendencias-atuais.md`, o painel vivo de
status. Os outros arquivos da pasta são o *como* e o *com que ferramenta*.

### `02-arquitetura/` — referência estável
Como o sistema é estruturado hoje: framework ARCcC, visão geral do sistema,
motor ALADYN e a ponte PyBind11, modelo de documento, subsistema de plugins.
Consulte quando precisar entender uma área antes de mexer nela, não quando
procurar o que está pendente.

### `03-guias/` — referência operacional estável
Ambiente de desenvolvimento, compilação e distribuição.

### `04-especificacoes/` — formais, estáveis
Formato de arquivo `.lmn` e gestão de cor (LittleCMS/ICC).

### `05-visao-e-futuro/` — visão estratégica e evolução de produto
Visão estratégica de produto, benchmark competitivo de mercado (`03-benchmark-competitivo-e-rotas-de-produto.md`) e roadmap do pipeline de cor 16-bit/float. Norteia as decisões de refinamento da branch `feature/evolucao-produto`.

### READMEs por pasta de código — leia antes de mexer
Cada pasta do repositório (`ui/` com os plugins em `ui/plugins/`, `engine/`, `bridge/`, `tests/`, `docs/`...) tem um `README.md` com a responsabilidade,
a porta de entrada, a tabela de arquivos, as regras, a dívida conhecida e as
dependências internas medidas (bloco `arccc:deps`). O teste
`tests/test_arccc_package_docs.py` falha se um arquivo ou import novo não
estiver lá. Como as peças conversam: `02-arquitetura/06-contratos-entre-componentes.md`.

### `historico/` — encerrado, não numerado de propósito
Auditorias já resolvidas (F-001 a F-031) e o panorama de estado de
2026-09-15 que `01-correcao-da-base/01-pendencias-atuais.md` substituiu.
É proveniência — explica *por que* uma regra ou teste existe — nunca lista de
tarefas.

---

## Changelog — o que foi feito, por quê, e com base em quê

> Toda entrada nova vai no topo. Formato: data, o que foi feito, por que
> agora, em qual documento (deste `docs/` ou do Claude Project) isso estava
> descrito, e qual era o objetivo declarado daquele documento. Não apague
> entradas antigas — este arquivo é o rastro de decisão do projeto.

### 2026-09-25 — Estrutura física do ARCcC, conferência do Windows e próximas tasks
**Base:** pedidos do usuário nesta sessão (Claude Code): terminar a estrutura
física do ARCcC (passos 1 a 5 de `02-arquitetura/07-auditoria-da-estrutura-fisica.md`),
fazer os commits passarem no Windows mesmo com o agente em Linux, tirar o CI
do push, e um relatório de estado do projeto em relação ao ARCcC e ao mercado.
**O que mudou:** serviços transversais em `ui/infrastructure`; motor C++ em
camadas (`utils` → `infrastructure` → `core` → `boundary`) sem ciclo de pasta
e com a ponte entrando só por `AladynEngine.hpp`; plugins em `ui/plugins`;
`scripts/check_windows_build.py` (MinGW-w64) e
`tests/test_windows_portability.py`; CI só à mão (`AGENTS.md` seção 5.1).
**Próximas tasks registradas:** engenharia sem feature em
`01-correcao-da-base/01-pendencias-atuais.md` ("Próximas tasks", 18 itens);
produto em `05-visao-e-futuro/03-benchmark-competitivo-e-rotas-de-produto.md`
(Rota C comercial, paridade e posicionamento).
**Números medidos** (Linux, Python 3.11, offscreen, base `9038c9c`): 925
testes, 920 passam e 5 pulados; cobertura de `ui/` 78%; 114 de 114 pastas
com README; 0 ciclos entre pastas do motor (eram 9) e 2 no Python (eram 9);
68 de 68 `.cpp` compilam para Windows com MinGW (escalar e AVX2).

### 2026-09-24 — Espaguete desfeito por contrato, catracas e README por pasta
**Base:** pedido do usuário nesta sessão (Claude Code): pôr tudo o que já
existe em conformidade com o ARCcC, sem espaguete, e documentado a ponto de
outros agentes trabalharem sem recriá-lo. Documento de referência:
`ARCcC - Atomic Recursive Componentization by Contract` (enviado pelo usuário).
**Diagnóstico medido:** o teto de linhas era cumprido fatiando arquivos, não
responsabilidades (mixins e funções soltas que recebem o dono e mexem nos
privados dele). Catraca nova `tests/test_arccc_coupling_ratchet.py`.
**O que mudou:** estado compartilhado em `ui/core/state` (pincel, ferramenta,
regras entre estados) injetado pelo construtor; camadas com um caminho só até
o motor; canvas com colaboradores de estado próprio e uma saída de câmera
(`publish_view`); barra secundária e páginas de opções como views do
`ToolState`; `ToolCommand`; CI verde (scipy no lock, testes de tempo pelo
melhor de 5); limpeza de janelas dos testes com o GC desligado (crash do
PySide achado com gdb/valgrind); README em todas as 62 pastas de código com
teste que os mantém verdadeiros; AGENTS.md seção 4.2.
**Números medidos** (Linux, Python 3.11, offscreen): 835 testes passam, 5
pulados; acoplamento `hasattr` 781 → 465, `getattr` literal 408 → 265,
privado alheio 349 → 71, `except` silencioso 15 → 0, núcleo → plugin 2 → 0;
0 arquivos na Zona Vermelha, 5 na parede. CI do GitHub (Windows 3.11–3.14 e
AVX2) verde no commit `5046cec`. Os bugs corrigidos, cada um medido antes e
depois, estão nas mensagens de commit do branch `claude/zealous-galileo-38k67d`.

### 2026-09-23 — Decisões do usuário: promessas falsas viram funções reais
**Base:** `claude/correcoes-e-decisoes-2026-09-22.md` (Claude Project), seção
"Decisões" — o usuário escolheu desenvolver as funções em vez de escondê-las,
seguir a recomendação sobre os `hasattr` e adiar o 16-bit.
**Números medidos** (Windows, Python 3.14): suíte completa verde (796
testes), `navigator_verify` com 0 `confirmed_violation`.
**O que mudou:** Seleção → Modificar, Transformar → Distorcer e Harmonias
implementados de ponta a ponta (motor C++ onde há pixels, UI só liga);
plano B dos `hasattr` do grupo A passa a avisar no log; `backend_protocols.py`
dividido antes de crescer. Detalhe em `01-correcao-da-base/01-pendencias-atuais.md`
e `05-visao-e-futuro/03-benchmark-competitivo-e-rotas-de-produto.md` (Rota 0
concluída).

### 2026-09-22 — Análise completa e correção dos achados (sessão Claude/Cowork)
**Base:** `claude/analise-completa-projeto-2026-09-22.md` (Claude Project) —
análise com medição ao vivo; o usuário pediu para corrigir tudo o que ela apontou.
**Números medidos no fim da sessão** (Windows, Python 3.14): suíte completa
verde (762 testes, 110–135 s), `navigator_verify` com 0 `confirmed_violation`,
0 arquivos na Zona Vermelha e nenhuma exceção de LOC.
**O que mudou (resumo; detalhe em `01-correcao-da-base/01-pendencias-atuais.md`):**
- Motor: 3 C++ divididos (fim da Zona Vermelha); prévia nativa do pincel
  restaurada (sumiu em 2026-08-25) com dois defeitos dormentes corrigidos.
- Vazamentos reais achados pelo novo gate de sessão longa
  (`scripts/soak_full_session.py`): cada documento aberto/fechado deixava
  ~89 KB (lambda no `Document` + botão de aba não destruído) — corrigidos,
  ~5 KB residuais por documento. Lambdas em sinais de singletons trocados por
  métodos ligados.
- Ponte: `WgpuRustBackend` removido; 5 varreduras `topLevelWidgets` →
  `canvas_access.py`; guardas `hasattr` numa lista travada por teste.
- Governança: catracas (`test_river_ratchets.py`, `test_i18n_keys_exist.py`,
  `test_hardcoded_colors_ratchet.py`); 25 chaves de tradução; CI com 3.14;
  testes renomeados por assunto (27 arquivos); suíte ≈3× mais rápida.
- Navigator: 3 arquivos acima do próprio teto divididos (saída idêntica),
  extrator `xl-contracts-v10`.
- Documentação: `AGENTS.md` (faixa amarela alinhada a 300, censo medido, regra
  de números medidos), benchmark de produto reescrito com o estado real de cada
  item (5 já existiam; 3 eram promessas falsas da interface).

### 2026-09-21 — Criação da Branch `feature/evolucao-produto` e Benchmark Competitivo de Mercado
**O que foi feito:** Transição formal da fase de correção da base para a fase de evolução de produto:
1. *Criação da Branch:* branch local `feature/evolucao-produto` criada e ativada a partir de `main` (commit `a41b41c`).
2. *Documento Direcionador de Produto:* criação de `docs/05-visao-e-futuro/03-benchmark-competitivo-e-rotas-de-produto.md` mapeando as lacunas competitivas do Lumenia frente aos líderes de mercado (Procreate, Clip Studio Paint, Krita, Infinite Painter e Photoshop), estruturando as 5 rotas de refinamento coeso pelos 5 Grandes Rios.

### 2026-09-21 — Descida ao Núcleo Primordial C++ e Fechamento Ascendente dos 5 Grandes Rios (Rodada 14)
**O que foi feito:** Décima quarta rodada de auditoria concêntrica expandindo a metodologia `lumenia-satellite-audit` até a profundidade máxima física e validando a subida dos 5 Rios:
1. *Expansão Metodológica para 6 Camadas Concêntricas*: atualização da skill (`.agents/skills/lumenia-satellite-audit/SKILL.md`) e da documentação canônica (`docs/01-correcao-da-base/06-auditoria-orbital-decomposta.md`), incorporando formalmente a Órbita 5 (Ponte PyBind11 e os 11 Orquestradores de Borda) e a Órbita 6 (Núcleo Físico Primordial: `TileGrid`, `TileUndoManager`, `Compositor`, `DabRenderer` SIMD).
2. *Formalização do Retorno Ascendente (The Complete Ascending River Loop)*: definição e verificação dos 5 Grandes Rios de propagação bottom-up: Rio 1 (Traço & Estabilizador), Rio 2 (Câmera & Viewport), Rio 3 (Camadas & Histórico), Rio 4 (Seleção & Transformação) e Rio 5 (Cor & Perfis Cromáticos).
3. *Auditoria de Integridade da Fronteira PyBind11 e Orquestradores*: validação da segurança de memória de `BufferContract.hpp` (prevenção contra overflow aritmético via `checkedRasterBytes` e snapshots imutáveis `pixelSnapshot` sem vazamento de ponteiros crus) e garantia de invocação sistemática de `DocumentContext::touch()` e dirty tracking.
4. *Suíte Dedicada de Integridade Primordial e Ascendente*: criação de `tests/test_native_core_invariants_and_rivers.py` cobrindo a descida e a subida dos 5 rios.
5. *Governança Estrita ARCcC*: todos os arquivos criados ou modificados estritamente na Zona Verde (< 450 LOC). 100% de testes verdes na suíte global.

### 2026-09-21 — Sincronização Bidirecional Viewport/Navigator e Dirty Tracking de Camadas (Rodada 13)
**O que foi feito:** Décima terceira rodada de auditoria e saneamento concêntrico aplicando `lumenia-satellite-audit`:
1. *Alinhamento dos Ícones de Flip no Navigator*: correção dos ícones SVG em `NavigatorControls` (`ui/plugins/panels/navigator_plugin/panel.py`), associando `flip-vertical` a `btn_fliph` e `flip-horizontal` a `btn_flipv`, alinhando a representação visual com a percepção do usuário e preservando conexões de sinal 1:1.
2. *Sincronização Bidirecional Viewport $\leftrightarrow$ Navigator*: os setters de `flip_x` e `flip_y` em `canvas_compat.py` agora emitem `cameraChanged.emit(...)` de forma idempotente quando alterados, garantindo que espelhamentos acionados externamente (menu principal, atalhos) atualizem imediatamente o viewport no painel do Navigator.
3. *Completude de Rastreamento Dirty em Camadas (`aladyn_layer_mixin.py`)*: inclusão sistemática de chamadas a `self._mark_document_dirty(...)` em todas as mutações da pilha de camadas (`add_layer`, `remove_layer`, `duplicate_layer`, `merge_layer_down`, `flatten_group`, `add_group`, `add_filter_layer`, `reorder_layer`, `reorder_layers`, `set_layer_parents`, `set_layer_blend_mode`, `set_layer_opacity`, `set_layer_visibility`, `set_layer_lock`, `set_layer_alpha_lock`, `set_layer_clipping_mask`, `set_layer_name`, `set_filter_params`), fechando a paridade 1:1 com o `ctx.touch()` de `LayerStackOrchestrator` do C++.
4. *Rastreamento Dirty em Geometria, Transações e Recursos*: adição de `_mark_document_dirty` em `resize`, `apply_prepared_geometry`, `commit_layer_transaction` (`aladyn.py`), `set_selection_mask_buffer` (`aladyn_selection_mixin.py`) e `set_canvas_resource` (`aladyn_resources_mixin.py`).
5. *Suíte Modular e Governança ARCcC*: criação de `tests/test_dirty_tracking_layers_and_navigator_flip.py` (7/7 testes verdes). Todos os arquivos modificados rigorosamente na Zona Verde (< 450 LOC). 100% de testes verdes na suíte global (670+ testes).

### 2026-09-21 — Saneamento dos Botões de Flip do Navigator e Fronteira Primordial C++ (Rodada 12)
**O que foi feito:** Décima segunda rodada de saneamento concêntrico aplicando `lumenia-satellite-audit`:
1. *Alinhamento dos Botões de Flip no Navigator*: correção no `NavigatorControls` (`ui/plugins/panels/navigator_plugin/panel.py`), onde `btn_fliph` estava indevidamente conectado a `flipVRequested.emit` e `btn_flipv` conectado a `flipHRequested.emit`. Alinhamento 1:1 restabelecido (`btn_fliph` $\to$ `flipHRequested`, `btn_flipv` $\to$ `flipVRequested`).
2. *Guard Resiliente em MDI (`aladyn_mdi_mixin.py`)*: substituição de condicional inalcançável por `if hasattr(facade, "set_render_options"):` com suporte a fallbacks granulares (`set_low_latency`, `set_linear_gamma`, `set_deep_color`) tanto na inicialização quanto na re-ativação de documentos.
3. *Rastreamento Dirty em Operações Nativas C++*: inclusão de chamadas a `self._mark_document_dirty(...)` em `clear_canvas`, `clear_layer`, `undo`, `redo` (`aladyn_layer_mixin.py`), e em `flood_fill`, `fill_area` e `end_stroke` (`aladyn_stroke_mixin.py`), garantindo sincronia perfeita do indicador de documento não-salvo.
4. *Suíte Modular e Governança ARCcC*: criação de `tests/test_render_options_and_native_dirty_tracking.py` (6/6 testes verdes). Todos os arquivos modificados abaixo do limite de 450 LOC (Zona Verde). 100% de testes verdes em toda a suíte do projeto.

### 2026-09-21 — Saneamento Orbital na Fronteira Primordial C++: Coerção de Cores, Dirty Tracking e Paridade no Menu (Rodada 11)
**O que foi feito:** Descida orbital até a fronteira primordial de transição Python $\leftrightarrow$ C++ (`PaintEngineFacade` / `aladyn_engine_native` / bindings PyBind11 / `TileGrid`), integrando a metodologia `lumenia-satellite-audit`, "O Curso do Rio" e ARCcC-Navigator. Saneadas 5 inconsistências fundamentais de borda:
1. *Coerção Resiliente de Cores na Borda C++ (`to_native_color_rgba`)*: unificada a conversão de cores em `ui/infrastructure/bridge_client/aladyn_buffers.py`, eliminando risco de `AttributeError` em `fill_selection_on_active_layer` e divergências entre `fill_area` e `flood_fill`. Suporte nativo a `ColorRGBA`, `QColor`, tuplas/listas normalizadas (0.0-1.0) ou inteiras (0-255) e duck-typing.
2. *Rastreamento Canônico de Dirty do Documento (`_mark_document_dirty`)*: adicionada notificação de alteração de documento nas mutações nativas de raster (`fill_selection_on_active_layer`, `delete_selection_on_active_layer`, `commit_transform`, `flip_active_layer`, `rotate_active_layer_90` e `paste_rgba_buffer_on_active_layer`), garantindo que o asterisco de aba (`*`) e autosave/recovery reflitam alterações visuais.
3. *Simetria de Sinais de Traço no Menu (`MainWindowMenuActionsMixin`)*: criado helper unificado `_emit_stroke_wrap(action)` envelopando preenchimento (`fill_active_selection_or_canvas`), corte (`cut_selection_or_layer_to_clipboard`), colagem (`paste_clipboard`) e limpeza (`clear_active_layer`) no par balanceado `strokeStarted.emit()` e `try ... finally: strokeFinished.emit()`, garantindo sincronização instantânea das miniaturas das camadas e do navegador (`_on_stroke_finished_sync_previews`), além da atualização dos estados de Undo/Redo.
4. *Resolução Canônica de Cor no Menu*: `fill_active_selection_or_canvas` agora prioriza a cor ativa selecionada na interface (`canvas_widget.active_color`), eliminando preenchimentos com cor desatualizada.
5. *Governança e Poda de Resíduos de IA*: eliminação de blocos `if True:` órfãos em `main_window_menu_actions.py`, mantendo o arquivo em 418 LOC (Zona Verde < 450). Nova suíte modular `tests/test_engine_boundary_color_and_signals.py` (4/4 testes verdes, 263 LOC). 100% de testes verdes em toda a suíte global (670+ testes). Commit atômico.

### 2026-09-21 — Saneamento e Auditoria Orbital Concêntrica dos Subsistemas Satélites (Rodadas 9 e 10)
**O que foi feito:** Aplicação da nova metodologia e skill `lumenia-satellite-audit` (Concentric Satellite Peeling) integrada com "O Curso do Rio" e ARCcC-Navigator, rastreando órbitas concêntricas ao redor dos núcleos saneados até a base primordial. Identificadas e corrigidas 13 inconsistências críticas em UI, Menus, Ferramentas Satélites, Plugins e Viewport:
1. *Balde de Tinta (`do_flood_fill`)*: preenchimento em preto silencioso corrigido com a propriedade canônica `active_color` e inicialização de `_active_draw_color` no `RenderWidget` e `CanvasCompatMixin`; garantia de simetria de sinais via `try ... finally: strokeFinished.emit()`.
2. *Ciclo de Vida do `TextToolController`*: simetria estrita com `strokeStarted.emit()` em `open_editor()` e `strokeFinished.emit()` garantido em `commit()` e `cancel()`, destravando docas e gavetas despinadas.
3. *Simetria de Sinais em Exclusão via Teclado*: Delete/Backspace em `input_router.py` agora dispara paridade 1:1 de `strokeStarted` e `strokeFinished`.
4. *Sincronização de Miniaturas em `clear_canvas`*: disparos balanceados de `strokeStarted` e `strokeFinished` adicionados ao `ToolManager.clear_canvas()`.
5. *Desacoplamento de `PaperLayerWidget`*: eliminação de varredura cega em `QApplication.topLevelWidgets()`, implementação de `set_paper_state(visible, color)` no `RenderWidget` e emissão do sinal `paperChanged(bool, object)`.
6. *Grade & Réguas via Menu/Atalhos*: alias canônico `@property def geometry_controller` no canvas resolvendo atalhos e menus silenciosamente quebrados.
7. *Espelhamento H/V Ponta a Ponta*: propriedades `flip_x`/`flip_y` no canvas e emissão de `flip_changed_by_user` pelo `NavigatorPanel` com sincronização bidirecional.
8. *Marching Ants em Seleção via Menu*: métodos unificados `select_all()`, `invert_selection()` e `clear_selection()` sincronizando o timer de 60ms.
9. *Guards em `AladynBackend`*: eliminação de branches `elif` inalcançáveis em `set_render_options` e `render`.
10. *Eliminação de Shim Nível 2*: remoção definitiva de `ui/plugins/panels/color_plugin/color_wheel.py` com import canônico conforme política Zero-Dirt.
11. *Simetria de Sinais em Formas e Transformação*: `strokeStarted` disparado no início do arrasto e `strokeFinished` garantido no término.
12. *Salvaguarda ARCcC Invariants*: divisão modular em `tests/test_tools_signal_symmetry_and_flip.py` (11/11 testes verdes) e `tests/test_tool_lifecycles_and_paper.py` (6/6 testes verdes), mantendo todos os arquivos abaixo do teto de 450 LOC (Zona Verde).
13. *Documentação e Skill*: criação de `.agents/skills/lumenia-satellite-audit/SKILL.md` e `docs/01-correcao-da-base/06-auditoria-orbital-decomposta.md`.
Homologado com 100% de testes verdes (670+ testes na suíte global).

### 2026-09-21 — Saneamento do Sistema de Traço: tap isolado, cursor contínuo e suporte a tilt/twist (oitava rodada)
**O que foi feito:** Auditoria vertical do pipeline de traço completo (hardware/tablet $\to$ `InputRouter` $\to$ `CanvasStrokePipeline` $\to$ `AladynStrokeMixin` $\to$ C++ facade/estabilizador $\to$ `TileGrid` $\to$ Viewport). Identificadas e corrigidas três inconsistências críticas: (1) *Tap isolado (single-click sem arrasto / sarda)*: o C++ registrava o dab mas retornava `[0,0,0,0]` em `totalCatchupDirty`, fazendo a UI ignorar a atualização; corrigido com cálculo de bounding box analítica defensiva baseada no raio ativo em `CanvasStrokePipeline.end_stroke`, tornando a marca imediatamente visível na tela; (2) *Fantasmas de cursor*: sincronização frame a frame de `widget._last_rendered_cursor_rect = cur_cursor_rect` em `paint_stroke`, garantindo que a união com a área anterior remova o anel sem deixar rastros geométricos em traços rápidos; (3) *Propagação de stylus tilt/twist*: adicionado suporte a `tilt_x`, `tilt_y` e `twist` em `RenderWidget`, `InputRouter`, `CanvasStrokePipeline`, `AladynStrokeMixin`, `EngineBackend` e `StrokeProtocol`, encaminhando inclinação e rotação da caneta física diretamente para as APIs C++. Testado com variações de velocidade (10 a 3500 px/s), 8 direções cardeais, inversão brusca de 180° e estabilizador de 0% a 98% em `tests/test_stroke_pipeline_integrity.py` (5/5 passed). Todos os 31 testes dourados do C++ (`test_stroke_characterization.py`) preservados intactos. Commit `f69be00`.

### 2026-09-21 — Saneamento do Sistema de Cursor e Feedback Tátil da Viewport (sétima rodada)
**O que foi feito:** Auditoria especializada no subsistema de cursor e suas interações com as ferramentas e canvas. (1) *Reatividade de raio*: `RenderWidget.brush_size` transformado em `@property` reativa que recalcula instantaneamente `_cached_brush_radius` e emite dirty rect para a região do anel, atualizando o contorno geométrico do cursor sob o ponteiro sem necessidade de clique; (2) *Catálogo SVG e Hotspot*: adicionado alias `"eyedropper": "eyedrop"` em `icon_svg_catalog.py` e corrigido o hotspot canônico para o bico `(2, 22)` em `ToolCursorRenderer`, eliminando falhas de carregamento de pixmap; (3) *Suporte a Smudge*: anel geométrico estendido para incluir a ferramenta borrador (`"smudge"`) no `CursorController` e `ViewportRenderer`; (4) *Tipologia de cursores*: mapeados `Qt.CrossCursor` para ferramentas de formas vetoriais (`shapes`, `shape_*`) e `Qt.IBeamCursor` para ferramenta de texto; (5) *Feedback tátil*: implementados `Qt.ClosedHandCursor` para Pan e `Qt.SizeVerCursor` para Zoom Drag com invalidação e restauração limpa de cache via `invalidate_cursor_cache()`. Validado em `tests/test_canvas_cursor_interactions.py` (5/5 passed). Commit `7b59079`.

### 2026-09-21 — Saneamento da Ferramenta de Texto: preservação de buffer QImage (sexta rodada)
**O que foi feito:** Diagnóstico e correção de falha de segurança de memória na ferramenta de texto (`text_tool.py`). A conversão de texto rasterizado para bytes RGBA dependia de um `QImage` temporário alocado no escopo local de `_apply_rendered_text`; ao obter `image.bits().tobytes()`, o coletor de lixo podia descartar o buffer subjacente do Qt antes da cópia/composição, gerando corrupção esporádica ou falha silenciosa. Implementada retenção explícita do objeto `QImage` até a conclusão da gravação do bitmap na camada ativa. Commit `b0a83fe`.

### 2026-09-21 — Auditoria do Sistema de Pincéis: saneamento de duplo despacho e textura (sexta rodada)
**O que foi feito:** Auditoria corretiva no pipeline de configuração de pincéis (`brush_plugin`). Identificado duplo despacho assimétrico onde `BrushSettingsController` enviava parâmetros concorrentemente para o backend nativo e propriedades locais em widgets de viewport. Centralizado o estado no `EngineBackend` com sincronização reativa unidirecional. Corrigida a escala de contraste e relevo de granulação/textura (`set_brush_grain_contrast`) para respeitar a curva linear esperada pelo motor nativo. Commit `215646f`.

### 2026-09-21 — Desacoplamento de Arquitetura: eliminação de acoplamento CanvasCompatMixin (sexta rodada)
**O que foi feito:** Aplicação estrita da Etapa 1 da skill Lumenia Corrective Audit ("seguir o curso do rio"). A análise inicial sugeria que `CanvasCompatMixin` era código morto candidato à exclusão; o rastreamento vertical revelou que `OverlayRenderer` dependia de atributos privados acessados diretamente no widget (`_selection_path`, `_shape_preview_points`). A exclusão cega teria quebrado o desenho de seleções e formas geométricas na tela. O `OverlayRenderer` foi refatorado para consumir propriedades públicas explícitas (`selection_path`, `shape_preview_points`), desacoplando as camadas sem quebra de regressão e documentando o alerta de arquitetura. Commit `f9980ae`.

### 2026-09-21 — Limpeza de Código Morto Nível 1, Sombra de Empacotamento e Shims (sexta rodada)
**O que foi feito:** Triagem segura em 3 níveis: (1) Remoção de código morto Nível 1 com zero chamadores e isolamento estrito (`color_wheel.py`, `dialog.py`, `flood_fill.py`, `IRenderContext.hpp` — commit `c217811`); (2) Eliminação de arquivos sombra causados por pastas com `__init__.py` duplicando nomes de arquivos homônimos (`icon_svg_catalog`, `dialogs`, `presets` — commit `4d3f254`); (3) Modernização dos scripts desktop `Launch_Lumenia.bat` e `Launch_Lumenia_Silent.vbs` para o ponto de entrada canônico `main.py` com PYTHONPATH ajustado (commit `db2b80f`); (4) Migração de chamadores legados de adaptadores e remoção segura de shims residuais obsoletos (commit `3cba060`).

### 2026-09-20 — Formalização e aprovação do Gate de Sessão Longa P4 (quinta rodada)
**O que foi feito:** Conclusão do item P4 (`01-pendencias-atuais.md` e `04-testes-e-qualidade.md`). Pesquisa de práticas da indústria (Krita/Blender/Desktop Qt) para validação de estabilidade sem vazamentos. Formalizados os critérios de aceitação: $\Delta \text{GDI} == 0$, $\Delta \text{Handles} \le 5$, e drift de memória privada $\le 0.05 \text{ MB} / 100 \text{ ciclos}$ no platô pós-aquecimento. Implementado o harness automatizado `scripts/run_soak_test.py` com medição direta via `user32.dll!GetGuiResources` e regressão linear (aprovado com drift $+0.0000 \text{ MB} / 100 \text{ ciclos}$ em 350 ciclos). Implementado modo de pós-análise e emissão de laudo em `scripts/monitor_session.ps1 -Analyze`.

### 2026-09-20 — Fiação de Feedback Visual de Undo/Redo na UI (quinta rodada)
**O que foi feito:** Conclusão da pendência de UX/Produto de histórico (`01-pendencias-atuais.md`). Métodos `backend.can_undo()` e `backend.can_redo()` integrados à interface: ações `act_undo`/`act_redo` no Menu Editar e `action_undo`/`action_redo` na Barra Lateral agora iniciam desabilitadas e sincronizam reativamente com eventos de desenho (`strokeFinished`), operações de histórico e troca de documentos, além de conexão direta ao sinal `aboutToShow` do menu Editar. Testado em `tests/test_menu_bar_complete_wiring.py`.

### 2026-09-20 — Triagem dos achados `suspicious` do ARCcC-Navigator e anotações estritas (quinta rodada)
**O que foi feito:** Conclusão formal do item P2 (`01-pendencias-atuais.md`). Diagnóstico da causa raiz dos ~184 achados `suspicious: missing_type_annotation`: o extrator AST do Navigator processa exclusivamente argumentos de funções (`node.args.args`), ignorando anotações em variáveis locais (`ast.AnnAssign`) e subscritos (`Optional[T]`), fazendo com que arquivos com anotações perfeitas fossem marcados como ausentes. Anotações estritas de classe única aplicadas no backend e recovery (`aladyn_brush_mixin.py`, `aladyn_resources_mixin.py`, `main_window_recovery.py`, `manager.py`).

### 2026-09-20 — Guardas `hasattr` fechados, tabela de pincel confirmada, `EngineBackend` 178 → 172 (quarta rodada)
**O que foi feito:** três itens P1 investigados e fechados na mesma
sessão: (1) os 12 `hasattr(self._facade, ...)` restantes foram
investigados um a um — 11 são fallback legítimo para `.pyd` desatualizado
(documentado pelo próprio `test_stroke_characterization.py`), mantidos
como estão por decisão do usuário; (2) a unificação da tabela de parâmetros
de pincel (Passo 2 de `02-simplificacao-da-ponte.md`) já estava
implementada antes desta sessão (`brush_param_table.py`, commit
`23900cc`) — documentação corrigida, nenhum código novo; (3) os 178
métodos de `EngineBackend` foram varridos por uso real (regex contra
`ui/`, `plugins/`, `tests/`, após o Navigator se mostrar insuficiente
para esta análise), achando 6 métodos genuinamente mortos/duplicados
(`set_group_pass_through`, `set_canvas_grain_enabled`,
`set_brush_grain_invert`, `get_selection_contour_segments`,
`replace_document_context`, `get_nearest_primary_grid_curve`), removidos
de `backend.py`, `backend_protocols.py` e dos mixins correspondentes
(178 → 172 métodos). Nenhum símbolo do binário C++ nativo foi tocado.
**Base:** `01-correcao-da-base/01-pendencias-atuais.md` (itens P1,
seções "Guardas hasattr" e "EngineBackend") e
`01-correcao-da-base/02-simplificacao-da-ponte.md` (passos 2 e 4).
**Objetivo original daqueles documentos:** fechar as pendências P1 da
fase de correção da base restantes, com evidência medida em vez de
suposição, antes de mudar de área de foco.


> Toda entrada nova vai no topo. Formato: data, o que foi feito, por que
> agora, em qual documento (deste `docs/` ou do Claude Project) isso estava
> descrito, e qual era o objetivo declarado daquele documento. Não apague
> entradas antigas — este arquivo é o rastro de decisão do projeto.

### 2026-09-20 — CI restaurada, teste de regressão `.pyi` e `EngineBackend` dividido em protocolos
**O que foi feito:** três itens P0/P1 da rodada de auditoria aplicados: (1)
`.github/workflows/ci.yml` criado (jobs `windows` e `windows-avx2`,
fechando F-020); (2) `tests/test_pyi_contract_matches_binary.py` criado,
formalizando via `ast` a checagem `.pyi` × binário compilado que antes só
existia como verificação manual, e removendo 2 declarações mortas do
`.pyi`; (3) `ui/core/engine/backend_protocols.py` criado, dividindo os 178
métodos de `EngineBackend` em 11 `Protocol`s por papel (gerados via `ast`,
verificados por `isinstance()` contra os dois backends concretos em
`tests/test_engine_backend_protocols.py`) — mudança aditiva, `EngineBackend`
em si não foi alterado.
**Base:** `01-correcao-da-base/01-pendencias-atuais.md` (itens P0 e P1) e
`01-correcao-da-base/02-simplificacao-da-ponte.md` (passos 1 e 3 da lista
de "O que fazer, em ordem").
**Objetivo original daqueles documentos:** reduzir a desconfiança
estrutural entre a UI e o motor (guardas defensivas, interface
monolítica) sem adicionar feature nova — só remoção/organização/verificação.

### 2026-09-20 — Reorganização de `docs/` em estrutura numerada por prioridade
**Por quê:** a organização anterior (`architecture/`, `guides/`,
`specifications/`, `audit/`) agrupava por *tipo* de documento, não por
*relevância para a fase atual*. Documentos de visão de futuro, auditorias já
fechadas e pendências ativas ficavam misturados na mesma prateleira.
**Base:** pedido direto do usuário na sessão de auditoria corretiva de
2026-09-20 (Claude Project, documento `auditoria-corretiva-geral-2026-09-20.md`).
**Objetivo:** que qualquer agente ou desenvolvedor saiba, só pela pasta, se
está lendo algo acionável agora ou referência/histórico.

### 2026-09-20 — Auditoria corretiva geral do projeto (Claude Project)
**O que foi feito:** verificação ao vivo, item a item, de toda a lista de
pendências de `historico/estado-da-base-2026-09-15.md`. Resultado consolidado
em `01-correcao-da-base/01-pendencias-atuais.md`.
**Base:** `estado-da-base-lumenia.md` (Claude Project, 2026-09-15).
**Objetivo original daquele documento:** listar, em ordem de dependência, o
que fazer para a base ficar sólida o suficiente para a Fase 3 começar.
