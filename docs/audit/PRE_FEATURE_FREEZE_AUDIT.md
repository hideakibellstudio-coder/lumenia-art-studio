# Auditoria de Endurecimento Pre-Fase 3 (F-017 a F-031)

Continuacao de `docs/audit/AUDIT_CLOSURE_REPORT.md` (F-001 a F-016, todas RESOLVIDAS).

> **Descoberta principal desta auditoria:** por varias rodadas, o `verify` do
> ARCcC-Navigator apontou 127 e depois 67843 "suspeitas" no motor C++. Nenhuma
> delas era risco arquitetural do Lumenia. O que estava acontecendo e pior e
> mais importante: **a analise C++ estava desligada em silencio** — o libclang
> recebia flags no dialeto do MSVC, nao conseguia parsear nada, devolvia ZERO
> simbolos, e o indexador registrava `extraction_status='ok'` mesmo assim.
> Ou seja: a ferramenta que deveria provar que a base esta solida nao estava
> olhando para o motor, e nao avisava disso.

---

## Cronologia honesta das hipoteses (o que foi crido x o que os dados provaram)

| Versao | Hipotese em vigor | Como caiu |
|---|---|---|
| v1 | `engine/` estaria fora de qualquer guardrail | Falsa: o Navigator ja modela o motor via `LUMENIA_PROFILE`, com excecoes formais para os 4 arquivos C++ na zona vermelha |
| v2–v3 | Faltava `compile_commands.json`; seria a causa dos 127 `suspicious` | Falsa: gerado (48 entradas), `insufficient_info` caiu 1→0, mas os 127 continuaram **identicos, achado por achado** |
| v4 | Dois bugs no Navigator (`sym_by_usr` quebrado + regra `dynamic_dispatch_risk` casando a substring "dynamic") | Bugs reais e corrigidos, mas a correcao da regra causou **regressao: 127 → 67843**, por nao distinguir chamada externa de chamada indeterminada |
| v5 | Distinguir "Clang resolveu, mas fora do projeto" de "Clang nao resolveu nada" | Correcao certa, mas o reindex deu **exatamente o mesmo 67843** |
| v6 | O `index` herdava relacoes antigas por causa do copy-on-write; faltava subir `extractor_version` | Verdade parcial: o bump funcionou (`"changed": 528`), mas o resultado **continuou 67843** |
| **v7** | **As flags MSVC do compile database quebravam o libclang; a extracao C++ produzia zero simbolos em silencio** | **Confirmada** por consulta direta ao banco, e depois pela correcao (ver "Confirmacao") |
| **v8** | O ruido restante (59735) nao era C++: o resolvedor **Python** confundia "alvo fora do projeto" com "alvo indeterminado" — exatamente o mesmo defeito, do outro lado | Confirmada pela aritmetica exata: `references\|unresolved` 35871 + `calls\|unresolved` 23864 = 59735 |

O que encerrou a investigacao nao foi mais uma hipotese, e sim uma consulta
crua ao SQLite do Navigator (`diagnose_relation.py`):

```
bind_canvas.cpp -> extraction_status: 'ok', error_message: '', simbolos: 0
relations dessa linha -> id: 'snap_1789401065_...' (snapshot de HORAS antes)
```

Duas evidencias decisivas: (1) o arquivo foi dado como extraido com sucesso e
**nao produziu simbolo nenhum**; (2) o `id` da relacao carregava um snapshot
antigo, prova de que a linha foi **copiada por heranca**, nunca recalculada.

---

## A cadeia causal completa

1. `scripts/generate_compile_commands.py` (F-022) grava fielmente a linha de
   comando real do `cl.exe`, como manda o formato: `/c /nologo /O2 /W3 /GL
   /MD /EHsc /std:c++20 /Tpbridge/core/bindings/bind_canvas.cpp /Fo...`.
2. O libclang roda em driver estilo GCC, onde um argumento iniciado por `/`
   **nao e flag, e caminho de arquivo de entrada**. O
   `compilation_database.py::_clean_clang_args` repassava tudo quase intacto,
   entao o clang tentava abrir `/nologo`, `/O2`, `/EHsc` como arquivos-fonte.
3. O parse do arquivo real nao rendia cursor algum → `extract_cpp_file`
   devolvia listas vazias, **sem lancar excecao**.
4. Sem excecao, `extraction_status` ficava `'ok'` e nenhum diagnostico era
   emitido. Zero simbolos C++ (o total caiu de 8367 para 3540 = so os simbolos
   Python) e zero referencias C++.
5. Com zero referencias, nenhum arquivo C++ entrava em `already_extracted_cpp`,
   entao **todos** caiam em `inherit_relations_for_paths`, que copia as
   relacoes do snapshot anterior preservando ate o `id` antigo. As 67843
   "suspeitas" eram sempre as mesmas linhas de um snapshot pre-correcao,
   viajando de snapshot em snapshot.
6. Por isso nenhuma das correcoes v4/v5/v6 aparecia no relatorio: elas estavam
   certas, mas nunca chegavam a rodar sobre dados novos.

A ironia que importa registrar: **antes de existir o compile database, o
caminho de flags inferidas (`-std=c++20 -fms-compatibility -I...`) funcionava**
e produzia os 8350 simbolos originais. Gerar o `compile_commands.json` — item
que esta propria auditoria recomendou — foi o que apagou a analise C++.

### Confirmacao de que a analise C++ voltou (medida, nao suposta)

| Sinal | Antes da correcao | Depois |
|---|:---:|:---:|
| Tempo de `index` | 146 s | **518 s** (parse real acontecendo) |
| Simbolos totais | 3540 (so Python) | **8356** |
| Simbolos de `bind_canvas.cpp` | **0** | **36** |
| `BufferContract.hpp:13 calls max` | `unresolved`, `id` de snapshot antigo | **`extracted`, `id` do snapshot atual** |
| Buckets novos de confianca | inexistentes | `calls\|extracted` 1842, `references\|extracted` 337 |
| `cxx_empty_extraction` | (regra nao existia) | nenhum |

As chamadas `.def()` do PyBind11 em `bind_canvas.cpp`, que eram o exemplo mais
citado nos relatorios anteriores, **sumiram completamente da lista de
suspeitas** — com flags validas o Clang resolve os templates do pybind11.

---

## Correcoes aplicadas (todas ja commitadas no ARCcC-Navigator)

**1. `core/compilation_database.py` — traducao MSVC → clang.** `_clean_clang_args`
agora traduz o dialeto do `cl.exe` para o do clang: `/I`,`-I` → `-I`; `/D` →
`-D`; `/U` → `-U`; `/FI` → `-include`; `/std:c++20` → `-std=c++20`
(`c++latest` → `c++20`); `/external:I` → `-I`; descarta flags de
codegen/warning MSVC (`/nologo /O2 /W3 /GL /MD /EHsc /bigobj /openmp`), o
input `/Tp<arquivo>` e a saida `/Fo<obj>`; deduplica `-std=` e includes
repetidos; garante `-fms-compatibility`, `-fms-extensions` e os includes do
pybind11/Python. Validado contra o `compile_commands.json` real: das 29 flags
do `cl.exe` sobram 13 utilizaveis, **incluindo os includes da STL do MSVC e do
Windows SDK** — que o caminho de flags inferidas nunca teve. A analise C++
deve ficar melhor do que era antes do compile database, nao so consertada.

**2. `core/workspace.py` — fim da falha silenciosa.** Se um arquivo C++ parseia
sem excecao mas nao rende simbolo nem referencia, agora e emitido um
diagnostico `cxx_empty_extraction` (com a origem das flags: `database` ou
`inferred`).

**3. `core/verifier.py` — o silencio vira achado.** `cxx_empty_extraction` e
`clang_parse_error` (que antes era ignorado sem deixar rastro) agora entram
como `insufficient_info`, com remediacao apontando para as flags.

**4. `core/config.py` + `data/projects/edea68689819d43065d0.json`:**
`extractor_version` elevado a cada correcao que muda extracao/resolucao
(hoje `xl-contracts-v5`), obrigatorio para invalidar o copy-on-write e
forcar reprocessamento total — sem isso, nenhuma correcao aparece.

**5. `core/python_semantic.py` — o mesmo defeito, do lado Python (F-025).** Com o
C++ consertado, as 59735 suspeitas restantes eram todas Python:
`os.path.dirname`, `sys.exit`, `RuntimeError`, `.strip`, `.append`, `.get`,
`Pybind11Extension`. O resolvedor marcava como `unresolved` toda chamada ou
acesso a atributo que nao casasse com um simbolo do projeto — ou seja, a
stdlib inteira, os builtins, as bibliotecas de terceiros e os metodos de tipos
nativos. Nada disso pode esconder dependencia entre pilares ARCcC. A nova
funcao `_external_or_unresolved()` aplica o mesmo criterio do lado C++: se
**nenhum** simbolo do projeto tem aquele nome (ou a raiz e um builtin, ou um
import que aponta para fora da arvore), o alvo e necessariamente externo →
`extracted`. So continua `unresolved` o caso que interessa a auditoria: **o
nome existe no projeto, mas nao conseguimos provar qual simbolo e** — uma
dependencia interna possivelmente escondida atras de dinamismo.

**6. `core/verifier.py` — agregacao por arquivo (F-026).** A regra
`dynamic_dispatch_risk` emitia um achado por ocorrencia, o que permitiu que um
unico defeito de resolucao virasse 67843 "suspeitas" e tornasse o relatorio
ilegivel. Agora e **um achado por arquivo**, com a contagem e exemplos de
alvos. A informacao e preservada e uma regressao futura no resolvedor nao pode
mais inundar o relatorio.

**7. Correcoes anteriores (F-023), que so passaram a rodar sobre dados reais depois da correcao do F-024:**
`sym_by_usr` deixou de ser sempre vazio (o `sym.id.split(":")` quebrava o
prefixo literal `"c:"` de toda USR do Clang); foi adicionado o ramo de
resolucao para `relation_type == "references"`; e a regra
`dynamic_dispatch_risk` deixou de casar a substring "dynamic" (que marcava a
classe legitima e 100% estatica `DynamicStabilizer`) e passou a distinguir
chamada externa resolvida (`extracted`) de chamada realmente indeterminada
(`unresolved`).

---

---

## Estado medido apos o refinamento da ferramenta (snapshot `snap_1789415881`)

| Categoria | Antes do refinamento | Agora |
|---|:---:|:---:|
| Relacoes totais | 81.204 | **50.952** (−37%, duplicatas de chamada/cadeia removidas) |
| `confirmed_violation` | 0 | **1** |
| `suspicious` | 311 arquivos / 14.614 ocorrencias | **112 arquivos** |
| `declared_exception` | 7 | **21** |
| `insufficient_info` | 0 | 0 |

### F-028 (RESOLVIDO): violacao comprovada em `ui/core/dialogs/render_settings_dialog.py:375-376`

```python
if hasattr(backend, "refresh_display"):
    backend.refresh_display()
```

`refresh_display` e declarado em UM unico lugar no projeto:
`bridge/boundary/contracts/aladyn_engine_native.pyi:335`
(`PaintEngineFacade.refresh_display`). Nao existe em
`ui/core/engine/backend.py`. O caminho autorizado para essa chamada e o
adaptador `ui/engine_backends/aladyn.py:159-160`, via `self._facade` — e
`ui/engine_backends/` tem excecao declarada no perfil, enquanto
`ui/core/dialogs/` nao tem.

Um dialogo do pilar `ui` invoca um metodo que so existe no contrato nativo,
driblando a abstracao do backend. O `hasattr` e o sintoma: e duck-typing
defensivo porque o metodo nao faz parte da interface canonica.

**Decisao em aberto:** incluir `refresh_display` na interface canonica do
`EngineBackend` — que `tests/test_arccc_architecture_invariants.py` ja obriga
a estar totalmente coberta, entao o teste passaria a proteger isso — e
eliminar o `hasattr`; ou declarar excecao formal no perfil.

> Este achado existia desde o inicio. Com 67.843, 59.735 ou mesmo 311
> achados no relatorio, ele nunca seria visto. E a justificativa concreta
> do esforco de refinar a ferramenta antes de auditar o projeto.

### Refinamentos aplicados no ARCcC-Navigator (F-025 a F-027 + pacote de contexto)

- **Extrator Python:** passa a preservar o receptor da expressao (`self.x`, nao
  so `x`) e deixa de emitir referencia duplicada para o `.func` de uma chamada
  e para elos internos de cadeias `a.b.c`. Medido em dois arquivos reais:
  1301 → 776 relacoes, 1209 → 0 suspeitas, com **zero** informacao unica
  perdida (39 pontos de codigo resolvidos antes e depois).
- **Pacote de contexto:** consulta por classe devolve a classe (devolvia um
  metodo dela); bloco de contrato duplicado eliminado; "homonimos" nao lista
  mais variaveis locais; corpo longo elidido com marcador; consumidores de uma
  classe passam a incluir os membros dela; e a ordem de INCLUSAO passou a ser
  por valor (consumidores antes do corpo da implementacao), mantendo a ordem
  de EMISSAO numerica.
- **`navigator_verify` via MCP:** devolvia 194 mil caracteres e era rejeitado
  por exceder o limite de tokens do cliente; agora devolve sumario ordenado por
  severidade, com `limit` e `detail` sob demanda.

---

## Matriz de Nao-Conformidades

| Codigo | Descricao do Risco | Status |
|---|---|:---:|
| **F-017** | Perfil `lumenia` nao era o padrao do projeto no Navigator. | 🟢 **RESOLVIDO** — `data/projects/edea68689819d43065d0.json` com `architecture_profile: "lumenia"`. |
| **F-018** | Tres tetos de LOC divergentes: pytest (500/499, so Python, sem excecoes), Navigator (450, Python+C++, com excecoes) e `test_arccc_cpp_and_docs_governance.py` (500, C++, sem mecanismo de excecao). | 🟢 **RESOLVIDO** — criado `tests/arccc_governance_rules.py` como fonte unica (`MAX_LINES_ERROR = 450` + excecoes declaradas espelhando o perfil `lumenia`); os dois testes passaram a importar de la. Validado contra os LOC reais: 4 arquivos C++ sob excecao, maior `.py` em 449 (uma linha do teto). Corrigiu tambem um teste que estava vermelho por construcao (reprovava `PaintEngineFacade.cpp`, 652 linhas, sem mecanismo de excecao). |
| **F-019** | `ARCHITECTURE.md` diz C++17; AGENTS.md, VISION_AND_ROADMAP.md e o default do Navigator dizem C++20. | 🟢 **RESOLVIDO** — 3 ocorrencias corrigidas para C++20 (mesma largura, caixa ASCII preservada). |
| **F-020** | CI so builda/testa `--simd scalar`; caminho AVX2 nunca testado automaticamente. | 🟡 **PATCH PRONTO, APLICACAO MANUAL** — job `windows-avx2` separado (nao triplica a matriz), com passo proprio de verificacao de carregamento do modulo. `.github/workflows/` e caminho protegido e nao aceita escrita remota: aplicar a mao. |
| **F-021** | ~~Indice vazio~~ — falso alarme da v1; banco do projeto (~508MB) populado. Resta um `index.sqlite` de 0 bytes e um banco orfao de ~536MB. | ⚪ BAIXA PRIORIDADE |
| **F-022** | `compile_commands.json` ausente. | 🟢 **RESOLVIDO com ressalva** — gerado (48 entradas), mas foi ele que disparou F-024. So e seguro em conjunto com a traducao de flags. |
| **F-023** | Bugs de resolucao no Navigator (`sym_by_usr` sempre vazio, `references` sem ramo de resolucao, regra `dynamic_dispatch_risk` por substring) inflavam falsos positivos. | 🟢 **RESOLVIDO** — confirmado em dados reais: buckets `extracted` aparecendo e chamadas do pybind11 fora da lista. |
| **F-024** *(o mais grave)* | Analise C++ silenciosamente desligada: flags MSVC repassadas cruas ao libclang → 0 simbolos, `extraction_status='ok'`, nenhum diagnostico. Um motor inteiro fora da auditoria sem que o relatorio acusasse. | 🟢 **RESOLVIDO** — ver tabela de confirmacao (simbolos 3540 → 8356, `bind_canvas.cpp` 0 → 36). |
| **F-025** *(novo)* | Resolvedor Python confundia alvo externo (stdlib, builtins, terceiros, metodos de tipos nativos) com alvo indeterminado: 59735 falsas suspeitas. | 🟡 **CORRIGIDO, AGUARDANDO MEDICAO** — `_external_or_unresolved()` em `python_semantic.py`. |
| **F-026** *(novo, de design)* | `dynamic_dispatch_risk` emitia um achado por ocorrencia, permitindo que um unico defeito de resolucao produzisse dezenas de milhares de achados e tornasse o relatorio inutil. | 🟡 **CORRIGIDO, AGUARDANDO MEDICAO** — agregacao por arquivo. |
| **F-027** *(novo, housekeeping do proprio Navigator)* | `ARCcC-Navigator/core/verifier.py` esta com ~502 linhas, acima do teto de 450 que a propria ferramenta impoe aos projetos auditados. Cresceu mais nesta rodada. | 🔴 **AGRAVADO** — ver Atualizacao 2 |
| **F-029** *(novo)* | Resolucao por tipo anotado so olhava membros diretos; classe composta por mixins resolvia apenas os proprios metodos. | 🟢 **RESOLVIDO** (`xl-contracts-v8`) — `main_window_menu_builder.py` saiu da lista de suspeitas. |
| **F-030** *(novo, raiz)* | Extrator nunca indexou atributos de instancia (`self.x = ...`): classe que declara estado no `__init__` aparecia so com metodos, e receptores eram atribuidos a classes homonimas erradas. | 🟢 **RESOLVIDO** (`xl-contracts-v9`) — simbolos 8361 → 9762; `doc` → `Document` em vez de `RenderWidget`. |
| **F-031** *(novo, capacidade)* | `dynamic_dispatch_risk` dizia quantas relacoes ficaram soltas, nunca o que fazer com elas. | 🟢 **ENTREGUE** — regra `missing_type_annotation`: 60 achados nomeando a classe a anotar, cobrindo 834 relacoes. |

---

## Proximos Passos

1. Reindexar e verificar. **Este `index` vai demorar sensivelmente mais que os
   anteriores** — pela primeira vez o libclang vai parsear de verdade os 48+
   arquivos C++ com a STL do MSVC e o Windows SDK inteiros:
   ```powershell
   cd "Z:\DESENVOLVIMENTO\+ LUMENIA CLEAN\ARCcC-Navigator"
   python main.py index Lumenia
   python main.py verify Lumenia --profile lumenia
   ```
2. **Sinais de saude ja verificados na rodada anterior** (manter conferindo):
   simbolos na casa dos 8300+, nenhum `cxx_empty_extraction`, e os `id` das
   relacoes carregando o snapshot atual (`python diagnose_relation.py`).
3. So entao interpretar `suspicious` — agora com significado util: cada achado
   e **um arquivo** com N chamadas a nomes que existem no projeto mas nao
   foram resolvidas. Nenhum numero anterior serve de referencia (127, 67843 e
   59735 eram todos artefatos de defeitos distintos). Espera-se algo na casa
   de dezenas de arquivos, nao dezenas de milhares de linhas. Cada um merece
   olhada: ou e despacho dinamico intencional, ou e dependencia implicita
   entre pilares.
4. Depois: F-018 (unificar tetos de LOC), F-019 (C++17 → C++20 no
   ARCHITECTURE.md), F-020 (job de CI com `--simd avx2`).
5. Sem cobertura automatizada ainda: teste de sessao longa (memoria/VRAM nao
   devem crescer monotonicamente) e uma validacao subjetiva de artista real
   fora da maquina de desenvolvimento, no instalador final.

---

## Quando parar de "solidificar" e comecar a Fase 3

Criterios objetivos, revisados a luz do que esta auditoria descobriu:

1. **A auditoria precisa provar que olhou para o motor.** Nao basta
   `confirmed_violation: 0` — um relatorio limpo sobre um indice vazio e pior
   que um relatorio sujo. Exigir contagem de simbolos C++ plausivel e nenhum
   `cxx_empty_extraction` em massa.
2. `confirmed_violation: 0` e todo `suspicious` remanescente explicado
   individualmente (excecao declarada, ou investigado e aceito).
3. F-018, F-019 e F-020 fechados.
4. Um teste de sessao longa que passe.

O item 1 e a licao real desta rodada: uma ferramenta de governanca que falha
em silencio produz falsa confianca, que e exatamente o oposto do que esse
congelamento de features pretende comprar.

---

## Atualizacao (2026-09-15)

**F-028 resolvido pelo autor:** as duas linhas mortas foram removidas e o
`preview_bar.update()` movido para dentro do guard. Sem buraco funcional: o
`AladynColorMixin.set_soft_proofing` termina em `_mark_document_dirty("soft_proof")`,
a mesma via de atualizacao que o projeto ja usa para troca de perfil de cor.
`confirmed_violation` voltou a **0** no snapshot `snap_1789420373_6678e76e`.

**Estado do portao:** F-017, F-018, F-019, F-022, F-023, F-024 e F-028 fechados.
F-020 com patch pronto aguardando aplicacao manual. Permanecem abertos apenas os
dois itens que exigem execucao, nao codigo: o teste de sessao longa
(memoria/VRAM nao devem crescer monotonicamente) e a validacao subjetiva de
artista real fora da maquina de desenvolvimento. Mais os 112 arquivos com
referencias internas nao resolvidas, que agora sao uma lista de trabalho
legivel e nao um muro de ruido.

---

## Atualizacao 2 (2026-09-15) — a ferramenta passou a nomear o defeito

Esta rodada tratou o proprio ARCcC-Navigator como produto: enquanto ele
devolver "N relacoes nao resolvidas", cada auditoria custa horas de leitura
humana ou de credito de IA para chegar onde a ferramenta ja poderia ter
chegado sozinha. O alvo foi transformar ruido agregado em instrucao
acionavel.

### F-029: resolucao por tipo anotado ignorava heranca

`main_window_menu_builder.py` declarava `win: QtWidgets.QMainWindow` e usava 61
membros que so existem em `MainWindow`. Depois de corrigir a anotacao para
`win: MainWindow`, **38 das 61 continuaram nao resolvidas**. Causa: o
resolvedor procurava apenas `{classe}.{atributo}` — membros diretos. `MainWindow`
e composta por mixins (`MainWindowMenuActionsMixin`, `MainWindowRecoveryMixin`),
entao 38 dos membros vivem nas bases. A consciencia de heranca existia no
`verifier.py` e nunca havia sido colocada no `python_semantic.py`: eram dois
lugares e so um fora corrigido.

**Corrigido** (`xl-contracts-v8`): mapa de bases construido a partir das
relacoes `inherits` ja existentes no banco, busca em largura na hierarquia com
guarda de ciclo, e preferencia pelo import declarado no proprio arquivo
(inclusive sob `if TYPE_CHECKING`) em vez da busca ambigua por nome simples.
**Medido:** `main_window_menu_builder.py` saiu inteiramente da lista de
suspeitas.

### F-030 (o mais instrutivo desta rodada): atributos de instancia nunca foram indexados

Ao tentar nomear a classe dos receptores restantes, a regra recomendou
**anotar `document` como `RenderWidget`**. Ler `workspace_document_sync.py`
provou que `doc` e um `Document` de verdade (`doc.uid`, `doc.layer_manager`,
`doc.paper_texture_id`).

Causa raiz: o extrator indexava `AnnAssign` de corpo de classe, mas **nunca
`self.x = ...`**. Uma classe que declara seu estado no `__init__` — o padrao
normal em Python — aparecia no indice **so com metodos**. `Document` nao possuia
`zoom`, `pan_x`, `uid` nem `layer_manager`; `RenderWidget` declara esses nomes
como campos de classe e vencia **sem oposicao**. A classe certa nao perdeu a
disputa: ela nao estava na disputa.

**Corrigido** (`xl-contracts-v9`): atributos de instancia entram como
`instance_attr`, fora do indice por nome simples (para nao criar arestas falsas
por homonimia) porem dentro do indice qualificado. No mesmo passe foi corrigido
um bug antigo — anotacoes **locais** dentro de funcoes eram contadas como campos
da classe que as contem, inflando todo conjunto de membros.

**Medido:** simbolos 8361 → **9762**. `doc`/`document` → `Document`,
`layer` → `LocalLayer`, e `serializer.py document` saiu de `RenderWidget` 57%
(descartado) para `Document` 100%.

### F-031: regra `missing_type_annotation`

Mesma prova de coerencia ja validada (>= 4 atributos distintos, >= 60%
pertencentes a uma classe, heranca incluida) aplicada ao receptor **sem**
anotacao. Empate entre classe e base sua resolve pela mais derivada; empate
entre classes sem parentesco vira um achado que **declara a ambiguidade e lista
as candidatas** em vez de afirmar uma. As relacoes explicadas por ela saem da
contagem generica, para o mesmo problema nao ser contado duas vezes.

Duas guardas nasceram da medicao, nao do projeto:

- **nao acusar quem ja tem anotacao** — a regra dizia "`win` nao tem anotacao"
  sobre um parametro anotado horas antes. O caso real ali e outro: anotacao
  completa, contrato incompleto (`win.menu_bar = MenuBar(win)` atribui estado de
  fora da classe). Fica registrado como trabalho futuro, nao improvisado agora.
- **nao recomendar classe que so existe nos testes** — `DummyHost` cobria 100%
  de um uso em `ui/boundary/` por ser um duble com os mesmos metodos. Seguir a
  recomendacao criaria dependencia de producao para codigo de teste.

### Estado medido (snapshot `snap_1789442169_b1c2bb2f`)

| metrica | antes desta rodada | depois |
| :--- | ---: | ---: |
| `confirmed_violation` | 0 | **0** |
| simbolos | 8361 | **9762** |
| `insufficient_info` | 0 | **0** |
| achados `suspicious` | 105 | **191** |
| relacoes com classe-alvo nomeada | 0 | **834** |

O aumento de 105 para 191 **nao e piora**. Antes, um unico achado generico
engolia dezenas de relacoes sem dizer o que fazer com elas. Agora 60 desses
achados dizem qual classe anotar e quantas relacoes a linha de anotacao
converte em arestas reais do grafo.

### Peso destes achados no portao

Os 60 `missing_type_annotation` **nao sao defeitos de comportamento**. O
programa funciona identicamente com ou sem a anotacao. Sao lacunas de contrato
declarado: importam para a auditoria conseguir **provar** coisas sobre o codigo,
nao para ele estar correto.

Isso tem consequencia direta na decisao de Fase 3. O criterio do portao e
"nenhuma dependencia entre pilares escondida atras de dinamismo". Um receptor
nao anotado nao e prova de que ha dependencia escondida — e prova de que a
ferramenta **nao consegue descartar** que haja. Anotar converte incerteza em
fato verificado, nos dois sentidos: ou vira aresta legitima, ou revela um
acesso que nao deveria existir. Ate que isso seja feito, os 834 acessos
permanecem nao-decididos, e um portao honesto nao pode contar nao-decidido
como aprovado.

### Licao de metodo, de novo confirmada

Tres hipoteses minhas foram derrubadas por medicao nesta rodada: que anotar
`win: MainWindow` bastaria (faltava heranca), que o desempate por tamanho de
classe resolveria a absorcao pelo `RenderWidget` (faltava o indice de atributos
de instancia), e que a regra estava pronta para commit (acusava receptor ja
anotado e recomendava duble de teste). **Nenhuma foi descoberta por raciocinio
— todas por rodar um script de diagnostico contra o banco real e por ler o
codigo-fonte de um achado de amostra.** O procedimento agora e fixo: simular a
regra contra o banco antes de liga-la, e ler a fonte de pelo menos um achado
antes de confiar na regra.
