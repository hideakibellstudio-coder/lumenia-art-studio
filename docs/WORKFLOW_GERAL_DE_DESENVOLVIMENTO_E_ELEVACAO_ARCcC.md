# 🏛️ WORKFLOW GERAL DE DESENVOLVIMENTO E ELEVAÇÃO ARCcC
## *Framework Operacional para Engenharia de Alta Performance, Refatoração Segura e Qualidade Competitiva de Software*

---

## 🧭 1. FILOSOFIA E PRINCÍPIOS FUNDAMENTAIS

Este documento formaliza o **método de trabalho sistemático** desenvolvido e validado ao longo da evolução da arquitetura do **Lumenia**. Ele foi desenhado para ser universalmente aplicável a qualquer subsistema do software — seja o **Motor C++ Nativo (Camada 1)**, o **Sistema de Ferramentas e Pincéis (Camada 2)**, o **Core do Workspace e Telas (Camada 3)**, ou o **Ecosistema de Plugins e UI (Camada 4)**.

### Os Três Pilares Inegociáveis:
1. **Engenharia Cirúrgica & Zero Regressão**: Nenhuma linha de código é alterada sem que haja clareza absoluta de seus impactos colaterais. Se um teste funcionava antes, ele continuará funcionando depois.
2. **Qualidade Concorrencial de Mercado**: Todo código, algoritmo e interface é projetado tendo como referência os padrões da indústria de ponta (Clip Studio Paint, Photoshop, Procreate, Krita).
3. **Conformidade Estrita com ARCcC**:
   - **Teto Absoluto de 500 Linhas de Código (LOC)** por arquivo (sem exceções).
   - **Arquitetura em Camadas Ortogonais**: Camadas superiores conhecem inferiores; camadas inferiores nunca dependem de superiores.
   - **Desacoplamento por Facades e Orquestradores**: Módulos complexos são divididos em componentes especializados, com interfaces públicas limpas e estritas.

---

## 🔄 2. O CICLO DE VIDA DO DESENVOLVIMENTO (MACRO-ETAPAS)

```mermaid
flowchart TD
    A["Etapa 1: Delimitação & Raio-X Arquitetural"] --> B["Etapa 2: Visão de Produto & Benchmark de Mercado"]
    B --> C["Etapa 3: Plano Mestre Estratégico em Fases"]
    C --> D["Etapa 4: Linha de Base & Blindagem de Testes"]
    D --> E["Etapa 5: Ciclo Iterativo de Execução por Fase"]
    E --> F["Etapa 6: Consolidação, Sincronização & Documentação"]
    
    subgraph E ["Etapa 5: Loop de Ferro da Fase"]
        E1["5.1 Micro-Design & Contratos"] --> E2["5.2 Implementação Cirúrgica"]
        E2 --> E3["5.3 Compilação / Build Nativo"]
        E3 --> E4["5.4 Testes Unitários de Baixo Nível"]
        E4 --> E5["5.5 Suíte Global de Regressão"]
        E5 --> E6{"Anomalia ou Regressão?"}
        E6 -- "Sim" --> E_Debug["Resolução por Causa-Raiz (3 Níveis)"]
        E_Debug --> E3
        E6 -- "Não" --> E7["5.6 Auditoria ARCcC (<500 LOC)"]
        E7 --> E8["5.7 Sync Multi-Workspace & Commit"]
    end
```

---

## 📋 3. GUIA PASSO A PASSO DETALHADO

### ETAPA 1: DELIMITAÇÃO & RAIO-X ARQUITETURAL (O CENSO)
Antes de escrever uma única linha de código, o sistema deve ser radiografado com precisão matemática.

- **Inventário de Arquivos e LOC**:
  - Listar todos os arquivos da área de foco com sua contagem de linhas atual.
  - Identificar arquivos "monolíticos" ou que excedem o teto de 500 LOC.
- **Mapeamento de Dependências**:
  - Mapear dependências externas, bibliotecas, headers órfãos ou código morto/não referenciado.
  - Mapear acoplamentos cruzados indesejados.
- **Contratos e Fronteiras**:
  - Quais APIs públicas esse subsistema expõe? Quem as consome?
- **Entregável Formal**: Criar o artefato/documento `docs/DIAGNOSTICO_ARCcC_[MODULO].md`.

---

### ETAPA 2: VISÃO DE PRODUTO & BENCHMARK COMPETITIVO
Um software de alto desempenho precisa atender às expectativas reais dos usuários profissionais.

- **Pergunta-Guia**: *"O que falta para este subsistema bater de frente com os líderes de mercado?"*
- **Análise de Fatores Sensoriais e de Desempenho**:
  - **Latência**: A resposta tátil/visual é imediata (< 16ms / 60-120 FPS)?
  - **Fidelidade e Artefatos**: Existem descontinuidades perceptivas, degraus de cor, bordas turvas ou falta de precisão sub-pixel?
  - **Escalabilidade**: O sistema aguenta trabalhar em condições extremas (ex: 4K, 600 DPI, pincéis de 1000px, 50 camadas, memória sob pressão)?
- **Lista de Diferenciais Competitivos**: Definir as 3 a 5 melhorias que transformarão o subsistema em referência técnica.

---

### ETAPA 3: O PLANO MESTRE ESTRATÉGICO EM FASES
Dividir a empreitada em fases incrementais, ortogonais e autolimitadas.

- **Estruturação Típica de 5 Fases**:
  - **Fase 1: Fundação & Higiene**: Limpeza de código morto, desacoplamento de arquivos gigantes (>500 LOC), contratos e interfaces formais.
  - **Fase 2: Capacidade Funcional & Fidelidade**: Novos algoritmos, dinâmica aprimorada, correção de lacunas conceituais.
  - **Fase 3: Performance & Throughput de Carga**: Vetorização (SIMD/AVX2), paralelismo (OpenMP), otimizações de cache e estruturas de dados.
  - **Fase 4: Escalabilidade & Gestão de Recursos**: Compressão em tempo real (ex: LZ4), Copy-on-Write ($O(1)$), paginação de memória/disco.
  - **Fase 5: Aceleração de Hardware & Apresentação**: Pipelines de Viewport (OpenGL/GPU), dirty tiles, culling e resposta de 120 FPS.
- **Critérios de Aceite Inegociáveis**: Toda fase deve definir exatamente:
  1. Entregáveis técnicos esperados.
  2. Teste automatizado de validação.
  3. Garantia de limite de LOC por arquivo.
- **Entregável Formal**: Criar o documento `docs/PLANO_MESTRE_[OBJETIVO].md`.

---

### ETAPA 4: LINHA DE BASE & BLINDAGEM DE TESTES
- **Execução da Suíte Existente**: Rodar a suíte global de testes (`discover tests`). Todos os testes devem passar (100%).
- **Commit de Ponto de Partida**:
  - `git commit -m "chore: baseline antes do plano mestre [modulo]"`
  - Isso garante um ponto seguro de restauração (rollback) se necessário.

---

### ETAPA 5: O LOOP DE FERRO DA EXECUÇÃO (POR FASE)
Para cada fase do plano, execute a sequência rigorosa a seguir:

#### 5.1. Micro-Design e Decomposição Preventiva
- Projete as novas classes/módulos mantendo a responsabilidade única.
- Se uma classe existente tiver 400+ linhas e for receber código novo, **decomponha-a primeiro** criando um orquestrador ou módulo auxiliar para nunca ultrapassar 500 linhas.

#### 5.2. Implementação Cirúrgica
- Escreva código moderno (C++17/20, Python 3.12+ tipado).
- Minimize alocações dinâmicas no caminho crítico de execução.
- Respeite as fronteiras de isolamento (APIs públicas estáveis).

#### 5.3. Build & Compilação Limpa
- Recompile módulos nativos/extensões (`setup.py build_ext --inplace` ou CMake).
- Exija **zero erros** e **zero warnings críticos**.

#### 5.4. Criação de Testes de Baixo Nível da Fase
- Crie um arquivo dedicado `tests/test_lowlevel_phaseX_[nome].py`.
- Cubra:
  - Testes de estresse e casos de borda (resoluções extremas, buffers vazios/cheios, concorrência).
  - Fidelidade matemática (tolerâncias analíticas `assertAlmostEqual`).
  - Performance e invariantes de estado.

#### 5.5. Bateria Global de Regressão
- Execute toda a suíte de testes do repositório:
  ```bash
  python -m unittest discover tests
  ```
- **Aprovação de 100% Obrigatória**: Nenhuma falha é aceitável para avançar.

#### 5.6. Protocolo de Resolução de Anomalias (O Método dos 3 Níveis)
Caso surja uma falha visual, artefato perceptivo ou comportamento inesperado durante a fase:
1. **Nível Físico/Matemático**: Analise os valores numéricos reais dos pixels ou dados. Verifique curvas de transferência (ex: sRGB gamma, clampings, divisões inteiras truncadas).
2. **Nível Algorítmico**: Verifique partições de loop, condições de contorno de matrizes/tiles, fast-paths com suposições incorretas.
3. **Nível Estrutural**: Verifique ordens de interpolação, acúmulo de erros de ponto flutuante ou desalinhamento de memória.
- Isole o problema com um teste reprodutível e corrija-o na causa-raiz, nunca com "gambiarras" superficiais.

#### 5.7. Auditoria Estrita ARCcC
- Execute verificação de linhas de código em todos os arquivos modificados/criados:
  - Nenhum arquivo pode ter $\ge 500\text{ LOC}$.

#### 5.8. Sincronização Multi-Workspace
- Se o projeto mantiver ambientes espelho (ex: Workspace Principal + Workspace de Produção/Testes):
  - Copie fielmente arquivos fontes, headers, binários compilados (`.pyd`) e testes.

#### 5.9. Git Commit Granular
- Realize o commit da fase com mensagem semântica detalhada:
  ```bash
  git commit -m "feat([modulo]): Fase X - [Titulo Descritivo] (detalhes tecnicos)"
  ```
- Garanta que a árvore de trabalho de ambos os repositórios fique limpa (`working tree clean`).

---

### ETAPA 6: CONSOLIDAÇÃO E GESTÃO DE CONHECIMENTO
- **Atualização do Walkthrough**: Registrar formalmente o progresso concluído, tabelas de métricas comparativas e decisões de design.
- **Revisão de Desempenho**: Comparar o antes e depois em velocidade, uso de memória e sensação de uso.
- **Pronto para a Próxima Fronteira**: O subsistema agora está estabilizado, testado e documentado no padrão do estado da arte.

---

## 🧠 4. A REGRA DA COESÃO DE DOMÍNIO: POR QUE < 500 LOC NÃO É SUFICIENTE

O teto de **$< 500\text{ LOC}$ (Regra 4)** é uma barreira mecânica fundamental contra classes monolíticas de milhares de linhas. No entanto, ela é uma métrica **quantitativa**, e não **qualitativa**. 

Um arquivo pode ter 250 ou 450 linhas e ainda assim ser uma **"God Class compactada"** ou um **"Canivete Suíço em miniatura"**, onde 4 ou 5 domínios técnicos completamente distintos dividem o mesmo espaço de memória, as mesmas variáveis de instância e o mesmo ciclo de vida. 

> [!CAUTION]
> **A Causa Oculta das Regressões**: A maioria dos bugs inseridos durante refatorações não nasce da quantidade de linhas, mas sim do **acúmulo de responsabilidades concorrentes** em um mesmo arquivo. Ao ajustar a lógica de um domínio $A$, quebram-se silenciosamente os invariantes ou o estado compartilhado do domínio $B$.

---

### Os 4 Sintomas do Acúmulo de Papéis Distintos:

1. **Acoplamento de Invariantes Incompatíveis**:
   - *Caso Real Lumenia*: Em `BlendEquations.hpp`, a mesma equação era usada para compor camadas independentes (que exige espaço linear sRGB) e acumular carimbos de um único traço de pincel (onde a curva sRGB de 8 bits gerava um degrau artificial de $R=13 \rightarrow 0$ no miolo).
2. **Estado Compartilhado e Efeitos Colaterais Temporais**:
   - Flags e variáveis mutáveis (`m_isDrawing`, `_cursor_in_viewport`, `m_lastDab`) manipuladas por múltiplos fluxos. A mutação de estado por uma ferramenta contamina a execução da próxima.
3. **Raio de Destruição Expandido (*Blast Radius*)**:
   - Quando um arquivo concentra múltiplos papéis (ex: `PaintEngineFacade` gerenciando 9 domínios ou `render_widget.py` orquestrando 7 ferramentas e o contexto OpenGL), qualquer alteração pontual força recompilações massivas e expõe o sistema a regressões em áreas não relacionadas.
4. **Névoa Cognitiva (*Context Overload*)**:
   - O desenvolvedor ou agente de IA precisa manter múltiplos modelos mentais concorrentes para editar um único arquivo, aumentando exponencialmente a chance de suposições errôneas.

---

### As 3 Regras Qualitativas ARCcC (Nível 2 de Maturidade):

#### 🎯 Regra Q1: O Teste do "E" (*Single Responsibility Audit*)
Se para explicar a função de uma classe ou arquivo você precisar utilizar a conjunção **"E"**, a classe viola o princípio de responsabilidade única e **deve ser decomposta**, mesmo que tenha menos de 200 linhas:
- ❌ *Incorreto*: "O `TileGrid` armazena a matriz de tiles **E** rastreia regiões sujas para a GPU **E** faz coleta de lixo de blocos vazios."
- ✅ *Correto*:
  - `TileStorage`: Apenas aloca e indexa os ponteiros de memória $(x, y)$.
  - `TileDirtyTracker`: Apenas registra o conjunto de coordenadas modificadas.
  - `TileMemoryPruner`: Apenas varre e recicla blocos transparentes.

#### 📦 Regra Q2: Separação Estrita de Estado e Algoritmo (*Data vs. Logic*)
Estruturas de dados básicas (matrizes de bytes, buffers, descritores de geometria) **não devem conter lógica de apresentação, orquestração de GPU ou persistência em disco**. Lógicas avançadas devem atuar sobre as estruturas como serviços desacoplados ou observadores.

#### ⏱️ Regra Q3: Isolamento por Causa e Frequência de Mudança (*Change Reason Isolation*)
Componentes que mudam por motivos e frequências distintas nunca devem residir no mesmo módulo:
- Cálculos matemáticos puros e determinísticos (ex: projeção de matrizes de perspectiva 3D ou interpolação de curvas Bézier) **quase nunca mudam**.
- Estilos visuais, espessuras, cores de linhas de interface e comportamento de menus **mudam frequentemente** com base no feedback de design.
- *Eles devem viver em arquivos estritamente separados*.

---

## 📐 5. TABELA DE REGRAS E LIMITES ARCcC (QUANTITATIVAS & QUALITATIVAS)

| Elemento | Limite / Regra | Tipo | Ação em Caso de Violação |
|---|:---:|:---:|---|
| **Tamanho Máximo de Arquivo** | **< 500 Linhas** (C++ e Python) | Quantitativo | Decompor imediatamente em sub-módulos ou orquestradores. |
| **Pureza de Responsabilidade** | **1 Único Domínio** (Teste do "E") | Qualitativo | Extrair os papéis secundários para classes/módulos especializados. |
| **Separação Dados / Apresentação** | **Zero lógica de UI em Core** | Arquitetural | Isolar modelos de dados de rotinas de pintura e shaders. |
| **Taxa de Aprovação de Testes** | **100%** (Zero regressões) | Rigor | Bloquear o avanço até a regressão ser solucionada na causa-raiz. |
| **Arquivos Órfãos / Código Morto** | **0** | Higiene | Deletar headers não utilizados e unificar interfaces redundantes. |
| **Alocações no Loop Crítico** | **Zero Alocação Dinâmica** | Performance | Utilizar memória pré-alocada, stack, LUTs ou pools de buffers. |
| **Compatibilidade de Fallback** | **100% Graceful Degradation** | Robustez | Chavear para caminho escalar/CPU seguro se hardware não suportar. |
| **Commits Git** | **Granulares por Fase / Feature** | Governança | Nunca misturar mudanças de contextos distintos no mesmo commit. |

---

## 🛠️ 6. TEMPLATES REUTILIZÁVEIS

### Template para Nomenclatura de Arquivos de Teste de Fase
```text
tests/test_lowlevel_phase[N]_[tema_da_fase].py
```

### Template para Mensagem de Commit de Fase
```text
feat([subsistema]): Fase [N] - [Nome da Fase] ([Principais Técnicas Empregadas])

- [Item 1 implementado]
- [Item 2 implementado]
- Suíte de testes: X/X aprovados. Regressão global: 100% aprovada.
- Conformidade ARCcC: Todos os arquivos < 500 LOC.
```

### Template de Checklist de Definição de Pronto (Definition of Done)
- [ ] Especificação técnica e matemática validada contra líderes de mercado.
- [ ] Nenhum arquivo no subsistema ultrapassa 500 linhas.
- [ ] Código compilado limpo sem erros ou advertências graves.
- [ ] Testes de estresse e borda criados e 100% aprovados.
- [ ] Suíte global de regressão 100% verde.
- [ ] Código sincronizado em todos os workspaces do projeto.
- [ ] Commit atômico registrado no controle de versão.
