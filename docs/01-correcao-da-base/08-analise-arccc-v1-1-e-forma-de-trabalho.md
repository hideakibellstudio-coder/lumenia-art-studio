# Análise sob o ARCcC v1.1.0 e como trabalhar no Lumenia (2026-10-01)

> **Perguntas que este documento responde:** (1) a nova versão do ARCcC
> (v1.1.0, 2026-09-29, escrita pelo dono) pede algo que a base ainda não
> cumpre? (2) Como devemos trabalhar daqui para frente, de modo que o trabalho
> de organização termine em vez de se multiplicar?
>
> **Base analisada:** `92e4543` (`main`). **Medido** no Linux do agente
> (Python 3.11; `lizard` 1.24.0 instalado fora do repositório). Os scripts de
> medição ficam no rascunho da sessão, fora do repositório; o método de cada
> número está no Apêndice A.
>
> **Limite do que sei:** o documento v1.1.0 chegou como arquivo da sessão e eu
> não tenho a versão anterior para comparar. Chamo de "novo" o que o
> repositório não cita nem aplica. O repositório cita o ARCcC em um único
> ponto numerado (a regra 15.4, duas vezes); a Seção 4.4 inteira (o fluxo de
> construção) não aparece em lugar nenhum.
>
> **Atualizado em 2026-10-01, depois de `4e5ee70`:** a Seção 9 traz o estado dos
> selos medido de novo (o que passou a 🟢, com o commit e o número, e o que
> continua 🟡 ou 🟠 e por quê). As Seções 2, 3.6 e 4 mostram o selo atual e,
> entre parênteses, o de antes.
>
> Relacionados: `07-analise-arccc-decomposta.md` (análise de 2026-09-26, da
> qual esta parte), `01-pendencias-atuais.md` (lista viva e linha de chegada),
> `../02-arquitetura/01-framework-arccc.md` (o documento do método no
> repositório, desatualizado: Apêndice E do relatório 07).

---

## 1. Resumo

1. **O que mudou de fato é o "como construir" (Seção 4.4).** O `AGENTS.md`
   tem 5 passos que *verificam* o trabalho (diagnóstico, edição, teste,
   higiene, validação). A 4.4 descreve o ciclo que *produz* o trabalho:
   responsabilidade → modelo → contrato → implementação mínima → teste →
   fatia vertical real → evidência → volta à fundação. Esse ciclo não está
   escrito em lugar nenhum do projeto.
2. **A base passa nas regras estruturais** (raiz reservada, camadas do motor,
   ponte fina, contrato da ponte testado, idioma dos identificadores) **e
   falha nas que a 4.4 acrescenta:** contrato público maior que a
   implementação, mecanismo criado para possibilidade que não existe,
   desempenho sem evidência versionada, contrato da ponte sem versão.
3. **Os 17 defeitos conhecidos (D1–D17) caem em 5 famílias**, e cada família
   é uma regra que existe no ARCcC sem trava automática que a faça cumprir
   (Seção 5). Isso responde por que "organizar" parece infinito: cada rodada
   acha instâncias novas da mesma família.
4. **Um defeito novo sob esta lente, D17:** se o motor C++ não carrega
   (binário ausente, de outra versão ou sem uma DLL), o app abre com o canvas
   vazio e só escreve uma linha de log de nível INFO. O usuário não é avisado
   (Seção 5.1).
5. **Como trabalhar:** o ciclo da 4.4 como laço por fatia, com as catracas
   existentes como piso, quatro regras de parada para o trabalho ter fim, e os
   pontos de extensão futuros *registrados e não implementados* (Seção 6).
6. **Mudanças propostas na linha de chegada: duas e só duas** (Seção 7): D17
   entra em S0.2 (mesmo padrão do D2), e nasce S0.8, benchmark versionado,
   porque S1 só pode cumprir o seu "pronto quando" se a medição estiver no
   repositório.
7. **Quatro decisões do dono** (Seção 8): idioma das mensagens de commit,
   limiar de complexidade, texto novo do `AGENTS.md`, e onde guardar o
   documento do ARCcC.

---

## 2. O que a v1.1.0 pede e onde o projeto está

| Seção do ARCcC | O que pede | No projeto | Situação |
|---|---|---|---|
| 2.1, 4.1 regras 1–2 (isolamento, sem dependência entre irmãos) | Pasta só importa de subpastas ou de infraestrutura contratada; irmãs não se importam | Lei 1 do `AGENTS.md` (plugins), catraca de camadas do C++, catraca de acoplamento | 🟢 |
| 2.3, 4.1 regra 5 (ponto único de entrada) | Cada pasta tem uma porta; o resto é privado | `__init__.py` em 60 pastas de `ui/`, README com "Porta de entrada"; catraca `door_bypass` (238 congeladas, nenhuma nova entra) | 🟡 com trava (era 🟠: convenção sem trava) (Seção 3.1) |
| 3.3 (arquivos essenciais) | `index`, `manifest.json`, `README.md`, `testes/` por pasta | README em toda pasta, com bloco `arccc:deps` **medido**; testes em `tests/` (exceção declarada) | 🟢 (o bloco medido substitui o `manifest.json` escrito à mão) |
| 4.2 (teste da caixa preta) | Trocar o interior de uma pasta não quebra ninguém | Vale para o motor e a ponte; não vale para as pastas de `ui/` (Seção 3.1) | 🟠 |
| **4.4 (fluxo de construção)** | Ciclo de 10 passos, fatia vertical, retorno à fundação, benchmark → evidência → arquitetura, 7 portas, "pronto arquitetural" | `AGENTS.md` 5.0 (o ciclo, as 6 perguntas e as regras de parada); 29 commits seguidos desde então seguem o ciclo, cada um com a medição na mensagem | 🟢 (era 🔴 ausente) |
| 4.4.4, 4.4.9 (responsabilidade antes de estrutura; sem mecanismo vazio) | Nada de gerente, registro ou protocolo "para depois" | Saíram: 4 tipos de plugin sem extensão (D9), o parâmetro `compositeBuffer` (D14), `PluginContext.backend` e `get_logger`. Falta: 10 dos 11 sub-protocolos do backend sem consumidor (`TelemetryProtocol` agora tem o `TelemetryTracker`) | 🟡 (era 🟠) (Seção 3.2) |
| 7.1 (gatilhos automáticos) | Dividir acima de 500 linhas, 5 métodos públicos, complexidade 10 | Zonas de 300/450 linhas (mais rígidas), complexidade 20 (decisão do dono: barreira em 20, alerta em 10). Medido de novo: C++ acima de 15 de 38 para 26 e acima de 20 de 25 para 15; Python acima de 20 de 21 para 20 | 🟡 limiares diferentes, por decisão (Seção 3.3) |
| 14 (idioma) | Todo identificador em inglês; branches, commits e tags também | Catraca de identificadores em 0 para os nomes; assunto de commit em inglês desde 2026-10-01 (29 seguidos, `git log`); branches já em inglês | 🟢 (era 🟡) (Seção 3.5) |
| 15 (multi-pilar) | Raiz só de pilares; só pela ponte; contrato único **e versionado**; ponte sem regra de negócio; testes de contrato | 5 de 6 regras 🟢 (a do contrato versionado fechou: versão 6, `.pyi` preso por hash); a regra 5 (release independente) segue 🟡 com 4 harnesses nativos isolados | 🟡 (Seção 3.6) |

---

## 3. Medições sob a nova versão

### 3.1 Portas de entrada (regras 1, 3 e 5; teste da caixa preta)

Das 60 pastas de `ui/` com `__init__.py`, 42 têm conteúdo (exportam algo) e 18
estão vazias. Olhando os imports que vêm de **fora** de uma pasta:

| Como entram | Imports |
|---|---|
| Pela pasta (a porta) | 281 |
| Direto num módulo interno de uma pasta cuja porta tem conteúdo | **325** |
| ... dos quais a porta **já exportava** o que foi importado | 239 |
| ... dos quais a porta **não exporta** o que foi importado | 86 |

Leitura: 54% dos imports de fora de uma pasta com porta passam por cima dela
(325 de 606), e 39% (239) poderiam ter usado a porta sem mudar a pasta. Onde a
porta é mais ignorada: `theme` (112), `core/engine` (51), `core/plugins` (45),
`core/document` (39), `core/dialogs` (29). Onde falta exportar: `core/document`
(19), `core/widgets` (18), `core/plugins` (14).

Por que importa: trocar o interior de `ui/infrastructure/theme` quebra 112
imports em outros arquivos. O teste da caixa preta (4.2) falha para as pastas
de `ui/`.

**Não é defeito que o usuário sinta hoje.** É risco de custo de mudança.
Tratamento proposto: catraca que impede o número de subir (como as de
acoplamento), sem corrigir o estoque; as 239 reescritas são mecânicas e podem
ser feitas pasta a pasta quando alguém mexer nela.

### 3.2 Superfície pública e mecanismos sem entrega (4.4.4, 4.4.9, 4.4.11)

A definição de pronto pede "contrato público menor que a implementação" e
"nenhuma complexidade artificial para possibilidade que não existe".

| Medida | Valor |
|---|---|
| `EngineBackend`: métodos públicos | 176 |
| `PaintEngineFacade` (C++): declarações públicas | ≈ 170 (contagem aproximada por expressão regular) |
| Classes Python de `ui/` | 325; com mais de 5 métodos públicos: 83; com mais de 20: 13 |
| Maiores | `EngineBackend` 176, `RenderWidget` 66, `AladynLayerMixin` 44, `AdvancedGeometryDialog` 39 |
| Sufixos "burocráticos" (4.4.4) em classes de `ui/` | `Controller` 9, `Manager` 7, `Registry` 3, `Service` 1 |

- O contrato do backend **é** a superfície inteira da facade espelhada: 176 de
  um lado, ≈170 do outro. Isso é o oposto de "contrato menor que a
  implementação". Foi o risco R1 do relatório 07.
- **Os 11 sub-protocolos do backend não têm consumidor.** Cada um é citado só
  na definição (`backend_protocols.py`) e no teste que confere o contrato
  (`tests/test_engine_backend_protocols.py`). Existem para uma possibilidade
  (consumidor que dependa de uma fatia do backend) que não aconteceu. É o caso
  exato da 4.4.9: "sem implementar mecanismos vazios".
- Os outros mecanismos sem entrega já registrados: `compress_inactive_layers`
  (D8), `PluginType.BRUSH/FILTER/TOOL/IO` (D9) e o parâmetro `compositeBuffer`
  que a interface dos motores promete e os 8 motores ignoram (D14).
- Existem 22 métodos do backend sem chamada direta em `ui/` (21 só aparecem em
  testes). **São candidatos, não defeitos:** alguns são chamados por métodos do
  próprio contrato (`backend.py:292` chama `self.flood_fill`). Verificar um a
  um antes de remover.
- O limiar "mais de 5 métodos públicos" da 7.1 não serve como regra geral para
  uma interface Qt (83 classes disparariam). Vale para classes de **contrato**
  (backend, facade, estados): lá a resposta é a Seção 6.4.

Os sufixos burocráticos são poucos (20 classes). Não são problema medido; a
pergunta da 4.4.4 ("que responsabilidade concreta não cabia no componente
atual?") vale como pergunta ao mexer em cada um.

### 3.3 Complexidade nos limiares do documento (7.1)

`lizard` (conta também `&&` e `||`):

| Pilar | Funções | Acima de 10 | Acima de 15 | Acima de 20 |
|---|---:|---:|---:|---:|
| `engine/` (C++) | 750 | 64 | 38 | 25 |
| `ui/` (Python) | 2603 | 85 | 37 | 21 |
| `bridge/` | 9 | 0 | 0 | 0 |

O documento pede refatorar acima de 10: seriam **149** funções (64 + 85). O
projeto adotou 20 (McCabe do `ruff`, que não conta operadores booleanos; o
`lizard` conta, por isso 46 acima de 20 aqui contra 6 `noqa: C901` lá). A
ponte tem funções simples; o resto da complexidade está nos 9 motores de pincel
e nos filtros (R2 do relatório 07). Ver decisão 2 na Seção 8.

(O relatório 07 contou 759 funções de C++: 750 do motor mais 9 da ponte.)

### 3.4 Falha que não chega a quem chamou

O D2 (falha ao criar contexto do documento) tem um irmão que só aparece sob a
lente da regra 15.4 nº 3 (contrato versionado):

- `ui/infrastructure/bridge_client/aladyn.py:79`: `import aladyn_engine_native`
  dentro de `try/except Exception`, que registra com `logger.info` e segue
  com `self._native = None`.
- `ui/core/engine/registry.py:67`: sem backend, registra "A interface roda em
  modo casca (canvas vazio)" também em `info`.
- Nenhuma tela, caixa de diálogo ou chave de tradução avisa o usuário.
  `main.py` não menciona o motor.
- O módulo nativo não expõe versão: `engine_bindings.cpp` só define
  `m.doc(...)`. A `version="0.2.0"` do `setup.py` e o `native-build.json`
  (gravado por `scripts/build_native.py`) não são lidos por ninguém na
  execução.
- O `AGENTS.md` registra o incidente de 2026-09-22: "cópias em outras pastas
  carregam binários velhos em silêncio".

Resumo do D17 na Seção 5.1. O detector mais simples da família ("`except` cujo
corpo só registra e segue") acha 41 handlers em `ui/` (debug 18, warning 12,
error 10, critical 1; 38 capturam `Exception` ou nada). É piso, não teto: o
D17 registra **e atribui**, e nem entra nessa contagem. Parte dos 41 é
legítima (o gerenciador de plugins isola falha de plugin de propósito); por
isso a proposta é catraca de contagem, não proibição.

### 3.5 Idioma (Seção 14)

- Identificadores: coberto por catraca (`test_arccc_identifier_language_ratchet`).
- A 14.1 lista "branches, commits e tags" como nomes que ficam em inglês. O
  histórico tem 296 commits, dos quais **178** têm marca de português no
  assunto (acento ou palavra comum; heurística, então é piso). Os branches já
  estão em inglês (o repositório não tem tags). Ver decisão 1.
- Pastas em `kebab-case` não se aplicam a pacotes Python (importáveis só em
  `snake_case`); a própria 14.3 diz que cada linguagem mantém a sua convenção
  de caixa.

### 3.6 Multi-pilar (15.4)

| # | Regra | Situação medida |
|---|---|---|
| 1 | Raiz reservada aos pilares | 🟢 `tests/test_arccc_root_layout.py`; exceção declarada (`tests`, `docs`, `assets`, `scripts`, `benchmarks`) |
| 2 | Comunicação só pela ponte | 🟢 os 3 imports de `aladyn_engine_native` em `ui/` estão todos em `ui/infrastructure/bridge_client/` (`aladyn.py`, `aladyn_brush_mixin.py`, `aladyn_resources_mixin.py`); fora dali, só teste de caixa-branca declarado |
| 3 | Contrato **único e versionado** | 🟢 (era 🟠) único: sim (2 `.pyi`, comparados com o binário em teste, inclusive a assinatura de cada método); **versionado: sim**, `kContractVersion` = 6 no binário e `EXPECTED_CONTRACT_VERSION` na interface, `.pyi` preso por hash em `tests/golden/bridge_contract.json`; binário de outra versão é recusado na partida com a causa na tela |
| 4 | Ponte sem regra de negócio | 🟢 9 funções, nenhuma acima de 10; 1.438 linhas contando os `.pyi` |
| 5 | Pilar com release independente | 🟡 4 harnesses nativos isolados (era 1): falhas do histórico, ordem do Borrar, 52 pinos do `blendPixel`, núcleo de dab com o codec de tiles; o resto dos testes do motor ainda passa pela ponte |
| 6 | Testes de contrato na ponte | 🟢 `test_pyi_contract_matches_binary.py`, `test_bridge_error_policy.py` (ficam em `tests/`, exceção declarada) |

### 3.7 As 7 portas de validação (4.4.10) contra o que o projeto automatiza

| Porta | O que existe | Lacuna medida |
|---|---|---|
| 1. Responsabilidade clara | README por pasta, conferido por `test_arccc_package_docs` (arquivos e dependências verdadeiros) | Que a frase de responsabilidade seja uma só (4.3) é lida por gente; nada mede |
| 2. Contrato definido | `.pyi` × binário, enums canônicos, `PANEL_CONTRACTS`, catraca de acoplamento | Número solto onde falta enum (D1); contrato sem versão (D17) |
| 3. Teste isolado | 137 arquivos de teste | Motor só testável pela ponte, salvo 1 teste nativo |
| 4. Integração validada | Testes dos "grandes rios", `tests/test_lowlevel_*`, caracterização | — |
| 5. Invariantes preservadas | Golden de traço e composição; catracas | Golden de traço só para o motor padrão (R11) |
| 6. Desempenho medido | `test_giant_brush_smoothness_and_throughput.py` (limites por fator de máquina); `benchmarks/run_engine_benchmarks.py` (só o motor; o teste confere o formato da saída) | Nada mede repintura, abrir, salvar, entrada pela interface. Os números do relatório 07 vieram de 4 scripts do rascunho da sessão |
| 7. Documentação atualizada | READMEs com dependências medidas; changelog | O documento do método está desatualizado (D10, Apêndice E do 07) |

**A porta 6 é a mais fraca e a que mais pesa.** A 4.4.8 diz "nunca transformar
intuição de desempenho em arquitetura antes de medir" e fecha o ciclo com
"novo benchmark". S1 (exibição por região, salvar em segundo plano) tem metas
numéricas ("repintura 4K < 4 ms"); sem a medição no repositório, a meta não é
verificável por quem vier depois, e o ciclo não fecha.

---

## 4. Pronto arquitetural por componente (4.4.11)

A definição pede: caixa dona da responsabilidade; contrato menor que o
interior; consumidores sem conhecer o interior; invariantes testáveis;
integração real; documentação batendo com o código; sem complexidade artificial.
Selos herdados do relatório 07, revistos com a nova lente:

| Componente | Selo | O que falta para "pronto" |
|---|:---:|---|
| Camadas, tiles e histórico do motor | 🟢 | Nada de estrutural. Tem teste nativo isolado e injeção de falha em disco; agora também o codec de tiles do arquivo, conferido sem a ponte |
| Estado compartilhado (`ui/core/state`) | 🟢 | Nada. Um escritor por assunto, valor igual não emite |
| Compositor e mesclagem | 🟢 (era 🟡) | Nada. `blendPixel` de complexidade 32 para 13, as duas sobrecargas de região unificadas (`Compositor.cpp` de 215 para 130 linhas, complexidade máxima 6) e `LayerMerger` de 32 e 19 para 12; nenhum pixel mudou (60 milhões de casos contra a versão anterior, 52 hashes de 4096 casos, 4 resumos de mesclagem e achatamento, golden de composição). `477ec19` |
| Seleção e transformação | 🟡 | Prévia (Qt) diferente do resultado (motor): D11, **não tratado**. Fechar pede uma prévia pelo amostrador do motor, um método novo na ponte e a decisão de custo por movimento do mouse; severidade baixa, fica para quando a feature de transformação for mexida |
| Ponte | 🟢 (era 🟡) | Nada. Contrato versionado e preso (versão 6); GIL solto em 3 lugares, cada um com a razão na política de `bridge/README.md` e travado por `tests/test_bridge_gil_policy.py`; a tela pede só a região (`get_display_region`), e as cópias de canvas inteiro que sobram (4 chamadas de `get_qimage` na interface: copiar para a área de transferência, gravação, prévia do traço e exportar a imagem) são de caminhos que precisam do canvas inteiro; a lupa do conta-gotas, que copiava o canvas para recortar 18×18 pixels (50 ms em 4K a cada movimento do mouse), passou a pedir só esses pixels (0,45 ms). `28bb597` |
| Telemetria do motor | 🟢 | Instrumento certo |
| Telemetria da tela (medidores) | 🟢 (era 🟠) | Nada. O medidor 6 conta a cópia do canvas e o `drawImage` (D16, `tests/test_viewport_paint_telemetry.py`) e as telas passam pelo `TelemetryTracker` para chegar ao motor. `0487eff`, `4e5ee70` |
| `EngineBackend` | 🟡 (era 🟠) | Contrato com 178 métodos, o tamanho da facade. Feito: a gravação e a abertura ganharam o contrato estreito `PersistenceBackend` em vez de 6 métodos a mais; o `TelemetryProtocol` tem consumidor (o tracker, 14 pedidos ao registro viraram 1); o `PluginContext` deixou de entregar o motor inteiro a todo plugin; a catraca `registry_lookup` congela os pedidos globais do motor (49 hoje) e só deixa descer. Falta: 10 dos 11 sub-protocolos sem consumidor e migrar os 49 pedidos para injeção, arquivo por arquivo, junto da feature que o tocar |
| Motores de pincel (9) | 🟢 (era 🟠) | Nada. D14 saiu; 108 pinos de pixel (12 variações por motor, inclusive textura, elipse girada, dureza 0 e 1, modos de dab e parâmetros de cada motor); o núcleo comum (`DabFootprint`, `PixelPermission`, `TipShape`, `StraightOver`) fez cada `renderDab` ir de 129–273 linhas e complexidade 25–71 para 19–57 linhas e 6–15; 2 pinos regravados de propósito (Óleo e Borrar em ponta achatada: 132 e 186 de 49152 bytes, no máximo 2 níveis). `4101a56`, `230f77c` |
| Documento e camadas | 🟢 (era 🟡) | Nada no documento: as 6 propriedades de camada são uma tabela (`layer_properties.py`) e os 8 lugares que as repetiam a percorrem; uma propriedade nova entra só ali (`tests/test_layer_property_registry.py` acrescenta uma e confere cada lugar; tirá-la de qualquer consumidor reprova). A interface (painel, menu, diálogo) e o método do motor continuam sendo da propriedade. `f9e8ad1` |
| Plugins | 🟢 (era 🟠) | Nada de arquitetura. Os 4 tipos sem extensão saíram (D9) e o `PluginContext` tem 3 nomes (`service_registry`, `main_window`, `attach_main_window`), sem o motor e sem logger, travados por `tests/test_plugin_context_contract.py`. Limite que não é de arquitetura: um plugin segue sendo código Python no mesmo processo; isolar pede decisão de produto (gatilho: o 1º plugin externo). `22ea776` |
| Exibição | 🟢 (era 🔴) | Nada. A tela pede só a região (`get_display_region`, `get_display_lod_region`); repintura a 100% em 4K de 34 ms para 0,5 ms; zoom afastado depois de uma mudança 0,28 ms; com perfil de cor ≠ sRGB, de 392 ms para 0,59 ms (o resíduo da D18, fechado). `a5d7fc5`, `1abc684`, `e16a315` |
| Arquivo (salvar e abrir) | 🟡 (era 🔴) | Salvar não trava (captura de 0,8 a 2,4 ms). Abrir um documento 4K com 10 camadas todas pintadas ainda para a janela na composição única da adoção: no `restore_document` isolado, 0,21 s dos quais 0,199 s são o `end_batch` nativo (o resto, 12 ms); no benchmark de `files_dense`, 0,56 s (0,559, 0,554 e 0,577 em três rodadas), porque o processo já guarda três cópias do documento (330 MB cada) e a primeira composição de um contexto novo paga as páginas do buffer de saída. Esparso 0,1 s. O "pronto quando" de S1.2 (abrir em menos de 1 s) está cumprido; "sem travar" para o documento denso não. O que fecha, medido nesta sessão: a composição é uma só e já usa os 4 núcleos; compô-la em faixas por volta do laço de eventos pede estado de "composição devida" na fachada, leitores que a concluam antes de ler o buffer, e o alvo por documento (o usuário pode trocar de aba no meio); construir o documento numa fachada solta, em outra thread, e anexá-lo em tempo constante pede reescrever o `restore` para uma fachada que não é a ativa. As duas são mudança de motor e de ponte (versão 7) e regra nova de posse entre threads, para custo de 0,2 s numa abertura rara do pior caso; não as tomei sem o dono pedir |

---|:---:|---|
| Camadas, tiles e histórico do motor | 🟢 | Nada de estrutural. Tem teste nativo isolado e injeção de falha em disco |
| Estado compartilhado (`ui/core/state`) | 🟢 | Nada. Um escritor por assunto, valor igual não emite |
| Compositor e mesclagem | 🟡 | `BlendEquations` com complexidade 32; golden dos 8 cenários existe |
| Seleção e transformação | 🟡 | Prévia (Qt) diferente do resultado (motor): D11 |
| Ponte | 🟡 | Contrato sem versão; GIL liberado em 1 lugar; pixels saem por cópia |
| Telemetria do motor | 🟢 | Instrumento certo |
| Telemetria da tela (medidores) | 🟠 | Mede só o `drawImage` e esconde a cópia do canvas: D16 |
| `EngineBackend` | 🟠 | Contrato do tamanho da facade; 11 protocolos sem consumidor |
| Motores de pincel (9) | 🟠 | Interface promete o que não faz (D14); golden de 1 em 9 (R11); rasterização repetida 9 vezes (R2) |
| Documento e camadas | 🟡 | Uma propriedade de camada (trava de alfa) está em 34 arquivos: é o gatilho semântico "preciso alterar X para mudar Y" da 7.2 |
| Plugins | 🟠 | Tipos sem ponto de extensão (D9); `PluginContext` largo (R9) |
| Exibição | 🔴 | Contrato "canvas inteiro" (D4/R4) |
| Arquivo (salvar e abrir) | 🔴 | Síncrono (D3) |

---

## 5. Defeitos sob esta lente

### 5.1 D17 (novo)

| Id | Defeito | Evidência | Severidade | Raiz | Correção |
|---|---|---|---|---|---|
| **D17** | Falha ao carregar o motor vira "modo casca" com log INFO; o usuário vê um canvas vazio sem explicação. O módulo não expõe versão, então um binário de outra versão também passa em silêncio | `aladyn.py:79`, `registry.py:67`, `engine_bindings.cpp`, `AGENTS.md` (incidente de 2026-09-22) | **Média** (latente: só ocorre com instalação quebrada, por exemplo uma dependência do sistema faltando, mas aí o usuário não recebe nenhuma pista) | Falha que não chega a quem chamou (regra de contrato) e contrato da ponte sem versão (15.4 nº 3) | O módulo expõe a versão do contrato; a ponte confere ao carregar; a falha chega à tela com a causa e o que fazer |

### 5.2 As cinco famílias

| Família | Regra do ARCcC que ela quebra | Defeitos | Trava automática hoje | Trava proposta |
|---|---|---|---|---|
| **A. Promessa sem entrega** | 4.4.4, 4.4.9, 4.4.11 | D8, D9, D14, 11 protocolos (R1); o `gapClosingPx` do balde (corrigido em `bd07511`) | Nenhuma | Todo protocolo, enum ou parâmetro exposto tem consumidor: começa pelos 11 protocolos (0 consumidores hoje) |
| **B. Falha que não chega a quem chamou** | Contrato (4.2 do `AGENTS.md`: sem `except` silencioso) | D2, D13 (mensagem culpa o arquivo), D17 | `silent_except` (só vê `pass`) | Catraca de contagem para `except` que só registra e segue (41 hoje) |
| **C. Valor solto no lugar de tipo** | Lei do Rio 4 | D1 | Só para modos de mesclagem, guias e simetria | Enum `EngineType` (S0.1): hoje 1 literal em código (`input_router.py`) e 9 categorias de preset com `"engine_type": N  # EngineType.X`, o comentário fazendo o papel do tipo |
| **D. Medição ausente ou enganosa** | 4.4.8, porta 6 | D16, R11, benchmark não versionado | 1 teste de vazão do pincel gigante | Benchmark versionado (S0.8) e golden dos 9 motores (S0.6) |
| **E. Duas cópias, dois escritores** | Lei do Rio 2, 4.2 caminho 4 | D5, D6, D7, D11 | Catraca de acoplamento (parcial) | Já cobertas pelas catracas existentes |

**Por que o trabalho parecia infinito:** B, A e C são famílias *sem trava*.
Cada análise acha instâncias novas e cada correção fecha uma instância, não a
família. D e E ou já têm trava ou ganham com S0.6/S0.8. Fechar a família
significa trava + zerar o estoque conhecido, e depois o número só pode descer.

---

## 6. Como trabalhar

### 6.1 O laço (a 4.4 aplicada a este repositório)

Cada tarefa, correção ou feature, é **uma fatia**. As 5 etapas de verificação
do `AGENTS.md` continuam como piso (etapas 7 a 10 abaixo); o que falta é a
parte que vem antes.

| # | Passo da 4.4 | No Lumenia |
|---|---|---|
| 1 | Entender | README da pasta e da pasta mãe; responder por escrito "qual é a responsabilidade real que nasceu aqui?" (4.4.3) |
| 2 | Delimitar | Dizer o que **não** pertence ao componente (uma linha na mensagem de commit) |
| 3 | Modelar | O tipo antes do código: enum, `dataclass`, `Protocol`, entrada no `.pyi` |
| 4 | Contrato | **O teste que falha primeiro**, escrito contra o contrato (por exemplo, o enum bate com o valor nativo) |
| 5 | Implementar o mínimo | Só a responsabilidade presente (4.4.4): nada de gerente, registro ou protocolo "para depois" |
| 6 | Teste isolado | Unidade; para o motor, `tests/native/` quando a unidade não precisa da ponte |
| 7 | Fatia vertical real | Entrada na interface → ponte → motor real, com o módulo nativo compilado (`tests/test_lowlevel_*`, caracterização) |
| 8 | Evidência | Número medido no comando rodado; golden regravado **com a mudança explicada**; benchmark antes e depois quando houver desempenho |
| 9 | Volta à fundação | Responder as 6 perguntas da 4.4.7 no changelog. Resposta "sim" vira linha em `01-pendencias-atuais.md`, não trabalho imediato |
| 10 | Registrar | README e `arccc:deps` no mesmo commit, changelog, pendências; suíte completa e `check_windows_build.py` quando tocar motor ou ponte |

As 6 perguntas da 4.4.7, para copiar no changelog:
1. A responsabilidade ficou no lugar certo?
2. Algum contrato ficou grande demais?
3. Algum componente passou a conhecer o que não devia?
4. Algum dado é convertido mais de uma vez?
5. Nasceu uma responsabilidade nova?
6. Alguma abstração criada antes deixou de fazer sentido?

### 6.2 Exemplo aplicado: S0.1 (ponta borracha liga o Borrar)

| Passo | S0.1 |
|---|---|
| Responsabilidade | Dizer, em Python, qual motor o C++ vai usar: uma lista fechada de motores com o mesmo valor do enum nativo |
| Não pertence | Escolher motor por regra de preset ou de ferramenta (isso é de quem chama) |
| Modelo | `EngineType` (`IntEnum`) em `ui/core`, como `LayerBlendMode` |
| Contrato (teste primeiro) | Os valores do enum Python são iguais ao `aladyn_engine_native.EngineType`. O teste da ponta borracha espera `EngineType.ERASER`, não o número |
| Mínimo | Enum; o roteador e as 9 categorias de preset usam o enum |
| Fatia vertical | Caneta com a ponta borracha: o motor ativo durante o traço é a Borracha; ao soltar, volta ao anterior |
| Evidência | O teste antigo (que cravou 6) falha antes da correção e o novo passa depois |
| Volta à fundação | Há outro número solto de motor? (Hoje: 1 literal + 9 categorias de preset.) Catraca para ficar em 0 |
| Registrar | `ui/core/README.md`, changelog |

### 6.3 Quatro regras de parada

1. **Estrutura só nasce de responsabilidade presente (4.4.4).** Nenhum registro,
   protocolo ou gerente por antecipação. Quem quiser criar um responde "que
   responsabilidade concreta não cabe no componente atual?" no commit.
2. **Achado novo só entra na linha de chegada se o usuário o sente hoje**
   (comportamento errado, perda de dado, travamento). Senão, vira trava de
   contagem ou ponto de extensão registrado (6.4).
3. **"Pronto" é do componente tocado, não do sistema.** A 4.4.11 é conferida
   para o que a fatia mexeu. O resto continua com o selo que tem.
4. **Dívida medida só desce (catraca).** O estoque não precisa ser limpo em
   rodada especial: cai quando alguém mexe no arquivo, e não sobe.

Soma-se a regra do relatório anterior: sem benchmark versionado, nenhuma
"otimização" (4.4.8).

### 6.4 Pontos de extensão: registrados, não implementados (4.4.9)

A 4.4.9 pede registrar o ponto natural de extensão **sem** implementar o
mecanismo. Cada linha diz o que o código atual **não pode** fazer para não
fechar a porta, e o gatilho que autoriza implementar. Isso é finito e
substitui "S2/S3 como obra de base".

| Ponto de extensão | Hoje | O que não pode acontecer | Gatilho para implementar |
|---|---|---|---|
| Formato de pixel (16 bits, HDR) | RGBA8 em `utils/ColorRGBA`; 49 linhas do motor fora de `PixelBuffer` e `ColorRGBA` fazem aritmética de 4 bytes por pixel (`AreaFilters` 18, `MipmapPyramid` 6, `PointFilters` 4...) | Esse número subir | Decisão do dono (S3.1) |
| Exibição por região ou GPU | **S1.1 feita.** A tela pede só a região; sobram 4 cópias do canvas inteiro na `ui/` (`get_qimage`: copiar, gravação, prévia do traço, exportar), todas de caminhos que precisam dele | Uma 5ª | A GPU: quando a tela deixar de copiar para a CPU |
| Nova propriedade de camada (máscara) | **S2.2 feita.** As propriedades de camada são `layer_properties.TABLE`; uma nova entra ali e no que a mostra | Uma propriedade escrita à mão num dos 8 lugares que a tabela já percorre | A feature "máscara de camada" |
| Registro de ferramentas, filtros e formatos | Dicionário e `enum` | Criar o registro vazio | O 2º formato de arquivo real (PSD) ou a 1ª ferramenta feita por terceiros |
| Biblioteca de pincéis em arquivo | Presets em código | Nova propriedade de pincel fora de `BrushState`/`BrushProfile` (como as curvas, D5) | A feature de importar e salvar pincel |
| Plugins de terceiros | **R9 feita.** `PluginContext` com 3 nomes, sem o motor e sem logger (`tests/test_plugin_context_contract.py`) | Dar ao plugin acesso ao motor inteiro: ele recebe um serviço pelo contrato que usa | O 1º plugin externo (aí decidir o isolamento) |
| Operações longas fora da thread da interface | **S1.2 feita** para salvar e abrir (a composição da abertura de um documento denso, 0,2 a 0,7 s, ainda roda na thread da interface). GIL solto em 3 lugares, com política escrita e travada | Nova operação longa na thread da interface; soltar o GIL numa chamada da fachada | Documento montado fora da thread da interface |
| Núcleo comum de rasterização | **S2.1 feita.** `DabFootprint`, `PixelPermission`, `TipShape` e `StraightOver`; cada `renderDab` com 19–57 linhas e complexidade 6–15 | Um 10º motor com laço de tiles e bloco de seleção/recorte próprios | O próximo motor, que já nasce com o núcleo |

### 6.5 Mudança proposta no `AGENTS.md` (não aplicada)

Acrescentar, na Seção 5, antes do passo 1, um bloco curto:

```text
CICLO DE CONSTRUÇÃO (ARCcC 4.4): toda tarefa é uma fatia.
1) Escreva a responsabilidade em uma frase e o que NÃO pertence a ela.
2) Escreva o tipo e o teste do contrato ANTES do código.
3) Implemente só a responsabilidade presente (sem registro, protocolo ou
   gerente para possibilidade que não existe).
4) Valide a fatia inteira (interface -> ponte -> motor real) e registre o número.
5) Responda as 6 perguntas da volta à fundação no changelog.
Dívida medida só desce (catraca). Achado novo só entra na linha de chegada
se o usuário o sente hoje.
```

---

## 7. Plano revisado

A linha de chegada de `01-pendencias-atuais.md` fica com duas mudanças. O
resto permanece como o dono decidiu.

| Item | Mudança | Por quê |
|---|---|---|
| S0.2 | **Inclui D17**: falha ao carregar o motor chega à tela com a causa, e o módulo expõe a versão do contrato que a ponte confere | Mesmo padrão do D2 (falha que não chega a quem chamou); é pequeno |
| **S0.8 (novo)** | **Benchmark versionado:** trazer para `benchmarks/` as 4 medições que hoje só existem no rascunho da sessão (custo por amostra pela interface, repintura, abrir e salvar, abertura do app), com saída em JSON comparável e limite relativo | A 4.4.8 e a porta 6. S1.1 e S1.2 têm metas numéricas ("pronto quando"); sem isso elas não são verificáveis por quem vier depois |

Ordem recomendada dentro da linha de chegada:

1. **S0.6** (golden dos 9 motores): é a porta 5 do que vem a seguir.
2. **S0.8** (benchmark versionado): é a porta 6 de S1. Sem ele, S1 não fecha o ciclo da 4.4.8.
3. **S0.1 a S0.5 e S0.7**, cada uma como uma fatia do laço da 6.1 (S0.2 já com D17).
4. **S1.1 a S1.3**, cada uma abrindo e fechando com o benchmark de S0.8.

**Travas opcionais** (cada uma cabe numa sessão; só impedem subir e não
corrigem estoque, então não aumentam a linha de chegada; o dono escolhe):
- `except` que só registra e segue: 41 hoje (família B).
- Imports que passam por cima da porta de uma pasta: 325 hoje (Seção 3.1).
- Aritmética de 4 bytes por pixel fora de `PixelBuffer`/`ColorRGBA`: 49 linhas hoje.
- Chamadas de cópia do canvas inteiro: 6 hoje.

Fora da base, como antes: S1.4–S1.5, S2, S3 e o "Aladyn Engine 2.0". Agora com
a tabela da 6.4 dizendo o que cada um **não pode** piorar enquanto espera.

---

## 8. Decisões do dono

1. **Mensagens de commit em inglês?** A 14.1 lista "commits" entre os nomes que
   ficam em inglês; o histórico tem 178 de 296 em português. *Recomendo:
   assunto em inglês a partir de agora e o corpo livre; o histórico não se
   reescreve.* Até a resposta, sigo em português.
2. **Limiar de complexidade.** O documento pede 10 (149 funções acima, contando
   booleanos); o projeto usa 20 (46 acima pelo `lizard`, 6 `noqa` pelo `ruff`).
   *Recomendo manter 20 como barreira e usar 10 só como alerta em relatório,
   sem barrar:* o custo de baixar para 10 está nos motores de pincel (R2), que
   S2.1 resolve de uma vez, quando o próximo motor pedir.
3. **Texto novo do `AGENTS.md`** (6.5). *Recomendo aprovar:* é o que falta para
   o ciclo existir fora desta conversa.
4. **Onde guardar o ARCcC v1.1.0.** O documento do repositório
   (`02-arquitetura/01-framework-arccc.md`) é uma versão curta e desatualizada
   (D10). *Recomendo:* guardar o v1.1.0 como o documento do método e escrever
   nele (ou ao lado) uma seção "como o ARCcC se aplica ao Lumenia" com as
   zonas de 300/450, `ui/plugins/`, mixins só no backend e as exceções
   declaradas. Isso fecha o S0.5 com a fonte certa.

---

## 9. Estado dos selos em 2026-10-01 (medido depois de `4e5ee70`)

O dono pediu os selos deste relatório fechados. Esta seção diz o que fechou,
com o commit e o número, e **o que não fechou e por quê**. Só marquei 🟢 onde há
teste ou medição que o sustente; o que ficou aberto está dito sem adjetivo.

### 9.1 O que fechou

| Selo | De → para | Evidência (commit, número) |
|---|---|---|
| Exibição | 🔴 → 🟢 | Repintura a 100% em 4K: 34 ms → 0,5 ms; zoom afastado depois de uma mudança 0,28 ms (era 5,1); com perfil de cor ≠ sRGB 392 ms → 0,59 ms. Oráculo independente em numpy depois de cada operação e em 40 sequências; `a5d7fc5`, `1abc684`, `e16a315` |
| Telemetria da tela | 🟠 → 🟢 | O medidor 6 conta a cópia do canvas e o `drawImage`; `tests/test_viewport_paint_telemetry.py`; as telas passam pelo `TelemetryTracker`. `0487eff`, `4e5ee70` |
| Compositor e mesclagem | 🟡 → 🟢 | `blendPixel` 32 → 13, `LayerMerger` 32 e 19 → 12, `Compositor.cpp` 215 → 130 linhas; 60 milhões de casos iguais à versão anterior, 52 hashes, 4 resumos de mesclagem; desempenho dentro do ruído. `477ec19` |
| Motores de pincel | 🟠 → 🟢 | 108 pinos (era 36); `renderDab` 129–273 linhas e complexidade 25–71 → 19–57 e 6–15; 2 pinos regravados de propósito (≤ 2 níveis em 0,3% dos bytes). `4101a56`, `230f77c` |
| Documento e camadas | 🟡 → 🟢 | 8 lugares que repetiam as propriedades → 1 tabela; o teste de contrato acrescenta uma propriedade e confere cada lugar. `f9e8ad1` |
| Ponte | 🟡 → 🟢 | Versão 6 presa por hash; política do GIL escrita e travada; 4 harnesses nativos isolados. `28bb597` |
| Plugins | 🟠 → 🟢 | Contexto com 3 nomes, sem motor; os 4 tipos sem extensão saíram. `22ea776` |
| 4.4 fluxo de construção | 🔴 → 🟢 | `AGENTS.md` 5.0; 29 commits seguidos com as 6 perguntas e a medição |
| 14 idioma | 🟡 → 🟢 | Assunto de commit em inglês (29 seguidos); identificadores com catraca em 0 |
| 15.4 nº 3 contrato versionado | 🟠 → 🟢 | Ver Ponte |

Defeitos achados pelo caminho e corrigidos (cada um com teste): abrir um arquivo
salvo não reproduzia os pixels; o `.pyi` mentia sobre 11 assinaturas; abrir um
`.lmn` dava `TypeError` desde 2026-09-24; a lupa do conta-gotas copiava o canvas
a cada movimento do mouse (50 ms → 0,45 ms em 4K); com perfil de cor a leitura
do zoom afastado custava 392 ms; o cache de granulação do pincel padrão podia
ser montado por duas threads ao mesmo tempo.

### 9.2 O que não fechou

| Selo | Fica | Por quê, e o que fecha |
|---|---|---|
| Arquivo (salvar e abrir) | 🟡 (era 🔴) | Salvar não trava (captura de 0,8 a 2,4 ms). Abrir um documento 4K com 10 camadas todas pintadas ainda para a janela por 0,22 a 0,32 s (0,66 s numa rodada do benchmark) na composição única da adoção; esparso 75 ms. O "pronto quando" de S1.2 (abrir em menos de 1 s) está cumprido; "sem travar" para o documento denso não. Fecha: construir o documento fora da thread da interface e anexá-lo em tempo constante, ou compor sob demanda por região; é mudança de motor e de ponte (versão 7) |
| Seleção e transformação | 🟡 | D11 (prévia pelo Qt, resultado pelo motor) **não tratado**: pede um método novo de prévia na ponte e a decisão de custo por movimento do mouse; severidade baixa |
| `EngineBackend` | 🟡 (era 🟠) | Continua com 178 métodos e 10 dos 11 sub-protocolos sem consumidor; a injeção dos 49 pedidos globais do motor fica arquivo por arquivo (catraca: só descem). Quanto o contrato diminui, não medi: não diminuiu |
| 2.3 porta única | 🟡 (era 🟠) | Trava de catraca (238 importações que contornam a porta, congeladas), mas as 238 existem; reescrevê-las em massa arrisca ciclo de importação escondido |
| 4.2 caixa preta | 🟠 | Vale para o motor e a ponte, não para as pastas de `ui/` (49 pedidos globais e 238 contornos congelados) |
| 4.4.4 e 4.4.9 mecanismos vazios | 🟡 (era 🟠) | 10 sub-protocolos sem consumidor (ver `EngineBackend`) |
| 7.1 limiares | 🟡 | Por decisão do dono (barreira em 20, alerta em 10). Medido de novo: C++ acima de 10 de 64 para 57, acima de 15 de 38 para 26, acima de 20 de 25 para 15; Python acima de 15 de 37 para 36 e acima de 20 de 21 para 20 |
| 15 multi-pilar | 🟡 | A regra 5 (release independente): 4 harnesses nativos isolados, mas a maior parte dos testes do motor ainda passa pela ponte |

### 9.3 O que mudou nas medições da Seção 3

- 3.1: as 239 importações que contornam a porta são 238 (uma saiu com o
  `PluginContext`) e agora há catraca; as 86 que a porta não exporta continuam
  sem tratamento (alargar a porta é decisão por pasta).
- 3.2: `EngineBackend` 178 métodos (eram 176): entraram `get_display_image`
  (S1.1), `load_error` (D17) e `max_canvas_dimension` (D13) e saiu
  `get_qimage_lod`. Os métodos de gravação e abertura não entraram: ficaram no
  `PersistenceBackend`. Pedidos globais do motor fora do registro e da ponte:
  49 em 29 arquivos (eram 60 quando a catraca os contou pela primeira vez).
- 3.3: ver 7.1 acima.
- 3.6: regra 3 🟢; regra 5 🟡 com 4 harnesses.

---

## Apêndice A — como cada número foi medido

Todos no Linux do agente, em `92e4543`. Os scripts estão no rascunho da
sessão (fora do repositório).

| Número | Comando ou método |
|---|---|
| 60 pastas com `__init__`, 42 com conteúdo, 18 vazias | `ast` sobre `ui/**/__init__.py`: conteúdo = tem `import`, `__all__`, classe ou função |
| 281 / 325 / 239 / 86 imports | `ast` sobre `ui/**/*.py`: `from ui.x.y import ...` feito de fora de `ui.x`; "direto" = o módulo citado é arquivo e não pasta, e a pasta tem porta com conteúdo; "a porta servia" = todo nome importado está exportado em `ui.x.__init__` |
| 176 métodos, 11 protocolos sem consumidor, 22 sem chamada | `ast` sobre `ui/core/engine/backend*.py` (métodos públicos); regex `\.nome\b` em `ui/` (sem `bridge_client` nem os próprios `backend*.py`) e em `tests/`; protocolos: arquivos de fora de `ui/core/engine` que citam cada classe |
| ≈ 170 declarações da facade | Regex sobre `PaintEngineFacade.hpp` depois de `public:` (aproximado) |
| 325 classes, 83 com mais de 5 métodos públicos, 13 com mais de 20 | `ast` sobre `ui/**/*.py` |
| Complexidade | `python -m lizard <pasta> -l cpp\|python --csv` (1.24.0), colunas de CCN |
| 41 handlers que só registram | `ast`: `except` cujo corpo são só chamadas `.debug/.info/.warning/.error/.exception/.critical` |
| 1 literal + 9 categorias de preset | `grep -rn "set_engine_type("` e `grep -rn '"engine_type":' ui/plugins/panels/brush_plugin/presets` |
| 178 de 296 commits | `git log --format=%s`, assunto com acento ou palavra comum do português |
| 58 de 137 arquivos de teste com o motor | `grep -l "aladyn_engine_native\|EngineRegistry\|AladynBackend" tests/*.py` |
| 49 linhas com aritmética de 4 bytes | `grep -rnE "\* ?4\b\|\b4 ?\*\|<< ?2\b\|sizeof\(.*ColorRGBA\)" engine` sem `PixelBuffer` e `ColorRGBA.hpp` |
| 6 chamadas de cópia do canvas | `grep -rnE "\.get_qimage(_lod)?\(" ui` sem `bridge_client` |
| 34 arquivos com a trava de alfa | `grep -rlE "alpha_lock\|alphaLock\|alpha_locked\|alphaLocked" ui engine bridge` (`.py .cpp .hpp .pyi`) |

**Limites das medições:** os números de portas e de métodos sem chamada são
aproximações por análise estática (não veem chamada por nome em texto nem por
`getattr`). Servem para decidir ordem de grandeza e onde olhar, não para apagar
código sem conferir.
