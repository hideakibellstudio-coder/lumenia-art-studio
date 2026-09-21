# Pendências atuais da fase de correção da base

> Documento vivo. Sintetiza e substitui `historico/estado-da-base-2026-09-15.md`
> e a parte ainda acionável de `historico/auditoria-f017-f031-endurecimento-navigator.md`.
> Atualizado com verificação ao vivo no terminal em 2026-09-21 (não é estimativa
> nem cópia do relatório anterior). Toda mudança de status aqui deve vir com uma
> linha correspondente em `../README.md`.

**Regra de ouro desta fase:** nenhuma feature nova. Cada item abaixo remove
código, remove ambiguidade, ou adiciona verificação. Nada aqui é estético.

---

## ✅ Resolvido nesta sessão (2026-09-21, rodadas 6 a 8)

Itens de auditoria vertical, código morto, integridade de traço e cursor concluídos e homologados:

- **Auditoria de Código Morto & Sombra de Empacotamento (Níveis 1, 2 e 3)**:
  - Nível 1: Remoção de 4 arquivos mortos isolados com zero chamadores (`color_wheel.py`, `dialog.py`, `flood_fill.py`, `IRenderContext.hpp` — commit `c217811`).
  - Nível 2 e 3: Eliminação de sombras geradas por subpacotes com `__init__.py` duplicando módulos de mesmo nome (`icon_svg_catalog`, `dialogs`, `presets` — commit `4d3f254`). Modernização dos inicializadores desktop `Iniciar_Lumenia.bat` e `Iniciar_Lumenia_Silencioso.vbs` para `main.py` (commit `db2b80f`) e remoção segura de shims legados (commit `3cba060`).
- **Desacoplamento de Arquitetura do Viewport (Nível 4)**:
  - Rastreamento pelo "curso do rio" revelou dependência do `OverlayRenderer` em atributos privados de `CanvasCompatMixin` (`_selection_path`, `_shape_preview_points`).
  - Refatorado para propriedades públicas limpas, prevenindo a quebra do desenho de seleções e formas na tela e eliminando o acoplamento espúrio (commit `f9980ae`).
- **Saneamento do Sistema de Pincéis**:
  - Eliminação de duplo despacho concorrente entre `BrushSettingsController`, backend e viewport widgets. Estado canônico centralizado no `EngineBackend` com propagação reativa unidirecional.
  - Correção na escala linear de textura/relevo (`set_brush_grain_contrast`) para o motor nativo (commit `215646f`).
- **Preservação de Buffer na Ferramenta de Texto**:
  - Correção de ciclo de vida do `QImage` temporário em `_apply_rendered_text`, retendo a referência durante o dump de bytes RGBA para evitar use-after-free/corrupção de raster (commit `b0a83fe`).
- **Saneamento Completo do Sistema de Cursor**:
  - `RenderWidget.brush_size` como `@property` reativa: recalcula `_cached_brush_radius` e emite dirty rect imediato, redimensionando o anel sob o ponteiro sem requerer clique.
  - Hotspot exato e alias do conta-gotas (`"eyedropper": "eyedrop"`, hotspot `(2, 22)`).
  - Suporte ao anel geométrico na ferramenta borrador (`"smudge"`).
  - Cursores especializados para formas (`CrossCursor`) e texto (`IBeamCursor`).
  - Feedback tátil em Pan (`ClosedHandCursor`) e Zoom Drag (`SizeVerCursor`) com restauração via `invalidate_cursor_cache()`.
  - Homologado em `tests/test_canvas_cursor_interactions.py` (5/5 passed, commit `7b59079`).
- **Saneamento Profundo do Sistema de Traço (Stroke Pipeline)**:
  - Rastreamento ponta a ponta: hardware $\to$ `InputRouter` $\to$ `CanvasStrokePipeline` $\to$ `AladynStrokeMixin` $\to$ Facade/Orchestrator C++ $\to$ `TileGrid` $\to$ Viewport.
  - *Tap isolado (single-click sem arrasto / sarda)*: fallback analítico de bounding box em `end_stroke` quando `totalCatchupDirty` for vazio, garantindo renderização instantânea do ponto.
  - *Ghosting de cursor*: atualização contínua de `widget._last_rendered_cursor_rect = cur_cursor_rect` frame a frame em `paint_stroke`.
  - *Tilt e Twist*: propagação completa de inclinação (`xTilt`, `yTilt`) e rotação da caneta física até o motor C++.
  - Validação de estabilizador WMA (0% a 98%), 8 direções cardeais e reversão brusca de 180° (U-turns).
  - Homologado em `tests/test_stroke_pipeline_integrity.py` (5/5 passed), preservando 100% dos testes dourados de caracterização (`test_stroke_characterization.py`, 31/31 passed). Commit `f69be00`. Suíte global em **659 testes passando**.

## ✅ Resolvido em sessões anteriores (2026-09-20, rodadas 1 a 5)

Estes três itens estavam listados como P0/P1 até esta rodada. Detalhes de
cada implementação estão no changelog do `../README.md`.

- **CI restaurada** — `.github/workflows/ci.yml` criado, com jobs `windows`
  (matriz 3.11/3.12/3.13, build `--simd scalar`) e `windows-avx2` (F-020,
  build `--simd avx2` com verificação explícita de carregamento do módulo).
- **Teste de regressão `.pyi` × binário compilado** —
  `tests/test_pyi_contract_matches_binary.py` criado, baseado em `ast`
  (não regex), comparando bidirecionalmente o contrato declarado com o
  módulo compilado. Aproveitado para remover 2 declarações mortas do
  `.pyi` (`get_pixel_data_size`, `get_display_pixel_data_size`).
- **`EngineBackend` dividido em protocolos por papel** —
  `ui/core/engine/backend_protocols.py` criado, com 11 `Protocol`s
  (`CoreLifecycleProtocol`, `StrokeProtocol`, `BrushProtocol`,
  `CanvasResourceProtocol`, `LayerProtocol`, `SelectionTransformProtocol`,
  `GeometryProtocol`, `TelemetryProtocol`, `ColorProtocol`,
  `RenderPipelineProtocol`, `HistoryProtocol`) cobrindo os 178 métodos de
  `EngineBackend`, gerados via `ast` a partir da classe real (não
  transcritos à mão) e verificados por `tests/test_engine_backend_protocols.py`
  (`isinstance()` de `AladynBackend` e `WgpuRustBackend` contra os 11
  papeis). **Importante:** isto é aditivo — `EngineBackend` continua
  existindo como contrato universal, sem nenhum método removido ou
  movido. O ganho é permitir testar/implementar um papel isoladamente
  sem precisar de um backend inteiro; não reduz, por si só, o tamanho de
  `EngineBackend` nem os `hasattr` do adaptador (ver P1 abaixo).

## 🟡 P1 — alto retorno, esforço baixo/médio

### Guardas `hasattr(self._facade, ...)` — investigados, fechados como não aplicável
107 → 12 entre 2026-09-15 e 2026-09-20 (queda de 89%). Os 12 restantes foram
investigados individualmente em 2026-09-20 (terceira rodada) e **não são dívida
de código defensivo por desconfiança de contrato** — são fallback deliberado
e documentado para quando o `.pyd` compilado está desatualizado (não tem os
métodos mais novos ainda). Prova: o próprio docstring de
`tests/test_stroke_characterization.py` descreve o caminho `facade` legado
(`begin_stroke`/`update_stroke`/`end_stroke`) como "fallback para builds
nativas antigas", e o teste mede os dois caminhos (`raw` e `facade`) de
propósito porque uma correção no estabilizador precisa tocar
`StrokeOrchestrator.cpp` **e** `PaintEngineFacade.cpp`. Os outros 8
(`get_display_pixel_buffer`/`get_best_lod_level` em `aladyn.py`, 5 métodos
de curvilinear/perspective em `aladyn_geometry_mixin.py`) seguem o mesmo
formato: recursos mais novos que degradam graciosamente se o binário ainda
não foi recompilado. O teste `.pyi`×binário (ver acima) garante que o
*contrato declarado* bate com o binário *no momento do teste* — não impede
rodar código novo contra um `.pyd` ainda não recompilado, que é exatamente o
cenário que esses guards protegem. **Decisão do usuário (2026-09-20):**
manter o código como está; fechar este item como investigado, não como
removido. `02-simplificacao-da-ponte.md` (passo 4) foi corrigido para
refletir isso.

> **Correção (2026-09-20, quarta rodada):** um dos 12, `get_nearest_primary_grid_curve`,
> não era de fato um fallback ativo — investigação mais profunda (ver item
> abaixo) mostrou que `GeometryToolController` sempre usa a versão pura-Python
> (`GeometrySnappingEngine.find_nearest_primary_grid_curve`) para o hover do
> grid curvilinear, e nunca chama a versão nativa. Diferente dos outros 11
> (que são exercitados de verdade pelo caminho `_snap_use_native_*`), este
> era órfão puro. Foi removido junto com os outros 5 métodos mortos abaixo.
> Restam 11 guards legítimos, não 12.

### `EngineBackend` — 178 → 172 métodos, 6 mortos removidos (2026-09-20, quarta rodada)
A divisão em protocolos (ver acima) nomeia o recorte natural, mas por si só
não reduz `EngineBackend`. A frase original aqui ("avaliar se as
implementações concretas podem delegar a papeis internamente") era
tecnicamente incoerente — `Protocol` do `typing` é tipagem estrutural pura,
sem implementação para delegar a. Corrigido: o usuário pediu investigar
duplicatas/mortos reais antes de decidir qualquer coisa.

**Método:** `navigator_references` (`calls`) no arquivo inteiro só achou 14
relações para uma classe de 178 métodos muito usada — limitação conhecida do
resolvedor Python do Navigator para `self.atributo.metodo(...)` quando o tipo
do atributo não é inferido estaticamente. Abandonado em favor de varredura
direta por regex nos 178 nomes contra `ui/`, `plugins/` e `tests/` (excluindo
os arquivos de definição e `ui/engine_backends/`), com verificação manual de
cada candidato antes de confirmar — inclusive dois falsos positivos do
próprio script (`available` é `@property`, acessado sem parênteses; `flood_fill`
é chamado internamente por `fill_area`) e um bug de regex (`-SimpleMatch` do
PowerShell tratando `|` como caractere literal, escondendo os chamadores reais
de `snap_perspective`/`set_curvilinear_guide_config`/`get_curvilinear_candidates`).

**6 métodos removidos** de `backend.py`, `backend_protocols.py` e do mixin
correspondente (nada tocado no `.pyd` nativo — a Lei de Isolamento do Binário
C++ continua intacta; o binário pode manter os símbolos, só a superfície
Python some), todos com 0 chamadores em `ui/`, `plugins/` ou `tests/`:

- `set_group_pass_through` — duplicata: o modo de blend "Pass Through" de
  grupo já é aplicado via `set_layer_blend_mode` (valor 7), o caminho
  genérico usado por `layers_plugin/header.py`. O setter dedicado nunca era
  chamado por nada.
- `set_canvas_grain_enabled` — duplicata: o "enabled" real do grain de
  papel/canvas já viaja como parâmetro de `set_canvas_paper_state(...)`
  (chamado por `layers_plugin/paper.py`); o setter dedicado nunca era chamado.
- `set_brush_grain_invert` — duplicata: o checkbox "Inverter Topografia" da
  UI (`brush_texture_section.py`) está ligado a `invertHeightChanged` →
  `_on_brush_invert` → `backend.set_brush_invert_height(...)` (outro método,
  em uso). A própria implementação antiga fazia
  `self._facade.get_brush_profile().brush_grain_invert = bool(invert)` —
  exatamente o que `apply_brush_preset_dict` (tabela única, ver Passo 2 de
  `02-simplificacao-da-ponte.md`) já faz via `setattr` genérico no perfil
  nativo. Redundante desde a unificação da tabela.
- `get_selection_contour_segments` — órfão: implementado, delegava pro
  facade, mas nenhum chamador em nenhum lugar.
- `replace_document_context` — órfão: peça de um fluxo MDI de "preparar
  documento em background e trocar atomicamente" (`uid`/`prepared_uid`) que
  nunca foi conectado — nada no repositório cria um `prepared_uid`.
- `get_nearest_primary_grid_curve` — órfão (ver correção acima): o guard
  `hasattr` existia mas nunca era exercitado, porque `GeometryToolController`
  sempre usa a versão Python pura (`GeometrySnappingEngine.find_nearest_primary_grid_curve`).

**Não removido, cluster relacionado mas fora de escopo:** `get_redo_count`,
`can_redo`, `get_undo_count`, `can_undo`, `get_undo_memory_limit_mb`,
`get_undo_max_steps` — implementados e testados no nível do motor
(`get_redo_count` inclusive tem um chamador interno real, `can_redo()` no
próprio mixin), mas os itens de menu Undo/Redo nunca usam esses métodos
para habilitar/desabilitar — ficam sempre habilitados, e `undo()`/`redo()`
só retornam `False` em silêncio quando não há o que fazer. Não é código
morto (há cobertura de teste real para a maioria), é uma decisão de
produto/UX (mostrar ou não o estado do histórico na UI) que não foi tomada
nesta rodada.

**Validado:** `ast.parse` nos 7 arquivos tocados, `test_engine_backend_protocols.py` + `test_pyi_contract_matches_binary.py` +
`test_brush_param_contract.py` isolados e a suíte completa, todos verdes no
Windows do usuário após a remoção.

## 🟢 P2 — menor urgência — Triagem concluída e fechada (2026-09-20, quinta rodada)

- **Triagem completa dos ~184 achados `suspicious` do Navigator**:
  - **Causa raiz diagnosticada:** O extrator AST do Navigator (`python_semantic.py:165-184`) extrai arestas `annotates` unicamente dos argumentos de funções (`node.args.args`). Ele descarta variáveis locais anotadas (`ast.AnnAssign`, ex: `w: "RenderWidget" = self.widget`, `layer: LocalLayer = ...`) e subscritos (`Optional[T]`, `list[T]`).
  - **Estado real do código Lumenia:** A grande maioria dos pontos sinalizados (como `input_router.py:136`, `layer_manager.py:207,214`, `history.py:43`, `serializer.py:59`, `shortcut_registry.py:14`) **já possuía anotação estática correta** no código-fonte.
  - **Anotações estritas aplicadas:** Nos locais de produção legítimos identificados com 100% de pertinência a uma única classe (`aladyn_brush_mixin.py`: `prof: "BrushProfile"`, `c_tex: "CanvasTexture"`; `aladyn_resources_mixin.py`: `canvas: "CanvasTexture"`; `main_window_recovery.py`: `document: Document`; `ui/core/document/manager.py`: `doc: Document`), as anotações foram devidamente inseridas respeitando o protocolo estrito.
  - **Conclusão:** Seguindo expressamente o `03-protocolo-do-navigator.md`, nenhum comportamento de runtime foi alterado para mascarar limitações estáticas do analisador. O item P2 está formalmente triado, documentado e encerrado.

## ⚪ P4 — cobertura que nunca existiu — Gate formalizado e validado (2026-09-20, quinta rodada)

- **Portão de Teste de Sessão Longa e Detecção de Vazamentos formalizado e aprovado**:
  - **Critérios formais estabelecidos:** Embasados na literatura de engenharia desktop do Krita e Blender, definidos em `04-testes-e-qualidade.md`:
    1. $\Delta \text{GDI} == 0$ (tolerância zero para vazamentos de GDI handles no Windows).
    2. $\Delta \text{Handles} \le 5$ (estabilidade de handles do SO).
    3. $\text{Drift} \le 0.05 \text{ MB} / 100 \text{ ciclos}$ na fase de platô (após aquecimento do anel de Undo e cache de tiles).
  - **Harness de estresse headless criado:** `scripts/run_soak_test.py` simula centenas de ciclos de pintura interpolada, variações de dinâmica e transações de histórico em modo offscreen com medição direta via `user32.dll!GetGuiResources` e `psapi.dll!GetProcessMemoryInfo`.
  - **Resultado da validação:** Bateria de 350 ciclos (180 warmup + 170 platô) executada e **100% APROVADA**: $\Delta \text{GDI} = 0$, $\Delta \text{Handles} = 0$, Drift de Memória Privada = $+0.0000 \text{ MB} / 100 \text{ ciclos}$.
  - **Monitor de sessão com artista integrado:** `scripts/monitor_sessao.ps1` recebeu parâmetro `-Analisar <csv>` para processamento pós-sessão de desenho humano e emissão automática do laudo do Gate.

---

## Como este documento se relaciona com os outros

- `02-simplificacao-da-ponte.md` — o *como* dos itens P1 acima (guardas e
  protocolos por papel).
- `03-protocolo-do-navigator.md` — leitura obrigatória antes de interpretar
  qualquer número de `suspicious`/`confirmed_violation` citado aqui.
- `04-testes-e-qualidade.md` — como rodar a suíte que valida qualquer mudança
  feita a partir deste documento.
- `05-fluxo-lumenia-navigator.md` — o método geral de trabalhar com o Navigator
  ao longo de uma sessão de correção.
- `../historico/` — auditorias fechadas que geraram os números-base citados
  aqui (F-001 a F-031). Não são pendência; são proveniência.
