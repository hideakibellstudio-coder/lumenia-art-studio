# Pendências atuais da fase de correção da base

> Documento vivo. Sintetiza e substitui `historico/estado-da-base-2026-09-15.md`
> e a parte ainda acionável de `historico/auditoria-f017-f031-endurecimento-navigator.md`.
> Atualizado com verificação ao vivo no terminal em 2026-09-20 (não é estimativa
> nem cópia do relatório anterior). Toda mudança de status aqui deve vir com uma
> linha correspondente em `../README.md`.

**Regra de ouro desta fase:** nenhuma feature nova. Cada item abaixo remove
código, remove ambiguidade, ou adiciona verificação. Nada aqui é estético.

---

## ✅ Resolvido nesta sessão (2026-09-20, segunda rodada)

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

## 🟢 P2 — menor urgência

- **~184 achados `suspicious` do Navigator** não triados individualmente
  (exceção declarada, ou investigado e aceito). Ver `03-protocolo-do-navigator.md`
  antes de interpretar qualquer achado — `suspicious` é limitação da
  ferramenta em construção de prova, não defeito automático do código.
- **Forward-reference em string não reconhecida pelo resolvedor do Navigator**
  (achado novo de 2026-09-20): `w: "RenderWidget" = self.widget` — padrão já
  estabelecido no próprio arquivo — continua marcado como `missing_type_annotation`
  mesmo correto. Limitação do Navigator, não do código Lumenia.

## ⚪ P4 — cobertura que nunca existiu

- Teste de sessão longa (`scripts/monitor_sessao.ps1` existe, sem critério de
  aprovação nem execução registrada como gate).
- Validação com artista real fora da máquina de desenvolvimento.

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
