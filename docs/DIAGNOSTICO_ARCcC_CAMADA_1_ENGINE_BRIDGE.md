# 🏛️ DIAGNÓSTICO ESTRUTURAL DA CAMADA 1 (MOTOR C++ & BRIDGE PYBIND11)
**Metodologia Base**: ARCcC (*Atomic Recursive Componentization by Contract*)  
**Data da Auditoria**: 05 de Setembro de 2026  
**Escopo Analisado**: Camada 1 — `engine/` (Pilar 3: Motor Nativo) e `bridge/` (Pilar 2: Ponte PyBind11)  
**Total de Arquivos**: 92 arquivos (`.hpp`, `.cpp`)  
**Volume Total de Código**: ~12.500 Linhas de Código (LOC)

---

## 1. INTRODUÇÃO E ESCOPO DA AUDITORIA

Este documento consolida a radiografia estática e arquitetural da **Camada 1** do ecossistema Lumenia, avaliada estritamente sob as diretrizes do documento [`ARCcC_-_Atomic_Recursive_Componentization_by_Contract.MD`](file:///z:/DESENVOLVIMENTO/+%20LUMENIA/Lumenia/docs/ARCcC_-_Atomic_Recursive_Componentization_by_Contract.MD).

A Camada 1 é responsável pelo núcleo de processamento matemático, cinemática de traço, gestão de memória em blocos esparsos, rasterização SIMD e composição de camadas. O objetivo desta auditoria é catalogar os **Pontos Fortes** consolidados e os **Pontos Fracos / Débitos Técnicos** acumulados durante sucessivas iterações de desenvolvimento, servindo como guia para decisões de refatoração cirúrgica.

---

## 2. PONTOS FORTES (CONFORMIDADES E MÉRITOS ARCcC)

### 2.1. Soberania e Pureza de Camada (ARCcC Seção 15 — Regra dos 3 Pilares)
* **Zero vazamento de dependências para cima**: O diretório `engine/` (Pilar 3) não possui qualquer diretiva `#include` ou referência a Python, PyBind11 ou Qt. Trata-se de uma biblioteca C++17/20 autossuficiente e isolada.
* **Isolamento da Fronteira (Pilar 2)**: Todo o código de ligação PyBind11 está confinado no diretório `bridge/core/bindings/`, garantindo que o motor possa teoricamente ser compilado como DLL/SO independente para qualquer outro front-end sem retrabalho no núcleo nativo.
* **Consumo Transparente pela UI (Pilar 1)**: A interface gráfica nunca toca o binário C++ diretamente; ela se comunica unicamente através do backend `ui/engine_backends/aladyn.py`.

### 2.2. Ponto Único de Entrada e Orquestração (ARCcC Regras 3 e 5)
* **Fachada Consolidada**: O subsistema `engine/boundary/public-api/` com `PaintEngineFacade` atua como guardião estrito de entrada, expondo comandos de alto nível e ocultando os detalhes dos subsistemas internos.
* **Orquestradores Especializados**: A divisão de fluxos complexos em `engine/boundary/orchestrators/` desacoplou responsabilidades multiestágio:
  * `StrokeOrchestrator`: Ciclo de vida do traço (start, update, end, cancel).
  * `LayerStackOrchestrator`: Operações compostas sobre a árvore de camadas.
  * `SelectionOrchestrator`: Gestão de máscaras de seleção e transformações flutuantes.
  * `TransformOrchestrator`: Transformações afins sobre o canvas/viewport.
  * `BufferPasteOrchestrator`: Inserção e colagem de buffers raster.

### 2.3. Desacoplamento Cinemático vs. Rasterização (ARCcC Regra 2 — Caixa-Preta)
* **Isolamento Físico Puro**: O pipeline de `engine/core/kinematics/` e `engine/core/stroke/` processa física de massa-mola (`MassSpringDamper`), suavização (`StrokeSmoother`), interpolação e supressão de ganchos (`TailSuppressor`) operando exclusivamente com estruturas puras de pontos (`StrokeSample`), sem tocar em buffers de pixel ou estruturas de camadas.

### 2.4. Arquitetura de Memória e SIMD de Alto Desempenho
* **Grid de Tiles Esparsos**: `TileGrid` opera em blocos de $128 \times 128$ alocados sob demanda, garantindo footprint de RAM reduzido e excelente localidade espacial de cache.
* **Composição Otimizada**: `Compositor.cpp` implementa rotinas vetorizadas em SIMD (SSE2/AVX2) combinadas com paralelização OpenMP, executando mesclagem de layers em $< 0.3\text{ ms}$ em resoluções de trabalho.
* **Undo/Redo Eficiente**: `TileUndoManager` implementa verificação rápida em $O(N)$ linear sem alocações dinâmicas de heap na rota quente de pintura.

### 2.5. Polimorfismo Atômico de Pincéis (ARCcC Seção 3.2 — Contrato por Interface)
* Todos os 8 estilos de pintura nativos (Inker, Pencil, Marker, Watercolor, Oil, Smudge, Eraser, Blur) derivam da interface pura `IBrushEngine`, garantindo que novos comportamentos de pincel possam ser criados sem alterar o código dos demais motores.

---

## 3. PONTOS FRACOS E DÉBITOS TÉCNICOS (DESVIOS DO ARCcC)

### 3.1. Violação da Regra 4 (Decomposição Preventiva: Limite de 500 Linhas)
A Regra 4 do ARCcC define que qualquer arquivo que ultrapasse 500 linhas de código deve ser preventivamente decomposto para preservar a legibilidade e evitar arquivos acumuladores. Três arquivos críticos violam esse teto:

| Arquivo | Linhas (LOC) | Papel Atual | Desvio Observado |
| :--- | :---: | :--- | :--- |
| `engine/boundary/public-api/PaintEngineFacade.cpp` | **746** | Fachada Principal | Além de despachar chamadas para orquestradores, ainda implementa internamente interpolação algorítmica de traços (`updateStrokeRaw` linhas 330–465), detecção de gancho residual (`endStrokeRaw` linhas 467–561) e flood fill inline (linhas 650–700). |
| `bridge/core/bindings/engine_bindings.cpp` | **552** | Amarração PyBind11 | Monólito de exportação. Declara e amarra todas as classes do motor em um único arquivo, forçando recompilação completa a cada alteração de assinatura. |
| `engine/core/document/LayerStack.cpp` | **513** | Pilha de Camadas | Centraliza lógica de nós da árvore hierárquica, reordenação de índices, mesclagem descendente (*merge down*) e rasterização agregada. |

### 3.2. Arquivos Órfãos e Cabeçalhos-Fantasma (Falta de Higiene Estrutural)
Foram identificados arquivos que não são utilizados ou que duplicam definições, gerando risco de inclusão acidental e ferindo a clareza arquitetural:

1. **`engine/core/stroke/SymmetryEngine.hpp` (Header Sombra / Duplicata)**:
   - *Problema*: Existe uma implementação real, ativa e completa em `engine/core/math/SymmetryEngine.hpp` e `.cpp`. A versão localizada em `stroke/` é uma duplicata antiga mantida no repositório.
2. **`engine/core/document/LayerGroup.hpp` (Código Morto)**:
   - *Problema*: Nunca é incluído por nenhum arquivo do projeto. O gerenciamento de grupos foi absorvido diretamente por `LayerStack` e `Layer` através da enumeração `LayerNodeType::Group`.
3. **`engine/core/math/Vector2D.hpp` (Não Utilizado)**:
   - *Problema*: Nunca é incluído. O sistema já padronizou os tipos geométricos em `MathTypes.hpp` (`Point2D`, `Vec2`).

### 3.3. Acoplamento Horizontal Interno em `core/engines/` (Violação da Regra 5)
A matriz de dependências entre os subdiretórios de `engine/core/` revelou acoplamento excessivo dos motores de pincel com estruturas internas de outros módulos:
* O subdiretório `engine/core/engines/` realiza inclusões diretas para:
  * `canvas/`: **11 inclusões**
  * `raster/`: **10 inclusões**
  * `document/`: **8 inclusões**
  * `math/`: **10 inclusões**
* *Diagnóstico ARCcC*: Em vez de os motores (`Inker`, `Oil`, `Watercolor`) receberem uma interface de contexto de renderização uniforme (ex: `RenderContext` ou `IPixelTarget`), eles manipulam diretamente ponteiros de baixo nível de `TileGrid` e conhecem estruturas internas de `LayerStack`.

### 3.4. Monolitismo da Camada de Ponte (Pilar 2)
* O arquivo `bridge/core/bindings/engine_bindings.cpp` (552 LOC) não está dividido por domínios. Uma decomposição em arquivos atômicos de amarração (ex: `bind_stroke.cpp`, `bind_canvas.cpp`, `bind_layers.cpp`, `bind_tools.cpp`) aumentaria a manutenibilidade e o paralelismo na compilação.

### 3.5. Ausência de Suíte de Testes Nativos Standalone (Pilar 3 Desacompanhado)
* *Diagnóstico ARCcC*: Não há executável de teste unitário puramente nativo (como GoogleTest ou Catch2) dentro de `engine/`.
* *Implicação*: Toda validação do C++ é feita indiretamente através de scripts Python via PyBind11 (`tests/test_lowlevel_*.py`). Se houver um problema no linker da bridge ou incompatibilidade de ABI do Python, o motor nativo não dispõe de um mecanismo próprio para se auto-validar de forma isolada.

---

## 4. MATRIZ DE CONFORMIDADE ARCcC DA CAMADA 1

| Subdiretório / Componente | Qtd Arquivos | Volume LOC | Status ARCcC | Risco | Diagnóstico Principal |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`boundary/public-api/`** | 2 | ~890 | ⚠️ Atenção | Médio | `PaintEngineFacade.cpp` ultrapassa 500 LOC (746 LOC) e retém rotinas procedurais de traço. |
| **`boundary/orchestrators/`** | 10 | ~1.650 | ✅ Excelente | Baixo | Total aderência ao padrão de mediadores desacoplados de ciclo de vida. |
| **`core/canvas/`** | 8 | ~1.300 | ✅ Excelente | Baixo | Gestão atômica de memória em tiles esparsos e undo linear zero-alloc. |
| **`core/document/`** | 6 | ~1.100 | ⚠️ Atenção | Médio | `LayerStack.cpp` excede limite (513 LOC); presença do órfão `LayerGroup.hpp`. |
| **`core/engines/`** | 18 | ~2.600 | ⚠️ Moderado | Médio | Polimorfismo exemplar (`IBrushEngine`), porém acoplamento horizontal alto com `canvas/` e `document/`. |
| **`core/kinematics/`** | 8 | ~950 | ✅ Excelente | Baixo | Módulo exemplar: física pura desacoplada de rasterização e pixels. |
| **`core/math/`** | 12 | ~1.400 | ⚠️ Bom | Baixo | Boa precisão algorítmica; possui arquivo órfão (`Vector2D.hpp`). |
| **`core/raster/`** | 10 | ~1.550 | ✅ Bom | Baixo | SIMD SSE2/AVX2 e OpenMP altamente performáticos; acoplamento previsível com `canvas/`. |
| **`core/selection/`** | 6 | ~700 | ✅ Bom | Baixo | Mapeamento atômico e claro de máscaras de seleção e operações afins. |
| **`core/stroke/`** | 12 | ~1.450 | ⚠️ Atenção | Baixo | Algoritmos de estabilização de traço sólidos; contém duplicata `SymmetryEngine.hpp`. |
| **`bridge/core/bindings/`** | 3 | ~650 | ⚠️ Atenção | Médio | `engine_bindings.cpp` monolítico (552 LOC); recomenda-se decomposição modular. |

---

## 5. MATRIZ DE DEPENDÊNCIAS INTERNAS (`engine/core/`)

O mapeamento de inclusões cruzadas entre os submódulos de `engine/core/` revelou o seguinte grafo de dependências:

```
[engines] -------------> [canvas] (11 includes)
   |  |  |-------------> [raster] (10 includes)
   |  |----------------> [math]   (10 includes)
   |-------------------> [document] (8 includes)

[raster] --------------> [canvas] (11 includes)
   |-------------------> [math]    (4 includes)

[stroke] --------------> [math]    (9 includes)
   |-------------------> [kinematics] (1 include)

[document] ------------> [canvas]  (4 includes)

[kinematics] ----------> (Auto-contido / Zero dependências internas)
[canvas] --------------> (Auto-contido / Zero dependências internas)
```

> **Conclusão Estrutural da Matriz**:  
> `canvas` e `kinematics` são os nós folha mais puros da arquitetura (zero acoplamento com irmãos).  
> `engines` e `raster` são os módulos que mais acumulam dependências horizontais diretas, sugerindo que futuras melhorias devem concentrar-se na criação de contratos de contexto de renderização (`RenderContext`) para blindar o núcleo de pincéis.

---

*Documento gerado como base definitiva para o planejamento das próximas etapas de manutenção e refatoração da Camada 1.*
