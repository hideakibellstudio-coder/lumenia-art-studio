# Pendências atuais da fase de correção da base

> Documento vivo. Sintetiza e substitui `historico/estado-da-base-2026-09-15.md`
> e a parte ainda acionável de `historico/auditoria-f017-f031-endurecimento-navigator.md`.
> Atualizado com verificação ao vivo no terminal em 2026-09-24 (não é estimativa
> nem cópia do relatório anterior). Toda mudança de status aqui deve vir com uma
> linha correspondente em `../README.md`.

**Regra de ouro desta fase:** nenhuma feature nova. Cada item abaixo remove
código, remove ambiguidade, ou adiciona verificação. Nada aqui é estético.

---

## ✅ 2026-09-24 — Espaguete desfeito por contrato (sessão Claude Code)

Medido no Linux (Python 3.11, offscreen): 835 testes passam, 5 pulados. CI do
GitHub verde nos 5 jobs no commit `5046cec`. Detalhe e bugs corrigidos nas
mensagens de commit do branch `claude/zealous-galileo-38k67d`; regras novas em
`AGENTS.md` seção 4.2 e `../02-arquitetura/06-contratos-entre-componentes.md`.

**Feito:** estado compartilhado (`ui/core/state`) no lugar de seis cópias da
cor e dos parâmetros do pincel e de quatro caminhos para a ferramenta ativa;
camadas com um caminho só até o motor; canvas, barra secundária e páginas de
opções sem acesso a privados alheios; catraca de acoplamento; README com
dependências medidas nas 62 pastas de código; CI verde.

**Pendências de arquitetura, em ordem de retorno** (números de
`python -m tests.arccc_coupling_metrics --top 8`):

1. ~~**Mixins que se leem por `self`** na `MainWindow` e no
   `WorkspaceContainer`.~~ *Feito em 2026-09-24:* seis colaboradores na casca
   (porta `workspace_port.py`) e quatro no workspace (`WorkspaceLayout`,
   `DocumentViewSync`, `PanelConnections`); papel com fonte única no
   `Document`. Resta: `add_panel` conhece os ids `navigator`/`layers`/`geometry`.
2. ~~**Painel avançado do pincel**~~ *(feito em 2026-09-24: cinco seções
   com estado próprio sobre `AdvancedSection`, `BrushEngineWriter` no lugar
   do mixin; comportamento caracterizado nos 23 controles antes e depois,
   idêntico; `tests/test_brush_advanced_panel.py`.)*
3. ~~**Docas**~~ *(feito em 2026-09-24: nenhum acesso a privado entre doca,
   animador, sidebar e gaveta; a doca recebe o widget onde flutua).* Resta:
   a persistência do estado das gavetas existe (`DockStateStore`) mas não
   está ligada ao app (decisão do usuário). *(Os dois painéis avançados agora
   abrem pela `FloatingPanelWindow` com `WorkspaceService.canvas_area_rect`.)*
4. ~~**Menus**~~ *(feito em 2026-09-24: `menu_bar.py` sem `hasattr`,
   `SettingsMenu` extraído; ids canônicos `PanelId` — o menu Janela pedia ids
   que nenhum plugin registrava e 4 dos 5 itens não faziam nada.)*
5. ~~**Telemetria**~~ *(feito em 2026-09-24: `TelemetryTracker` é a fonte
   única; cockpit, painel e diagnóstico são views dele; os 20 medidores e o
   relatório existem uma vez (`telemetry_meters.py`, `telemetry_report.py`);
   o DTO lê a struct nativa sem valor padrão, com teste de contrato. Bugs
   medidos e corrigidos: "Limpar Undo" esvaziava listas privadas e dizia
   "limpa" com a RAM do histórico intacta (agora `clearHistory` nativo via
   `DocumentHistory.clear`); a tela afirmava "AVX2 / SSE2 Ativo" no build
   escalar padrão; o relatório mostrava sempre o motor padrão; o benchmark
   pintava 1000 carimbos na camada do usuário; o painel mostrava o estado do
   quadro anterior.)*
6. ~~**Segundo caminho até o motor**~~ *(feito em 2026-09-24: saíram o
   `BridgeClient`, os comandos em dataclass, `contracts.py`,
   `aladyn_dispatch.py` e `dispatch` do contrato — nenhum chamador em
   produção. O backend avisa `EngineRegistry.notify_document_modified` e o
   `DocumentManager` suja o documento, sem o backend importar o modelo. O
   contexto nativo provisório do boot (`default_doc`) passou a ser liberado
   quando o primeiro documento abre; antes ficava alocado a sessão toda.)*
7. ~~**Arquivos na parede dos 450**~~ *(feito em 2026-09-24: os 5 divididos
   por responsabilidade — gravação (`RecordingActions`, fonte de quadros do
   documento, barra flutuante só com sinais), novo documento
   (`PresetGallery`), temas (`InterfaceTweaksGroup`; raio e fonte agora
   funcionam; filtro Escuros/Claros funciona fora do pt-BR), geometria
   (`NativeGeometrySnap`, `geometry_engine_sync`, `Document.store_*_state`) e
   relatório de testes (mostra o resultado medido da execução em vez de
   "110 testes / 100% / APROVADO" fixos). Censo: 0 na parede.)*
8. **Textos sem `tr()`**: rótulos das views da barra secundária e mensagens de
   status da `MainWindow` em português fixo.
9. **Pastas sem porta de entrada** (`__init__.py`): `ui/core/geometry`,
   `canvas/renderers`, `canvas/tools`, `canvas/viewport`, `dock`, entre
   outras (cada README registra). `ui/utils` não tem consumidor;
   `ui/boundary/public_api` está vazia.

---

## ✅ 2026-09-23 — Decisões do usuário aplicadas (sessão Claude/Cowork)

Relatório: `claude/correcoes-e-decisoes-2026-09-22.md` (Claude Project).
Medido no Windows: suíte completa verde (796 testes), `navigator_verify`
com 0 `confirmed_violation`.

- **Promessas falsas viraram funções reais** (decisão: "deixar de prometer e
  desenvolver a função real"):
  - Seleção → Modificar (Expandir, Contrair, Suavizar Borda) no motor
    (`SelectionMorphology.cpp`), com Desfazer.
  - Transformar → Distorcer (4 cantos, homografia no motor; prévia e commit
    coincidem) no painel e na barra secundária.
  - Harmonias na roda de cores (5 regras, marcas no anel, amostras clicáveis).
- **Guardas `hasattr` do grupo A** (11, funções que já existem no binário):
  o plano B continua, mas registra um aviso no log (`native_fallback.nativo_tem`)
  em vez de ficar calado. Grupos B (traço raw vs legado, 3) e C (detector de
  capacidades, 1) mantidos. Travados em `tests/test_river_ratchets.py`.
- Anotações de tipo que o Navigator pedia (`layer`, `doc`).
- `backend_protocols.py` (434, na parede dos 450) dividido: o papel
  SelectionTransform foi para `backend_protocols_selection.py`.
- **Adiado por decisão:** pipeline de cor 16-bit (mexe em tile, compositor,
  desfazer e formato de arquivo).

**Ainda com decisão do usuário:** `Ctrl+E`, ffmpeg no instalador, critério do
gate de sessão longa, processos antigos do Antigravity, `.venv`, remoto do
Navigator.

---

## ✅ 2026-09-22 — Análise completa + correções (sessão Claude/Cowork)

Relatório: `claude/analise-completa-projeto-2026-09-22.md` (Claude Project).
Medido no Windows ao fim da sessão: suíte completa verde (762 testes), `navigator_verify`
com 0 `confirmed_violation` e 0 arquivos na Zona Vermelha.

**Afirmações anteriores corrigidas** (estavam neste documento e no benchmark):
- "100% dos arquivos na Zona Verde (< 450)": falso até hoje -- havia 3 C++ ≥ 450
  sob exceção e ~95 arquivos entre 251 e 449. Os 3 foram divididos hoje.
- "Zero vazamentos" pelo gate P4: `scripts/run_soak_test.py` roda sem nenhum
  widget, um documento, traços de 40 px e desfazer limitado a 30 passos -- o
  platô de memória é garantido pelo próprio anel de desfazer. Continua útil
  como smoke test do motor; o gate de sessão real é
  `scripts/soak_full_session.py` (MainWindow real, camadas, salvar .lmn, MDI).
- Contagens de teste "725"/"659"/"670+": a medida real hoje é a do pytest.

**Corrigido nesta sessão:**
- Binário `.pyd` de 2026-09-05 esquecido em `ui/engine_backends/` (138 vs 185
  atributos) movido para `../build/obsoleto/`.
- `WgpuRustBackend` removido (adaptador de um motor Rust inexistente); teste
  dos Protocols passou a exigir implementação real fora de `EngineBackend`.
- Teste com caminho absoluto `z:\...\.agents\...` (falhava fora desta máquina).
- `render_stroke_preview` restaurado (sumiu do motor em 2026-08-25; o painel
  de pincel mostrava aproximação vetorial) + a prévia agora copia o perfil em
  vez de alterar o pincel em uso.
- 5 varreduras `topLevelWidgets()` → `ui/core/plugins/canvas_access.py`.
- 5 lambdas em sinais de singletons (vazamento + "C++ object already deleted").
- Guardas `hasattr` sobre o motor: 19 → 16 pontos (15 entradas nomeadas) em
  `tests/test_river_ratchets.py` (guarda nova falha o teste).
- 25 chaves de tradução ausentes nos 4 idiomas + teste que impede regressão.
- `except Exception: pass` que escondiam falha de plugin agora registram log.
- CI com Python 3.14 (versão da máquina de desenvolvimento).
- C++ Zona Vermelha: `StrokeOrchestrator.cpp`, `TransformEngine.cpp`,
  `SelectionEngine.cpp` divididos por método; exceções de LOC removidas.
- Suíte: janelas órfãs descartadas entre módulos (≈369 s → ≈110 s).
- Navigator: `verifier.py` (777), `python_semantic.py` (752) e `context.py`
  (512) divididos sem mudar saída (relatório byte a byte idêntico); bump do
  extrator para `xl-contracts-v10` (faltou no commit `f1fa359`).

**Abertos, com decisão do usuário** (ver o relatório no Project):
promessas falsas da interface (Modificar Seleção, "Distorcer", "Harmonias"),
lista final de guardas `hasattr`, faixa amarela 251 vs 300, `Ctrl+E`,
ffmpeg no instalador, execução do gate de sessão longa com artista.
*(Promessas falsas e guardas `hasattr` resolvidas em 2026-09-23, acima.)*

---

## ✅ Resolvido nesta sessão (2026-09-21, rodadas 6 a 14)

Itens de auditoria vertical, código morto, integridade de traço, cursor, fronteira C++ e subsistemas satélites concluídos e homologados:

- **Auditoria Orbital Concêntrica de Subsistemas Satélites (Rodadas 9 a 14)**:
  - Criação e expansão da skill `lumenia-satellite-audit` e documento metodológico `06-auditoria-orbital-decomposta.md` para o modelo de 6 camadas concêntricas e verificação ascendente dos 5 Rios.
  - *Rodada 14 (Descida ao Núcleo C++ e Laço Ascendente dos 5 Rios)*: validação de `BufferContract.hpp` (`checkedRasterBytes`, `validateRasterInput`, `pixelSnapshot`), `DocumentContext::touch()` monótono, invariantes de `TileGrid`, `TileUndoManager`, `Compositor` e `DabRenderer` SIMD. Homologação do fechamento ascendente completo nos 5 Rios (Traço, Câmera/Viewport, Camadas/Histórico, Seleção/Transformação e Cor/Perfis). Suíte dedicada `tests/test_native_core_invariants_and_rivers.py` (9/9 testes verdes).
  - *Rodada 13 (Sincronização Viewport/Navigator e Dirty Tracking de Camadas)*: alinhamento dos ícones SVG de flip no painel Navigator (`flip-vertical` / `flip-horizontal`), emissão idempotente de `cameraChanged` nos setters `flip_x`/`flip_y` de `canvas_compat.py` para sincronização bidirecional, e cobertura completa de dirty tracking (`_mark_document_dirty`) nas 18 operações de camada de `AladynLayerMixin`, geometria, transações e recursos. Suíte dedicada `tests/test_dirty_tracking_layers_and_navigator_flip.py` (7/7 testes verdes).
  - *Rodada 12 (Saneamento dos Botões de Flip e Fronteira Primordial C++)*: alinhamento 1:1 de `btn_fliph`/`btn_flipv` $\to$ `flipHRequested`/`flipVRequested` no Navigator, guard defensivo resiliente em MDI com `hasattr(facade, "set_render_options")` e fallbacks granulares, e dirty tracking em operações nativas (`clear_canvas`, `clear_layer`, `undo`, `redo`, `flood_fill`, `fill_area`, `end_stroke`). Suíte dedicada `tests/test_render_options_and_native_dirty_tracking.py` (6/6 testes verdes).
  - *Rodada 11 (Borda Primordial C++ e Paridade de Menu)*: função canônica `to_native_color_rgba` para coerção polimórfica resiliente de cores, marcação dirty em mutações de raster (fill, delete, transform, paste, flip, rotate), paridade de sinais `strokeStarted`/`strokeFinished` no menu principal com helper `_emit_stroke_wrap` e resolução canônica de cor. Suíte dedicada `tests/test_engine_boundary_color_and_signals.py` (4/4 testes verdes).
  - *Rodadas 9 e 10 (Subsistemas Satélites, Ferramentas e Docks)*: balde de tinta com `active_color` e paridade de sinais `try ... finally`, ciclo de vida simétrico do `TextToolController`, sincronização de previews em Delete e `clear_canvas`, desacoplamento de `PaperLayerWidget` com sinal `paperChanged`, réguas/grade com alias `geometry_controller`, marching ants dinâmicas unificadas no `SelectionToolController` e eliminação do shim `color_wheel.py`.
  - *Salvaguarda ARCcC Invariants*: 100% de conformidade com o teto de 450 LOC por arquivo (Zona Verde) em todos os arquivos modificados. 100% de testes verdes em toda a base (**725 testes passando** com zero falhas).

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
