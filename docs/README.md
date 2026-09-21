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

### `05-visao-e-futuro/` — explícitamente **não** é para agora
Visão estratégica de produto e o roadmap do pipeline de cor 16-bit/float.
Mantido por referência; nada aqui deve virar trabalho antes da base fechar.

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
**O que foi feito:** Triagem segura em 3 níveis: (1) Remoção de código morto Nível 1 com zero chamadores e isolamento estrito (`color_wheel.py`, `dialog.py`, `flood_fill.py`, `IRenderContext.hpp` — commit `c217811`); (2) Eliminação de arquivos sombra causados por pastas com `__init__.py` duplicando nomes de arquivos homônimos (`icon_svg_catalog`, `dialogs`, `presets` — commit `4d3f254`); (3) Modernização dos scripts desktop `Iniciar_Lumenia.bat` e `Iniciar_Lumenia_Silencioso.vbs` para o ponto de entrada canônico `main.py` com PYTHONPATH ajustado (commit `db2b80f`); (4) Migração de chamadores legados de adaptadores e remoção segura de shims residuais obsoletos (commit `3cba060`).

### 2026-09-20 — Formalização e aprovação do Gate de Sessão Longa P4 (quinta rodada)
**O que foi feito:** Conclusão do item P4 (`01-pendencias-atuais.md` e `04-testes-e-qualidade.md`). Pesquisa de práticas da indústria (Krita/Blender/Desktop Qt) para validação de estabilidade sem vazamentos. Formalizados os critérios de aceitação: $\Delta \text{GDI} == 0$, $\Delta \text{Handles} \le 5$, e drift de memória privada $\le 0.05 \text{ MB} / 100 \text{ ciclos}$ no platô pós-aquecimento. Implementado o harness automatizado `scripts/run_soak_test.py` com medição direta via `user32.dll!GetGuiResources` e regressão linear (aprovado com drift $+0.0000 \text{ MB} / 100 \text{ ciclos}$ em 350 ciclos). Implementado modo de pós-análise e emissão de laudo em `scripts/monitor_sessao.ps1 -Analisar`.

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
