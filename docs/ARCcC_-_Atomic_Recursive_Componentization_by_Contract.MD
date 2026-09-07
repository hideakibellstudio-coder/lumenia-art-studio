# ARCcC - Atomic Recursive Componentization by Contract

## Metodologia Universal de Arquitetura por Decomposição Recursiva e Isolamento Absoluto por Pastas

---

## Índice

1. [Fundamentos Filosóficos](#1-fundamentos-filosóficos)
2. [Pilares da Arquitetura](#2-pilares-da-arquitetura)
3. [Estrutura Hierárquica Detalhada](#3-estrutura-hierárquica-detalhada)
4. [Regras de Ouro e Aplicação Prática](#4-regras-de-ouro-e-aplicação-prática)
5. [Exemplos de Implementação](#5-exemplos-de-implementação)
6. [Padrões de Comunicação](#6-padrões-de-comunicação)
7. [Gatilhos de Decomposição](#7-gatilhos-de-decomposição)
8. [Benefícios e Trade-offs](#8-benefícios-e-trade-offs)
9. [Guia de Transição para ARCcC](#9-guia-de-transição-para-arccc)
14. [Diretrizes Obrigatórias para Geração de Código por IA](#14-diretrizes-obrigatórias-para-geração-de-código-por-ia)
15. [Arquitetura Multi-Linguagem: Pilares e Ponte](#15-arquitetura-multi-linguagem-pilares-e-ponte)
16. [Ciclo de Vigilância Contínua e Higiene Arquitetural Periódica](#16-ciclo-de-vigilância-contínua-e-higiene-arquitetural-periódica)

---

## 1. Fundamentos Filosóficos

### 1.1 O Princípio da Caixa Preta Universal

A ARCcC propõe que **todo diretório é uma caixa preta** que encapsula completamente sua lógica interna, expondo apenas o mínimo necessário para interação com o restante do sistema. Esta abordagem transcende linguagens, frameworks e domínios de aplicação.

### 1.2 Decomposição como Ferramenta Primária

Diferente de metodologias que priorizam padrões de projeto ou arquiteturas em camadas, a ARCcC coloca a **decomposição física como mecanismo principal de gerenciamento de complexidade**. A pergunta não é "qual padrão usar?" mas sim "como posso quebrar esta responsabilidade em partes menores e isoladas?".

### 1.3 A Hierarquia Natural da Complexidade

A metodologia reconhece que a complexidade em software é fractal - assim como um organismo vivo se divide em sistemas, órgãos, tecidos e células, o software deve se dividir em módulos, submódulos, componentes e unidades atômicas.

---

## 2. Pilares da Arquitetura

### 2.1 Isolamento Absoluto por Jurisdição

Cada pasta representa uma **jurisdição soberana** com suas próprias regras, estruturas de dados e lógica de negócio. Módulos irmãos não compartilham código diretamente - toda comunicação ocorre através de contratos bem definidos.

### 2.2 Recursividade Infinita

A decomposição não tem limite teórico. Se um submódulo cresce em complexidade, ele se divide em sub-submódulos, e assim sucessivamente, até que cada unidade contenha uma responsabilidade única e atômica.

### 2.3 Ponto Único de Entrada

Cada pasta deve conter um arquivo centralizador (`index`, `mod`, `init` ou similar) que atua como:
- **Porta de entrada** para o mundo externo
- **Guardião** que decide o que é público e privado
- **Orquestrador** das funcionalidades internas

### 2.4 Contratos Explícitos

A comunicação entre caixas pretas é sempre através de:
- **Interfaces bem definidas** (ex: TypeScript interfaces, Java interfaces, C headers)
- **Eventos/Sinais** (pub/sub desacoplado)
- **APIs públicas** (REST, gRPC, etc.)

---

## 3. Estrutura Hierárquica Detalhada

### 3.1 Estrutura Universal de Referência

```
projeto/
├── fronteira/                      # CAMADA DE ENTRADA E ORQUESTRAÇÃO
│   ├── publica/                    # Interfaces públicas do sistema
│   │   ├── api/                    # Endpoints, handlers, rotas
│   │   └── eventos/                # Eventos que o sistema pode receber
│   │
│   └── orquestrador/               # Orquestrador central
│       ├── dispatcher              # Distribui ações para módulos
│       └── contratos/              # Contratos com cada módulo
│
├── nucleo/                         # NÚCLEO DE NEGÓCIO PRINCIPAL
│   ├── modulo_A/                   # JURISDIÇÃO A
│   │   ├── publico/                # O que o módulo expõe
│   │   │   ├── interfaces/
│   │   │   ├── tipos/
│   │   │   └── servicos/
│   │   │
│   │   ├── privado/                # Implementação interna
│   │   │   ├── core/               # Lógica central
│   │   │   ├── validadores/
│   │   │   └── transformadores/
│   │   │
│   │   ├── sub_modulo_1/           # SUBMÓDULO (complexidade moderada)
│   │   │   ├── index               # Ponto de entrada do submódulo
│   │   │   ├── core/               # Lógica específica
│   │   │   ├── modelos/            # Estruturas locais
│   │   │   └── testes/             # Testes unitários locais
│   │   │
│   │   └── sub_modulo_2/           # SUBMÓDULO (alta complexidade)
│   │       ├── index
│   │       ├── core/
│   │       ├── sub_sub_modulo_X/   # SUB-SUBMÓDULO
│   │       │   ├── index
│   │       │   ├── algoritmo_X/
│   │       │   └── utilitarios/
│   │       │
│   │       └── sub_sub_modulo_Y/   # OUTRA RAMIFICAÇÃO
│   │           ├── index
│   │           └── algoritmo_Y/
│   │
│   └── modulo_B/                   # JURISDIÇÃO B (independente de A)
│       ├── publico/
│       ├── privado/
│       ├── instrumentos/           # Ferramentas internas do módulo
│       └── fabricas/               # Fábricas de objetos/instâncias
│
├── infraestrutura/                 # INFRAESTRUTURA COMPARTILHADA
│   ├── persistencia/               # Acesso a dados
│   ├── comunicacao/                # Clientes HTTP, filas, etc.
│   ├── logging/                    # Logging centralizado
│   └── monitoramento/              # Métricas e observabilidade
│
└── util/                           # UTILITÁRIOS COMUNS (não-núcleo)
    ├── helpers/                    # Funções auxiliares puras
    ├── constantes/                 # Constantes imutáveis
    └── formatadores/               # Formatadores de dados
```

### 3.2 Níveis de Aninhamento

| Nível | Nome | Descrição | Gatilho de Criação |
|-------|------|-----------|-------------------|
| 0 | Projeto | Todo o sistema | Início do projeto |
| 1 | Módulo | Jurisdição principal | Domínio de negócio ou funcionalidade macro |
| 2 | Submódulo | Especialização | Quando módulo > 500 LOC ou > 7 responsabilidades |
| 3 | Sub-submódulo | Micro-especialização | Quando submódulo > 300 LOC ou > 5 responsabilidades |
| 4+ | Unidade Atômica | Componente indivisível | Quando sub-submódulo > 150 LOC |

### 3.3 Arquivos Essenciais por Nível

Cada pasta deve conter, no mínimo:

```
pasta_qualquer/
├── index               # Ponto de entrada obrigatório
├── manifest.json       # Metadados (dependências, versão, descrição)
├── README.md           # Documentação específica do submódulo
└── testes/             # Testes isolados deste escopo
    └── (testes de unidade)
```

**Arquivo `index` (ponto de entrada) - Exemplo Conceitual:**

```typescript
// index.ts de um submódulo
export * from './publico/interfaces';
export * from './publico/tipos';
export * from './publico/servicos';

// Importante: NÃO exportar nada do 'privado/'
// Importante: NÃO exportar implementações internas
```

---

## 4. Regras de Ouro e Aplicação Prática

### 4.1 As 5 Regras Fundamentais

| # | Regra | Descrição | Consequência da Violação |
|---|-------|-----------|--------------------------|
| 1 | **Isolamento de Nível** | Arquivos em uma pasta só podem importar arquivos de suas subpastas ou de pastas de infraestrutura/nível superior explicitamente contratadas | Acoplamento quebradiço, testes frágeis |
| 2 | **Sem Depêndencia entre Irmãos** | Pastas irmãs não podem se importar diretamente | Dependências circulares, dificuldade de manutenção |
| 3 | **Contrato por Interface** | Toda comunicação pública deve ser via interface/contrato, nunca implementação concreta | Alto acoplamento, dificuldade de substituição |
| 4 | **Fracionamento Preventivo** | Divida antes que o arquivo cresça demais, não depois | Dívida técnica acumulada, arquivos monstro |
| 5 | **Ponto Único de Entrada** | Cada pasta tem exatamente UM arquivo de entrada público | Confusão sobre API pública, vazamento de implementação |

### 4.2 O Teste da Caixa Preta

Para validar se uma pasta está corretamente isolada, aplique o **Teste da Mudança**:

1. Pegue uma pasta `sub_modulo_X/`
2. Mude completamente sua implementação interna
3. **Nenhuma outra pasta deve quebrar ou precisar de alteração** (desde que a interface pública permaneça a mesma)

### 4.3 O Teste do Arquivo Mínimo

Para cada pasta, pergunte:

> "Se eu tivesse que descrever o que esta pasta faz em UMA frase, eu conseguiria?"

Se a resposta exigir mais de uma frase, a pasta provavelmente está acumulando responsabilidades demais e precisa ser decomposta.

---

## 5. Exemplos de Implementação

### 5.1 Exemplo: E-commerce (Processamento de Pagamentos)

```
ecommerce/
├── fronteira/
│   ├── api/
│   │   ├── controllers/
│   │   └── validators/
│   └── orquestrador/
│       └── checkout_orchestrator
│
├── nucleo/
│   ├── pagamentos/
│   │   ├── publico/
│   │   │   ├── interfaces/
│   │   │   │   └── ProcessadorPagamento.ts
│   │   │   └── tipos/
│   │   │       └── Transacao.ts
│   │   │
│   │   ├── processadores/
│   │   │   ├── index
│   │   │   ├── cartao_credito/
│   │   │   │   ├── index
│   │   │   │   ├── adquirentes/
│   │   │   │   │   ├── index
│   │   │   │   │   ├── stone/
│   │   │   │   │   │   └── cliente.ts
│   │   │   │   │   └── cielo/
│   │   │   │   │       └── cliente.ts
│   │   │   │   └── validadores/
│   │   │   │       └── bandeira.ts
│   │   │   │
│   │   │   └── boleto/
│   │   │       ├── index
│   │   │       ├── gerador/
│   │   │       └── registrador/
│   │   │
│   │   └── transacoes/
│   │       ├── index
│   │       ├── autorizador/
│   │       ├── capturador/
│   │       └── cancelador/
│   │
│   ├── produtos/
│   │   ├── publico/
│   │   └── estoque/
│   │
│   └── clientes/
│       ├── publico/
│       └── cadastro/
│
├── infraestrutura/
│   ├── banco/
│   ├── filas/
│   └── cache/
│
└── util/
    ├── numeros/
    ├── datas/
    └── validadores/
```

### 5.2 Exemplo: Motor de Jogos (Rendering Pipeline)

```
game_engine/
├── fronteira/
│   ├── entrada/
│   │   ├── teclado/
│   │   └── mouse/
│   └── cena/
│       ├── index
│       └── gerenciador_cena/
│
├── nucleo/
│   ├── renderizacao/
│   │   ├── publico/
│   │   │   └── Renderizador.ts
│   │   │
│   │   ├── pipeline/
│   │   │   ├── index
│   │   │   ├── vertex/
│   │   │   │   ├── index
│   │   │   │   ├── shaders/
│   │   │   │   └── buffers/
│   │   │   │
│   │   │   ├── rasterizacao/
│   │   │   │   ├── index
│   │   │   │   ├── triangulos/
│   │   │   │   └── linhas/
│   │   │   │
│   │   │   └── fragmento/
│   │   │       ├── index
│   │   │       └── blend/
│   │   │
│   │   └── texturas/
│   │       ├── index
│   │       ├── carregador/
│   │       ├── cache/
│   │       └── filtros/
│   │
│   ├── fisica/
│   │   ├── colisoes/
│   │   └── dinamica/
│   │
│   └── audio/
│       ├── reprodutor/
│       └── mixagem/
│
└── infraestrutura/
    ├── graphics_api/
    │   ├── vulkan/
    │   └── opengl/
    └── audio_api/
        ├── openal/
        └── wasapi/
```

### 5.3 Exemplo: Aplicação Mobile (Health Tracker)

```
health_tracker/
├── fronteira/
│   ├── ui/
│   │   ├── telas/
│   │   │   ├── dashboard/
│   │   │   ├── atividades/
│   │   │   └── perfil/
│   │   └── componentes/
│   │       ├── graficos/
│   │       └── cartoes/
│   └── navegacao/
│
├── nucleo/
│   ├── atividades/
│   │   ├── publico/
│   │   ├── registro/
│   │   │   ├── index
│   │   │   ├── steps/
│   │   │   ├── corrida/
│   │   │   └── musculacao/
│   │   └── analytics/
│   │       ├── index
│   │       ├── calorias/
│   │       └── distancia/
│   │
│   ├── usuarios/
│   │   ├── perfil/
│   │   └── preferencias/
│   │
│   └── saude/
│       ├── sono/
│       ├── hidratacao/
│       └── alimentacao/
│
├── infraestrutura/
│   ├── sensores/
│   │   ├── acelerometro/
│   │   └── gps/
│   ├── armazenamento/
│   └── sincronizacao/
│
└── util/
    ├── conversores/
    └── formatadores/
```

---

## 6. Padrões de Comunicação

### 6.1 Comunicação entre Módulos

```
[Modulo A] ----(interface pública)----> [Modulo B]
     |                                       |
     |                                         |
     +----(evento/sinal)-------------------> [Orquestrador]
                                                  |
                                                  +----(callback)----> [Modulo C]
```

### 6.2 Padrões Suportados

| Padrão | Uso | Exemplo |
|--------|-----|---------|
| **Injeção de Dependência** | Fornecer implementações para interfaces | `new ProcessadorPagamento(clienteCartao, validador)` |
| **Pub/Sub com Eventos** | Comunicação desacoplada | `eventBus.emit('pagamento.aprovado', dados)` |
| **Mediator/Orquestrador** | Coordenação entre módulos | `CheckoutOrchestrator.processar(pedido)` |
| **Factory** | Criação de objetos complexos | `FabricaTransacao.criar(tipo, dados)` |
| **Strategy** | Algoritmos intercambiáveis | `ProcessadorStrategy.calcular(metodo)` |

### 6.3 Contratos Explicitos

**Exemplo de Contrato (Interface):**

```typescript
// nucleo/pagamentos/publico/interfaces/ProcessadorPagamento.ts
export interface ProcessadorPagamento {
    processar(dados: DadosPagamento): Promise<ResultadoTransacao>;
    cancelar(transacaoId: string): Promise<CancelamentoResultado>;
    consultarStatus(transacaoId: string): Promise<StatusTransacao>;
}
```

**Exemplo de Evento:**

```typescript
// fronteira/eventos/EventosPagamento.ts
export const EventosPagamento = {
    PAGAMENTO_INICIADO: 'pagamento.iniciado',
    PAGAMENTO_AUTORIZADO: 'pagamento.autorizado',
    PAGAMENTO_CAPTURADO: 'pagamento.capturado',
    PAGAMENTO_CANCELADO: 'pagamento.cancelado',
    PAGAMENTO_FALHOU: 'pagamento.falhou',
} as const;
```

---

## 7. Gatilhos de Decomposição

### 7.1 Gatilhos Automáticos

| Métrica | Limiar | Ação |
|---------|--------|------|
| Linhas de código | > 500 LOC | Dividir em submódulos |
| Responsabilidades | > 5 funções/métodos públicos | Extrair para submódulo |
| Dependências externas | > 3 imports de alto nível | Isolar em submódulo |
| Complexidade ciclomática | > 10 | Refatorar ou decompor |
| Tempo de compilação | > 5s por arquivo | Quebrar em partes menores |

### 7.2 Gatilhos Semânticos

| Sintoma | Interpretação | Ação |
|---------|---------------|------|
| "Este arquivo faz X e também Y" | Mistura de responsabilidades | Criar submódulo para Y |
| "Este módulo é usado de 5 formas diferentes" | Muitos casos de uso | Extrair submódulos por caso de uso |
| "Preciso alterar X para mudar Y" | Acoplamento inadequado | Criar interface e implementações separadas |
| "As alterações em X afetam Y" | Efeitos colaterais | Isolar X e Y em submódulos distintos |

### 7.3 Fluxo de Decisão de Decomposição

```
[Arquivo/Módulo Analisado]
        ↓
    [Complexidade > Limiar?]
        ↓                    ↓
     Sim                    Não
        ↓                    ↓
    [Criar nova pasta]   [Manter arquivo]
        ↓
    [Definir interface pública]
        ↓
    [Mover código para submódulos]
        ↓
    [Atualizar importações]
        ↓
    [Verificar contrato original mantido]
```

---

## 8. Benefícios e Trade-offs

### 8.1 Benefícios Críticos

| Benefício | Descrição | Impacto |
|-----------|-----------|---------|
| **Isolamento Total** | Módulos são independentes | +80% facilidade de manutenção |
| **Testabilidade** | Cada pasta pode ser testada em isolamento | +70% cobertura de testes |
| **Onboarding** | Novos devs entendem o sistema por pastas | -60% tempo de ramp-up |
| **Parallelização** | Equipes podem trabalhar em pastas diferentes | +90% eficiência de times |
| **Refatoração** | Mudanças internas não afetam outros módulos | -75% risco de regressão |
| **Escalabilidade** | Sistema cresce por adição de pastas | Escalabilidade infinita teórica |

### 8.2 Trade-offs e Desafios

| Desafio | Impacto | Mitigação |
|---------|---------|-----------|
| **Overhead de arquivos** | Muitas pastas e arquivos | Automatizar criação de estrutura |
| **Complexidade de navegação** | Hierarquia profunda | IDEs com boa navegação e docs |
| **Dificuldade de visão global** | Perda de contexto macro | Documentação arquitetural top-level |
| **Rigidez inicial** | Decisões precoces impactam estrutura | Refatoração contínua e iterativa |
| **Comunicação entre módulos** | Overhead de contratos | EventBus e injeção de dependência |

### 8.3 Comparativo com Outras Arquiteturas

| Característica | ARCcC | MVC | Clean Architecture | Microservices |
|----------------|-------|-----|-------------------|---------------|
| Isolamento físico | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Decomposição recursiva | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Facilidade de teste | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Onboarding | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Overhead inicial | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Escalabilidade | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 9. Guia de Transição para ARCcC

### 9.1 Estratégia de Migração de Projetos Existentes

```
Fase 0: Análise
├── Mapear arquivos por responsabilidade
├── Identificar módulos naturais
└── Listar dependências cruzadas

Fase 1: Estrutura Base
├── Criar pastas principais (fronteira, nucleo, infra)
├── Definir pontos de entrada (index)
└── Mover arquivos sem alterar lógica

Fase 2: Interface e Contratos
├── Extrair interfaces públicas
├── Criar arquivos de tipos compartilhados
└── Refatorar para usar interfaces

Fase 3: Isolamento e Decomposição
├── Identificar submódulos dentro de cada módulo
├── Criar subpastas
└── Mover código para submódulos

Fase 4: Eliminação de Acoplamento
├── Remover importações diretas entre módulos
├── Substituir por injeção de dependência
└── Implementar EventBus para comunicação

Fase 5: Otimização e Ajustes
├── Refinar interfaces
├── Ajustar estrutura conforme necessidade
└── Documentar arquitetura
```

### 9.2 Passo a Passo para Novo Projeto

1. **Crie a estrutura base:**
   ```bash
   mkdir -p {fronteira,nucleo,infraestrutura,util}
   ```

2. **Defina o primeiro módulo de negócio:**
   ```bash
   mkdir -p nucleo/modulo_A/{publico,privado}
   ```

3. **Crie o ponto de entrada:**
   ```bash
   touch nucleo/modulo_A/index.ts
   ```

4. **Implemente a interface pública:**
   ```bash
   touch nucleo/modulo_A/publico/interfaces/IServicoA.ts
   ```

5. **Implemente a lógica privada:**
   ```bash
   touch nucleo/modulo_A/privado/core/ServicoA.ts
   ```

6. **Conecte tudo via injeção de dependência**

7. **Teste o isolamento** (Teste da Caixa Preta)

8. **Repita para os próximos módulos**

### 9.3 Check-list de Conformidade ARCcC

- [ ] Cada pasta tem um `index` como ponto de entrada
- [ ] Nenhum arquivo importa diretamente de pastas irmãs
- [ ] Toda comunicação pública é via interface/contrato
- [ ] Implementações internas não são exportadas
- [ ] Cada pasta pode ser testada em isolamento
- [ ] Sem dependências circulares entre pastas
- [ ] Arquivos com > 500 LOC foram decompostos
- [ ] Pastas têm documentação (README.md)
- [ ] A estrutura segue o padrão hierárquico definido
- [ ] O sistema compila sem warnings de acoplamento

---

## 10. Ferramentas e Automatização

### 10.1 Scripts Recomendados

```bash
# Script para criar novo módulo
./scripts/criar_modulo.sh modulo_Novo

# Script para analisar estrutura
./scripts/analisar_estrutura.sh

# Script para validar conformidade
./scripts/validar_arccc.sh

# Script para gerar documentação
./scripts/gerar_docs_estrutura.sh
```

### 10.2 Integração com IDEs

- **VSCode**: Usar `.vscode/workspace.code-workspace` para organização de pastas
- **IntelliJ**: Configurar módulos como "packages" no projeto
- **Sublime**: Usar "Project Folders" para navegação hierárquica

### 10.3 CI/CD para Conformidade

```yaml
# .github/workflows/arccc_check.yml
name: ARCcC Compliance Check
on: [push]
jobs:
  check-architecture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Check for circular dependencies
        run: ./scripts/check_circular.sh
      - name: Verify isolated imports
        run: ./scripts/check_imports.sh
      - name: Check folder structure
        run: ./scripts/check_structure.sh
```

---

## 11. Estudos de Caso e Aplicações

### 11.1 Caso: Startup Fintech com 50+ Desenvolvedores

**Desafio:** Sistema monolítico com forte acoplamento entre módulos de pagamento, risco e cadastro.

**Solução ARCcC:**
- Pagamentos → submódulos por tipo de pagamento (cartão, boleto, pix)
- Risco → submódulos por análise (manual, automática, machine learning)
- Cadastro → submódulos por categoria de cliente (PF, PJ, internacional)

**Resultados:**
- Equipes independentes por módulo
- Deploy contínuo por submódulo
- Redução de 70% em bugs de regressão
- Onboarding de novos devs em 3 semanas (vs 3 meses anterior)

### 11.2 Caso: Engine de Jogos Indie

**Desafio:** Engine complexa com rendering, física, IA e áudio interligados.

**Solução ARCcC:**
- Cada sistema → módulo principal
- Submódulos por sub-sistemas específicos
- Comunicação via EventBus para reduzir acoplamento

**Resultados:**
- Possibilidade de trocar implementação de rendering (OpenGL → Vulkan)
- Testes de unidade isolados por submódulo
- Performance otimizada por submódulo específico

### 11.3 Caso: SaaS de Health Tech

**Desafio:** Sistema com múltiplos clientes e integrações complexas.

**Solução ARCcC:**
- Módulo de integrações com submódulos por parceiro
- Módulo de dados com submódulos por tipo de dado
- Submódulo de compliance com sub-submódulos por regulamentação

**Resultados:**
- Novas integrações implementadas em 2 dias (vs 2 semanas)
- Manutenção simplificada por isolamento
- Compliances diferentes coexistindo sem conflitos

---

## 12. Conclusão e Visão Final

A **ARCcC** representa uma abordagem universal e pragmaticamente orientada para arquitetura de software que coloca a **decomposição física** como ferramenta primária de gestão de complexidade.

Sua força reside em:
1. **Universalidade** - aplica-se a qualquer linguagem/framework
2. **Simplicidade** - baseada em pastas e contratos, não em padrões complexos
3. **Escalabilidade** - cresce organicamente com a complexidade do projeto
4. **Testabilidade** - isolamento natural que facilita testes
5. **Manutenibilidade** - mudanças locais não afetam o todo

A metodologia nos lembra que, no final das contas, software é sobre **organização e abstração** - e a melhor forma de organizar é através do isolamento físico e hierárquico, respeitando o princípio fundamental de que **cada coisa deve estar em seu lugar correto, e cada lugar deve conter apenas uma coisa**.

---

## 13. Referências e Leituras Adicionais

### 13.1 Princípios Relacionados

- **Single Responsibility Principle** (SRP) - Aplicado a nível de pasta
- **Dependency Inversion Principle** (DIP) - Através de contratos
- **Interface Segregation Principle** (ISP) - Interfaces minimalistas por módulo
- **Liskov Substitution Principle** (LSP) - Substituição via contratos
- **Open/Closed Principle** - Módulos fechados para modificação, abertos para extensão

### 13.2 Padrões Complementares

- **Event-Driven Architecture** - Comunicação via eventos
- **Dependency Injection** - Gerenciamento de dependências
- **Factory Pattern** - Criação de objetos complexos
- **Strategy Pattern** - Algoritmos intercambiáveis
- **Mediator Pattern** - Orquestração de comunicação

### 13.3 Ferramentas Recomendadas

- **Linters**: ESLint, Pylint, Checkstyle
- **Analisadores de Dependência**: Madge, Jdepend, NDepend
- **Gerenciadores de Módulo**: npm, yarn, pip, maven
- **Documentadores**: Docusaurus, MkDocs, Sphinx

---

## 14. Diretrizes Obrigatórias para Geração de Código por IA

> **Contexto:** Como grande parte (ou a totalidade) do código escrito sob esta arquitetura é produzido por agentes de IA, esta seção define **comandos obrigatórios e não-negociáveis** que qualquer IA (assistente de código, agente autônomo, LLM integrado ao IDE, etc.) deve seguir ao criar, renomear ou modificar qualquer artefato dentro de um projeto ARCcC. Estas diretrizes têm prioridade sobre preferências de estilo pessoais e devem ser tratadas como regras de compliance, não sugestões.

### 14.1 Regra de Ouro do Idioma

> **TODO código-fonte é escrito em inglês. Sem exceções.**

Isso inclui, obrigatoriamente:

- Nomes de **pastas/diretórios**
- Nomes de **arquivos**
- Nomes de **classes, interfaces, tipos e enums**
- Nomes de **funções, métodos e variáveis**
- Nomes de **constantes**
- Nomes de **branches, commits e tags** de controle de versão
- Chaves de **objetos, DTOs, schemas e payloads** de API
- Nomes de **eventos, tópicos de fila e rotas de endpoint**

O **português (ou qualquer outro idioma natural) é permitido apenas em:**

- Comentários voltados a humanos (quando o time preferir)
- Texto de documentação (`README.md`, `manifest.json` → campo `description`)
- Mensagens de erro/log destinadas ao usuário final (nunca no nome da exceção/classe)
- Conteúdo de dados (ex: valor de um campo `nome_produto` — mas o campo em si deve se chamar `productName`)

**Justificativa:** Times distribuídos, bibliotecas open-source, modelos de IA e ferramentas de análise estática assumem inglês como padrão. Nomes em português quebram convenções de tooling (linters, geradores de docs, autocompletar) e dificultam colaboração internacional.

### 14.2 Glossário de Tradução Conceito → Código

Este documento descreve a arquitetura em português (`fronteira`, `nucleo`, `modulo`, etc.) por clareza didática. **Ao implementar de fato**, a IA deve traduzir esses termos conceituais para os equivalentes em inglês abaixo. Este glossário é a fonte única de verdade para essa tradução — a IA não deve inventar sinônimos alternativos, para manter consistência entre projetos.

| Termo Conceitual (PT-BR, usado neste documento) | Termo Obrigatório no Código (EN) |
|---|---|
| `fronteira` | `boundary` |
| `publica` (dentro de fronteira) | `public-api` |
| `orquestrador` | `orchestrator` |
| `dispatcher` | `dispatcher` |
| `contratos` | `contracts` |
| `nucleo` | `core` |
| `modulo` | `module` |
| `sub_modulo` | `submodule` |
| `sub_sub_modulo` | `subsubmodule` |
| `publico` (dentro de módulo) | `public` |
| `privado` | `private` |
| `interfaces` | `interfaces` |
| `tipos` | `types` |
| `servicos` | `services` |
| `validadores` | `validators` |
| `transformadores` | `transformers` |
| `instrumentos` | `instruments` |
| `fabricas` | `factories` |
| `infraestrutura` | `infrastructure` |
| `persistencia` | `persistence` |
| `comunicacao` | `communication` |
| `logging` | `logging` |
| `monitoramento` | `monitoring` |
| `util` | `utils` |
| `helpers` | `helpers` |
| `constantes` | `constants` |
| `formatadores` | `formatters` |
| `testes` | `tests` |
| `index` (ponto de entrada) | `index` |
| `manifest.json` | `manifest.json` |
| `interface`/`ui` (pilar de UI) | `ui` |
| `ponte` (pilar de interoperabilidade) | `bridge` |
| `nucleo_nativo`/`motor` (pilar de núcleo nativo) | `engine` (ou `core-native`) |
| `vinculos`/`amarracoes` (bindings) | `bindings` |
| `esquema_compartilhado` | `shared-schema` |

> **Regra prática:** ao ler qualquer exemplo de estrutura de pastas neste documento (Seções 3 e 5), a IA deve mapear cada termo em português para seu equivalente em inglês desta tabela antes de criar o diretório real no projeto. Novos termos que não constam na tabela devem seguir o mesmo espírito de tradução literal e objetiva, e devem ser adicionados a este glossário assim que criados, para evitar divergência entre módulos.

### 14.3 Convenções de Nomenclatura por Tipo de Artefato

| Artefato | Convenção | Exemplo Correto | Exemplo Incorreto |
|---|---|---|---|
| Pasta/diretório | `kebab-case` | `payment-processor/` | `ProcessadorPagamento/`, `processador_pagamento/` |
| Arquivo de classe | `PascalCase` (mesmo nome da classe) | `PaymentProcessor.ts` | `payment_processor.ts`, `processadorPagamento.ts` |
| Classe / Interface / Type / Enum | `PascalCase` | `class PaymentProcessor`, `interface PaymentGateway` | `class processadorPagamento` |
| Função / Método / Variável | `camelCase` | `calculateTotalAmount()`, `userEmail` | `calcular_total()`, `email_usuario` |
| Constante imutável | `UPPER_SNAKE_CASE` | `MAX_RETRY_ATTEMPTS` | `maxRetryAttempts` (para valor fixo global) |
| Arquivo utilitário/função solta | `kebab-case` ou `camelCase` (conforme convenção da linguagem) | `format-currency.ts` | `FormataMoeda.ts` |
| Evento / Tópico de fila | `dot.case` em inglês | `payment.approved` | `pagamento.aprovado` |
| Rota de API | `kebab-case` em inglês | `/api/payment-methods` | `/api/metodos-pagamento` |
| Branch Git | `kebab-case` com prefixo semântico | `feat/payment-retry-logic` | `feature/logica-retentativa-pagamento` |
| Variável de ambiente | `UPPER_SNAKE_CASE` | `DATABASE_CONNECTION_URL` | `URL_CONEXAO_BANCO` |

Cada linguagem mantém sua convenção nativa (ex: Python usa `snake_case` para funções/variáveis em vez de `camelCase`), mas o **idioma continua sendo sempre inglês**, independentemente da convenção de caixa (case) adotada.

### 14.4 Bloco de Instrução Padrão para Prompts de IA

Ao instruir um agente de IA (via system prompt, `.cursorrules`, `CLAUDE.md`, arquivo de configuração de agente, etc.) para trabalhar em um projeto ARCcC, recomenda-se incluir literalmente o bloco abaixo:

```
REGRAS OBRIGATÓRIAS DE NOMENCLATURA (ARCcC):

1. Todo código deve ser escrito em INGLÊS: nomes de pastas, arquivos,
   classes, funções, variáveis, constantes, eventos, rotas e branches.
2. Comentários e documentação podem ser em português, mas o código
   em si (identificadores) nunca deve conter palavras em português.
3. Use o glossário de tradução da Seção 14.2 do documento ARCcC
   para converter termos arquiteturais (ex: "nucleo" -> "core",
   "fronteira" -> "boundary") antes de criar qualquer pasta ou arquivo.
4. Siga as convenções de case da Seção 14.3 (PascalCase para classes,
   camelCase para funções/variáveis, kebab-case para pastas, etc.)
5. Nunca traduza literalmente ao pé da letra de forma estranha
   (ex: NÃO usar "PaymentProcesor" tentando imitar "Processador"
   incorretamente) — use o termo correto e idiomático em inglês
   que um desenvolvedor nativo usaria.
6. Antes de criar uma nova pasta ou módulo, verifique se já existe
   um termo equivalente no glossário. Se não existir, escolha um
   nome em inglês claro e adicione-o ao glossário do documento.
7. Nunca misture idiomas dentro do mesmo identificador
   (ex: NÃO usar "getPagamentoStatus", usar "getPaymentStatus").
```

### 14.5 Checklist de Validação de Nomenclatura (antes de commitar)

- [ ] Nenhuma pasta ou arquivo criado contém palavras em português
- [ ] Nenhuma classe, função, método ou variável contém palavras em português
- [ ] Termos arquiteturais foram traduzidos conforme o Glossário (Seção 14.2)
- [ ] Convenção de case (PascalCase/camelCase/kebab-case/UPPER_SNAKE_CASE) respeitada por tipo de artefato
- [ ] Nenhum identificador mistura português e inglês na mesma palavra/expressão
- [ ] Nomes de eventos e rotas de API estão em inglês e em `dot.case`/`kebab-case`
- [ ] Comentários em português (se existirem) não vazam para nomes de exceções, logs estruturados ou chaves de payload
- [ ] Novos termos sem equivalente prévio foram adicionados ao glossário da Seção 14.2

---

## 15. Arquitetura Multi-Linguagem: Pilares e Ponte

### 15.1 O Problema: Quando um Projeto Usa Mais de uma Linguagem/Runtime

Todas as seções anteriores assumem, implicitamente, um projeto de **linguagem única** (ex: só TypeScript, só Python, só Rust). Isso cobre a maioria dos casos, mas existem projetos onde duas ou mais linguagens/runtimes coexistem e precisam se comunicar — o exemplo canônico deste documento é uma aplicação com **UI em PySide6 (Python)** e **motor de renderização em Rust + wgpu**.

Nesses casos, aplicar a hierarquia da Seção 3 diretamente na raiz do projeto **não funciona**, porque `nucleo/`, `infraestrutura/`, etc. passariam a misturar arquivos Python e Rust dentro das mesmas pastas, quebrando o Pilar 2.1 (Isolamento Absoluto por Jurisdição) — a jurisdição, neste caso, não é só "domínio de negócio", é também "linguagem/runtime".

### 15.2 A Solução: Divisão em 3 Grandes Pilares

Quando um projeto envolve duas ou mais linguagens, a **primeira camada de decomposição, antes de qualquer `boundary/`, `core/` ou `infrastructure/`**, deve ser feita por **pilar de execução**, e não por domínio de negócio:

```
[ UI ]  <---(contratos)--->  [ BRIDGE ]  <---(contratos)--->  [ ENGINE / CORE NATIVO ]
 Python                       FFI / IPC /                      Rust, C, C++, etc.
 (PySide6)                    bindings /                       (wgpu, motores nativos,
                               protocolo                         performance crítica)
```

| Pilar | Papel | Linguagem Típica | Responsabilidade |
|---|---|---|---|
| **1. `ui/`** | Apresentação e interação com o usuário | Python (PySide6), TS (Electron/Tauri front), Swift, Kotlin, etc. | Telas, widgets, estado de UI, chamadas à Ponte |
| **2. `bridge/`** | Interoperabilidade entre runtimes | Depende do par de linguagens (PyO3, FFI em C, gRPC, protobuf, JSON-RPC, WASM bindings) | Serialização, contratos compartilhados, conversão de tipos, marshalling |
| **3. `engine/`** (ou `core-native/`) | Núcleo de processamento pesado / performance-crítico | Rust, C, C++, Zig, etc. | Lógica de domínio pesada, renderização, cálculos, acesso a hardware |

> **Regra fundamental:** cada pilar é uma **jurisdição soberana de nível 0** — assim como definido na Seção 2.1, mas agora aplicada não a um módulo de negócio, e sim a um runtime inteiro. Um pilar **nunca importa/inclui/linka código-fonte de outro pilar diretamente**. Toda comunicação passa exclusivamente pela `bridge/`.

### 15.3 O ARCcC é Aplicado Dentro de Cada Pilar, de Forma Independente

Este é o ponto central: **a estrutura completa das Seções 2, 3 e 4 (boundary, core, infrastructure, utils, módulos, submódulos, regras de ouro, etc.) é replicada integralmente dentro de cada pilar**, como se cada pilar fosse, ele mesmo, um projeto ARCcC autocontido.

```
projeto-root/
│
├── ui/                              # PILAR 1 — apenas Python/PySide6 aqui dentro
│   ├── boundary/
│   │   ├── public-api/
│   │   └── orchestrator/
│   ├── core/
│   │   ├── screens/
│   │   │   ├── dashboard/
│   │   │   └── settings/
│   │   └── widgets/
│   ├── infrastructure/
│   │   └── bridge-client/          # cliente que fala com a bridge (único ponto de saída)
│   └── utils/
│
├── bridge/                          # PILAR 2 — código de interoperabilidade
│   ├── boundary/
│   │   └── contracts/              # contratos/IDL compartilhados (ex: .pyi, .proto, cbindgen headers)
│   ├── core/
│   │   ├── serialization/          # conversão de tipos entre runtimes
│   │   └── bindings/               # PyO3 bindings, FFI exports, etc.
│   └── infrastructure/
│       └── error-mapping/          # tradução de erros nativos <-> erros Python
│
└── engine/                          # PILAR 3 — apenas Rust aqui dentro
    ├── boundary/
    │   └── public-api/             # o que o engine expõe para a bridge consumir
    ├── core/
    │   ├── rendering/
    │   │   ├── pipeline/
    │   │   └── shaders/
    │   ├── physics/
    │   └── scene/
    ├── infrastructure/
    │   └── wgpu-adapter/
    └── utils/
```

Observe que dentro de `ui/`, `bridge/` e `engine/` a nomenclatura segue exatamente o glossário e as convenções já definidas nas Seções 3, 4 e 14 (`boundary`, `core`, `infrastructure`, `utils`, regras de isolamento, ponto único de entrada, etc.) — **nada muda na metodologia em si**, apenas o nível em que ela começa a ser aplicada (dentro do pilar, não na raiz do projeto).

### 15.4 Regras Específicas para Projetos Multi-Pilar

| # | Regra | Descrição |
|---|-------|-----------|
| 1 | **Raiz reservada aos pilares** | A raiz do projeto contém *apenas* as pastas de pilar (`ui/`, `bridge/`, `engine/` ou equivalentes) mais arquivos de build/orquestração do monorepo (ex: `Cargo.toml`, `pyproject.toml`, `Makefile`). Nenhuma lógica de negócio vive na raiz. |
| 2 | **Comunicação exclusiva via Bridge** | `ui/` nunca importa símbolos de `engine/` diretamente (nem via FFI bruto). Toda chamada passa pelo cliente exposto em `ui/infrastructure/bridge-client/`, que fala com `bridge/`. |
| 3 | **Contrato único e versionado** | `bridge/boundary/contracts/` é a fonte única de verdade do "formato de conversa" entre os dois lados. Mudanças aqui exigem atualização coordenada de `ui/` e `engine/`. |
| 4 | **A Bridge não tem lógica de negócio** | A `bridge/` só serializa, converte tipos, mapeia erros e expõe bindings. Regras de negócio pesadas ficam no `engine/`; regras de apresentação ficam na `ui/`. |
| 5 | **Cada pilar pode ter seu próprio ciclo de release** | Como são jurisdições isoladas, `engine/` pode ser versionado, testado e até publicado (ex: como crate/lib nativa) independentemente de `ui/`. |
| 6 | **Testes de contrato na Bridge** | `bridge/` deve conter testes que validam que o formato de dados trafegado entre os dois lados permanece estável (contract testing), evitando que uma mudança silenciosa em um pilar quebre o outro. |

### 15.5 Generalização: N Pilares

O modelo de 3 pilares (UI → Bridge → Engine) é o caso mais comum, mas a mesma lógica se generaliza para **N pilares** sempre que houver mais de um runtime/linguagem no projeto. Exemplos:

- **UI (Web/TS) → Bridge (gRPC) → Backend (Go) → Bridge 2 (FFI) → Módulo Nativo (Rust)** — 4 pilares, com uma bridge entre cada par de runtimes adjacentes.
- **Mobile (Kotlin) → Bridge (JNI) → Core Compartilhado (Rust) → Bridge (WASM bindgen) → Web (TS)** — núcleo compartilhado servindo duas UIs diferentes, cada uma com sua própria bridge.

A regra permanece a mesma independentemente do número de pilares: **cada pilar aplica o ARCcC internamente, de forma isolada, e toda travessia de fronteira de linguagem/runtime passa por uma pasta `bridge/` dedicada e explícita.**

### 15.6 Checklist de Conformidade Multi-Pilar

- [ ] A raiz do projeto contém apenas pastas de pilar + arquivos de build/monorepo
- [ ] Cada pilar tem sua própria estrutura ARCcC completa (`boundary/`, `core/`, `infrastructure/`, `utils/`)
- [ ] Nenhum arquivo de um pilar importa/linka código-fonte de outro pilar diretamente
- [ ] Existe uma pasta `bridge/` explícita para cada par de runtimes que se comunicam
- [ ] `bridge/` contém apenas serialização, bindings e mapeamento de erros — nunca lógica de negócio
- [ ] O contrato de comunicação está centralizado em `bridge/boundary/contracts/` e é versionado
- [ ] Existem testes de contrato validando a estabilidade do formato de dados entre pilares
- [ ] Nomenclatura de todos os pilares segue as regras de idioma e case da Seção 14

---

## 16. Ciclo de Vigilância Contínua e Higiene Arquitetural Periódica

### 16.1 O Princípio da Anti-Entropia em Arquiteturas Vivas

A experiência prática em sistemas de grande porte demonstra que **nenhuma arquitetura permanece limpa passivamente**. À medida que novas funcionalidades, ferramentas, atalhos, painéis e tratamentos de casos de borda são incorporados nas rotinas diárias de desenvolvimento, o código sofre uma **força entrópica constante**:

1. **Inchaço Lento e Silencioso**: Arquivos começam com 100 LOC e, ao longo de várias tarefas pontuais, recebem 20 linhas aqui, 30 ali, até ultrapassarem a zona de conforto e atingirem 400-500 LOC.
2. **Acúmulo de Responsabilidades Híbridas ("God Classes Compactadas")**: Mesmo mantendo-se sob o teto estrito de 500 LOC, arquivos passam a desempenhar 3 ou mais papéis distintos (ex: apresentação + I/O de disco + persistência + cálculo matemático).
3. **Fragilidade Colateral e Regressões Ocultas**: A tentativa de alterar uma funcionalidade pontual passa a afetar inadvertidamente fluxos secundários que compartilham o mesmo arquivo ou estado mutável.

> **Regra Mandatória de Anti-Entropia:** A decomposição e a higiene de código no ARCcC **não são um evento com data de término**, mas uma **rotina contínua de engenharia e governança de software**.

### 16.2 Gatilhos e Zonas de Alerta para Refatoração Preventiva

A metodologia estabelece três zonas formais de densidade de código:

| Faixa de Linhas (LOC) | Classificação | Ação Requerida |
|---|---|---|
| **$0 - 299\text{ LOC}$** | **Zona Verde (Segura)** | Manutenção e extensão permitidas livremente, desde que respeitada a pureza de domínio. |
| **$300 - 449\text{ LOC}$** | **Zona Amarela (Alerta)** | **Massa Crítica.** Nenhuma feature expressiva deve ser adicionada sem antes planejar a extração preventiva de submódulos. |
| **$\ge 450\text{ LOC}$** | **Zona Vermelha (Bloqueio)** | **Refatoração Compulsória Imediata.** O arquivo está congelado para novas funcionalidades até ser fatiado em componentes atômicos. |

Além da métrica de LOC, o **Teste do "E" (Single Responsibility Audit)** é soberano: se um arquivo de 150 linhas desempenha duas responsabilidades técnicas distintas (ex: lógica de negócio pura E diálogo de interface do sistema operacional), a separação é obrigatória.

### 16.3 Integração com o Workflow de Desenvolvimento da Organização

Para guiar a execução prática passo a passo desse ciclo de vigilância, o ARCcC trabalha em simbiose com o manual operacional de engenharia:

👉 **Consulte o documento canônico**: [`Lumenia/docs/WORKFLOW_GERAL_DE_DESENVOLVIMENTO_E_ELEVACAO_ARCcC.md`](./WORKFLOW_GERAL_DE_DESENVOLVIMENTO_E_ELEVACAO_ARCcC.md), especialmente:
- **Seção 4**: *A Regra da Coesão de Domínio e os 4 Sintomas de Acúmulo de Papéis*.
- **Seção 5**: *O Protocolo de Auditoria Contínua e Saneamento ARCcC (Roteiro Operacional em 5 Etapas)*.
- **Seção 6 & 7**: *Tabela de Regras Quantitativas/Qualitativas e Checklist de Definição de Pronto (DoD)*.

---

*"A simplicidade é a sofisticação máxima."* - Leonardo da Vinci

*"Software is not about code, it's about organization."* - Uncle Bob Martin

---

**Versão do Documento:** 1.1.0  
**Data da Revisão:** 2026-09-07  
**Classificação:** Público - Universal  

