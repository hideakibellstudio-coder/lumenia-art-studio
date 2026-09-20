# Lumenia — estado da base e o que fazer nela

*2026-09-15. Números medidos, não estimados. Escrito para ser executado por um
agente que não acompanhou a sessão: cada item diz onde mexer, por que agora, e
como verificar que funcionou.*

---

## 0. Como ler este documento

A ordem importa e não é por tamanho. É por **dependência**: um item resolvido
fora de ordem ou não se sustenta, ou desperdiça o trabalho do seguinte. Onde a
ordem é obrigatória, está dito explicitamente.

Três regras que valem para todos os itens, e que vieram de erros reais desta
base:

1. **Meça antes de corrigir.** Nesta sessão, quatro hipóteses minhas sobre a
   causa de um bug foram derrubadas por um diagnóstico de vinte linhas. Escreva
   o probe, rode contra o binário, leia o resultado. Só então mude código.
2. **Nada de guarda defensiva nova.** `if hasattr(x, "y"): x.y = v` foi o
   mecanismo que escondeu sete controles mortos por meses. Falhar alto é o
   comportamento pedido.
3. **Fixe antes de mexer.** Toda mudança em código de renderização começa por um
   teste de caracterização que grava o comportamento atual. Se um pino quebrar
   e você não souber explicar por quê, reverta — não regrave o pino.

---

## 1. Estado medido

### Governança (ARCcC-Navigator, snapshot `snap_1789489546_d94b27da`)

| | |
| :--- | ---: |
| `confirmed_violation` | 0 |
| `suspicious` | 191 |
| `declared_exception` | 19 |
| `insufficient_info` | 0 |
| símbolos / relações | 9.863 / 53.501 |
| zonas LOC (verde/amarela/vermelha) | 456 / 49 / 4 |

> Esta medição é **anterior** às mudanças de hoje. Reindexe antes de usá-la
> como referência.

### Testes

| | |
| :--- | ---: |
| suíte completa | ~500 testes |
| contrato de parâmetros de pincel | 95 |
| caracterização de composição | 13 |
| caracterização de traço | 31 |

### A ponte interface ↔ motor

| | |
| :--- | ---: |
| `ui/engine_backends/` | 1.861 linhas, 182 métodos |
| referências a `self._facade` | 456 |
| guardas `hasattr(self._facade, …)` | **107** |
| métodos em `EngineBackend` | 152 — **137 sem corpo real** |
| métodos declarados no `.pyi` | **135** |
| métodos expostos pelas bindings | **198** |

Os **63 métodos de diferença** entre o `.pyi` e as bindings são a métrica mais
importante deste documento. O `.pyi` é o contrato que a interface e as
ferramentas leem. Ele está errado, e tudo que depende dele herda o erro.

---

## 2. O que já foi fechado (não refazer)

Fechado nesta rodada, com teste:

- **Tabela única de parâmetros de pincel.** `ui/engine_backends/brush_param_table.py`
  declara 43 parâmetros uma vez cada. `get_brush_profile_dict`,
  `apply_brush_preset_dict` e `set_brush_param` derivam dela. As quatro listas
  paralelas mantidas à mão deixaram de existir.
- **Sete controles mortos.** `jitter_size`/`jitter_angle`/`jitter_position`
  escreviam num grupo `dynamics` inexistente; `jitter_opacity` e
  `scatter_radius` não existem no motor e foram removidos; `blend_mode` mandava
  `int` onde a binding exige `DabBlendMode`, lançando `TypeError` num slot Qt;
  `jitter_position` e `jitter_angle` escreviam valor cru de slider (0–100) em
  campos 0..1 — `jitter_position` dispersava os dabs por 100× o raio.
- **`set_brush_param` lança `KeyError`** em vez de descartar em silêncio.
- **`_last_brush_preset` sincronizado** antes de trocar de contexto de documento
  (`aladyn_mdi_mixin.py`). Era a regressão do estabilizador.
- **`FilterApplier` decomposto** 431 → 39 linhas, com pinos de composição.
- **Estabilizador × baixa latência** — mudança escrita, **não verificada**
  (item 3.1).

---

## 3. O que fazer, em ordem

### P0 — Sem isto, nada é verificável

#### 3.1 Verificar a mudança do estabilizador *(pendente agora)*

O `StrokeOrchestrator.cpp` e o `PaintEngineFacade.cpp` foram alterados e **não
foram recompilados**. A mudança troca `ctx.lowLatency` por
`usarAtalhoDeLatencia(ctx)`, que é `lowLatency && estabilização <= 0.5`.

```powershell
python scripts/build_native.py
python -m pytest tests/test_stroke_characterization.py -v
python -m pytest
```

Critério: os **8 pinos** continuam batendo; `test_baixa_latencia_respeita_o_estabilizador`
passa nos 4 casos; `test_estabilizador_muda_o_traco_em_baixa_latencia` passa nos 2;
`test_no_raw_a_baixa_latencia_desliga_mais_que_o_estabilizador` continua passando.

Se um pino quebrar: reverta. Não regrave.

#### 3.2 Restaurar a CI *(F-020 depende disto)*

`.github/workflows/ci.yml` **não existe no disco**. Foi apagado em algum ponto
entre `e23e67a` e hoje, e é a explicação mecânica de por que as regressões
desta sessão passaram despercebidas por semanas. O conteúdo recuperado está em
`docs/audit/ci.yml.recuperado`.

Restaure-o, e só então adicione a matriz AVX2 (F-020) — hoje só `--simd scalar`
é construído e testado, e o caminho AVX2 nunca roda automaticamente.

Critério: um push dispara o workflow e ele fica verde.

---

### P1 — O contrato Python ↔ C++

#### 3.3 Verificar o `.pyi` contra o módulo compilado

**Este é o item de maior retorno do documento.** Um teste que compara
`bridge/boundary/contracts/aladyn_engine_native.pyi` com o módulo importado, por
introspecção. PyBind11 expõe as assinaturas no `__doc__` de cada método;
`dir()` e `inspect` dão o resto.

Divergências já conhecidas, para servir de caso de teste:

| ausente do `.pyi` | existe nas bindings |
| :--- | :--- |
| `PaintEngineFacade.set_render_options` | `bind_canvas.cpp:66` |
| `PaintEngineFacade.set_low_latency` / `get_low_latency` | `bind_canvas.cpp:60-61` |
| `PaintEngineFacade.begin_stroke_raw` / `update_stroke_raw` / `end_stroke_raw` | `bind_stroke.cpp:53-59` |
| `PointerEvent.tilt_x` / `tilt_y` / `twist` | `bind_math_brush.cpp:151-153` |

Decida **uma** direção e siga: ou o `.pyi` passa a ser gerado a partir das
bindings, ou o teste falha até que alguém o atualize à mão. A segunda é mais
barata e suficiente.

Critério: o teste falha hoje (63 métodos de diferença) e passa depois de o
`.pyi` ser completado.

#### 3.4 Regra: todo `.cpp` em todas as listas de fontes

Existem **duas** listas de fontes C++ mantidas em paralelo:
`setup.py::cpp_sources` e `tests/native/build_history_faults.py::SOURCES`.
Adicionar um arquivo só na primeira produz 10 erros de coleta no pytest, com
mensagem que não aponta para a causa. Aconteceu nesta sessão.

Um teste que varre `engine/**/*.cpp` e `bridge/**/*.cpp` e exige presença em
ambas as listas custa ~15 linhas.

---

### P2 — Simplificar a ponte

O diagnóstico completo está em `docs/audit/PLANO_SIMPLIFICACAO_PONTE.md`. O
passo 2 daquele plano (tabela declarativa) está **feito**; o passo 1 virou o
item 3.3 acima. Restam dois.

#### 3.5 Entrada única do facade — eliminar as 107 guardas

Substitua `if self._facade and hasattr(self._facade, "x")` por um
`_exigir_facade()` que lança quando não há contexto.

**Não** use um facade nulo (objeto no-op). Ele silencia erro real: chamar um
motor inexistente passaria a não fazer nada em vez de falhar — exatamente o
mecanismo que este documento inteiro existe para eliminar.

Faça depois do 3.3: enquanto o contrato não for confiável, remover as guardas é
imprudente; depois dele, cada guarda removida é um ramo a menos para testar.

Critério: `grep -rn "hasattr(self._facade" ui/engine_backends/ | wc -l` → 0.

#### 3.6 Protocolos por papel em vez de uma interface de 152 métodos

`EngineBackend` tem 152 métodos numa classe só, 137 sem corpo. Os mixins **já**
definem o recorte natural: pincel, camada, seleção, transformação, cor,
geometria, recursos, traço, MDI. Trocar a interface única por protocolos por
papel não inventa estrutura — nomeia a que já está lá.

Ganho concreto: hoje, para testar qualquer coisa é preciso um backend inteiro.
Com papéis, cada um é implementável e testável isoladamente.

Custo: mecânico, mas toca muitos arquivos. Faça por último.

---

### P3 — Governança

#### 3.7 Não-conformidades abertas

| Código | O quê | Onde |
| :--- | :--- | :--- |
| **F-018** | Três tetos de LOC divergentes: pytest (500/499, só Python, sem exceções), Navigator (450, Python+C++, com exceções), `test_arccc_cpp_and_docs_governance.py` (500, C++, sem exceções) | unificar em 450 com mecanismo de exceção único |
| **F-019** | `ARCHITECTURE.md` diz C++17; `AGENTS.md`, `VISION_AND_ROADMAP.md` e o Navigator dizem C++20 | uma linha |
| **F-020** | CI só testa `--simd scalar` | depende de 3.2 |
| **F-028** | `render_settings_dialog.py:375` chama `backend.refresh_display()`, que só existe no contrato nativo — dribla a abstração | incluir na interface canônica ou declarar exceção |

#### 3.8 ~60 anotações de tipo ausentes

A regra `missing_type_annotation` do Navigator aponta ~60, das quais ~25 estão
no raio de impacto da Fase 3. Cada anotação melhora a resolução do próprio
Navigator, então o retorno é composto.

#### 3.9 O documento de auditoria está desatualizado

`docs/audit/PRE_FEATURE_FREEZE_AUDIT.md` e a cópia nos docs do projeto
divergem, e nenhum dos dois reflete o estado de hoje. Reconcilie antes de usar
qualquer número de lá.

---

### P4 — Cobertura que não existe

Nenhum destes tem automação hoje, e os três são critério de saída para a Fase 3:

- **Teste de sessão longa.** Memória, handles e objetos GDI não podem crescer
  monotonicamente. `scripts/monitor_sessao.ps1` já coleta as amostras; falta o
  critério de aprovação e a execução.
- **Validação com artista real**, fora da máquina de desenvolvimento, no
  instalador final.
- **As 191 suspeitas explicadas uma a uma** — exceção declarada, ou investigada
  e aceita. Um relatório limpo sobre um índice vazio é pior que um relatório
  sujo.

---

## 4. O que NÃO fazer

**Não colapse as camadas.** A separação interface → contrato → adaptador →
motor é o que permite `wgpu_rust.py` existir ao lado de `aladyn.py`. Ela parece
uma estrada longa demais e é a razão de o motor ser trocável. O alvo é a
duplicação de declaração, não o número de saltos.

**Não adicione feature nenhuma.** Nem pincel, nem filtro, nem formato. Cada item
acima **remove** código ou adiciona verificação. Uma feature nova antes de a base
fechar herda todos os buracos que ainda estão abertos.

**Não regrave um pino golden** sem saber exatamente qual mudança de
comportamento ele está registrando e por que ela foi pedida.

**Não reintroduza guarda defensiva.** Se um campo pode não existir, ou o
contrato está errado (conserte o contrato) ou a chamada está errada (conserte a
chamada). `hasattr` como resposta padrão é o que criou esta lista.

**Não confie em análise estática para responder "funciona?".** O Navigator
responde "onde olhar" — foi ele que apontou o `FilterApplier` e trouxe a
investigação para a camada de pincel. Quem responde "o que é verdade" é um probe
executado contra o binário. As duas perguntas são diferentes, e a segunda não se
responde por leitura de código.

---

## 5. Critério de pronto

A base está sólida o bastante para a Fase 3 quando:

1. A CI existe, roda, e cobre `scalar` e `avx2`.
2. O `.pyi` bate com o módulo compilado, provado a cada execução.
3. `hasattr(self._facade` chega a zero.
4. `confirmed_violation: 0` **e** toda `suspicious` remanescente explicada
   individualmente.
5. F-018, F-019, F-020 e F-028 fechados.
6. Um teste de sessão longa que passe.
7. Um artista real desenhou no instalador final e o resultado foi aceito.

O item 2 é o que carrega os outros: enquanto o contrato mentir, tudo construído
sobre ele é suposição.
