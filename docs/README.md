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
