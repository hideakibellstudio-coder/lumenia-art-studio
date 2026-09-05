# 🚀 PLANO MESTRE DE ELEVAÇÃO DO MOTOR NATIVO C++ (CAMADA 1)
**Metodologia Base**: ARCcC (*Atomic Recursive Componentization by Contract*)  
**Visão de Produto**: Padrão de Competitividade com Gigantes de Mercado (Clip Studio Paint, Photoshop, Krita, Procreate e Rebelle)  
**Data de Emissão**: 05 de Setembro de 2026  
**Escopo**: Camada 1 — `engine/` (Pilar 3: Motor Nativo) e `bridge/` (Pilar 2: Ponte PyBind11)

---

## 1. VISÃO GERAL E OBJETIVOS ESTRATÉGICOS

Este plano estabelece a folha de rota para transformar o motor nativo da Camada 1 em um núcleo de desenho e pintura digital de classe mundial.

A estratégia concilia dois imperativos fundamentais:
1. **Rigor Arquitetural ARCcC**: Decomposição atômica (< 500 LOC), contratos explícitos entre subsistemas, eliminação de código órfão e preservação dos limites soberanos dos 3 Pilares.
2. **Competitividade Comercial de Produto**: Sensação de traço com latência zero, mistura de cores natural sem bordas acinzentadas (*muddy edges*), throughput para pincéis massivos (> 500px), suporte a grandes formatos de impressão (600 DPI) e viewport a 120 FPS.

As 5 fases foram organizadas em **cascata lógica por dependência técnica e mitigação de risco**.

---

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ FASE 1: FUNDAÇÃO & HIGIENE ARCcC (Saneamento Estrutural e Contratos)            │
├─────────────────────────────────────────────────────────────────────────────────┤
│ FASE 2: REVOLUÇÃO CROMÁTICA & SENSAÇÃO DE PINTURA (Color Science & Blending)    │
├─────────────────────────────────────────────────────────────────────────────────┤
│ FASE 3: THROUGHPUT DE CARIMBOS & PINCÉIS GIGANTES (Dab Engine de Alta Carga)    │
├─────────────────────────────────────────────────────────────────────────────────┤
│ FASE 4: ESCALABILIDADE DE FORMATO & MEMÓRIA (Heavy-Duty Canvas / 600 DPI)       │
├─────────────────────────────────────────────────────────────────────────────────┤
│ FASE 5: PIPELINE DE VIEWPORT DE 120 FPS (Composição Híbrida GPU/Hardware)       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. DETALHAMENTO DAS 5 FASES DO PLANO MESTRE

---

### 🏛️ FASE 1: FUNDAÇÃO & HIGIENE ARCcC (Saneamento Estrutural e Contratos)
> **Objetivo**: Estabilizar a base nativa sob 100% de conformidade com o ARCcC, blindando a arquitetura por contratos formais para viabilizar as fases de produto sem regressões.

#### 1.1. Eliminação de Código Órfão e Ambiguidade de Cabeçalhos
* **Remover/Arquivar Cabeçalho Sombra**: Eliminar `engine/core/stroke/SymmetryEngine.hpp` (o arquivo oficial e ativo é `engine/core/math/SymmetryEngine.hpp / .cpp`).
* **Expurgar Código Morto**: Remover `engine/core/document/LayerGroup.hpp` (a gestão de grupos foi absorvida por `LayerStack` via `LayerNodeType::Group`) e `engine/core/math/Vector2D.hpp` (substituído por `MathTypes.hpp`).

#### 1.2. Decomposição Preventiva (< 500 LOC — Regra 4 ARCcC)
* **`PaintEngineFacade.cpp` (746 LOC $\rightarrow$ ~350 LOC)**:
  * A Fachada deve atuar estritamente como guardiã e despachante de alto nível.
  * Extrair rotinas procedurais de interpolação e tratamento de deflexão (`updateStrokeRaw` linhas 330–465 e `endStrokeRaw` linhas 467–561) integralmente para `boundary/public-api/internal/StrokeOrchestrator.cpp`.
  * Extrair rotinas inline de flood fill para um despachante dedicado em `boundary/public-api/internal/FloodFillOrchestrator.cpp`.
* **`LayerStack.cpp` (513 LOC $\rightarrow$ ~380 LOC)**:
  * Extrair operações compostas de mesclagem recursiva (*merge down*, aplainamento de grupos e reordenação complexa) para um módulo auxiliar especializado `LayerMerger.cpp`.

#### 1.3. Modularização da Ponte PyBind11 (Pilar 2)
* Decompor o monólito `bridge/core/bindings/engine_bindings.cpp` (552 LOC) em módulos atômicos de amarração compilados separadamente:
  * `bind_canvas.cpp`: `Tile`, `TileGrid`, `UndoManager`, buffers de pixel.
  * `bind_layers.cpp`: `Layer`, `LayerStack`, modos de mesclagem, hierarquia.
  * `bind_stroke.cpp`: `DynamicStabilizer`, dinâmicas de caneta, ciclo de traço.
  * `bind_tools.cpp`: Seleções, transformações, preenchimento, simetria e guias.

#### 1.4. Contrato de Contexto de Renderização para Mini-Motores (Regra 5)
* Introduzir a interface abstrata `IRenderContext` / `IPixelTarget`:
  * Os 8 mini-motores (`Inker`, `Pencil`, `Marker`, `Watercolor`, `OilImpasto`, `Smudge`, `Eraser`, `Blur`) deixam de incluir diretamente cabeçalhos de dados de baixo nível de `canvas/` e `document/`.
  * Toda leitura e escrita em pixels passa a ser intermediada por um contexto formal, eliminando o acoplamento horizontal cruzado.

#### 1.5. Criação do Harness de Testes C++ Standalone (Pilar 3 Puro)
* Implementar um runner de testes unitários em C++ nativo (Catch2 ou runner nativo sem dependências) para validar cinemática, alocação de tiles, composição SIMD e estabilização de forma isolada, sem necessidade do runtime do Python.

---

### 🎨 FASE 2: REVOLUÇÃO CROMÁTICA & SENSAÇÃO DE PINTURA (Color Science & Blending)
> **Objetivo**: Superar o maior gargalo de qualidade artística do software frente ao Clip Studio Paint 3.0, Krita e Rebelle: eliminar bordas acinzentadas (*muddy edges*) e adicionar dinâmica de caneta completa.

#### 2.1. Mistura Linear sRGB / Perceptual (Zero Overhead de RAM e CPU)
* **Problema**: O motor atual mescla cores no espaço sRGB não-linear com gamma 2.2 (`(src * a + dst * (1-a)) / 255`), gerando escurecimento sujo em misturas (azul + amarelo gerando cinza antes de verde).
* **Solução Técnica**:
  * Implementar tabelas de conversão pré-calculadas (LUTs bidirecionais de 256 entradas: `sRGB_to_Linear` e `Linear_to_sRGB`) no `DabRenderer` e no `Compositor`.
  * Realizar o cálculo de deposição de pigmento no espaço linear ou Oklab perceptual e converter de volta para os tiles RGBA8888 no commit.
* **Resultado para o Produto**:
  * Misturas de cores vibrantes, puras e ricas como em mídias físicas reais.
  * Preservação total da compatibilidade com os blocos de memória existentes (zero aumento no consumo de RAM).

#### 2.2. Dinâmica de Caneta Estendida (Art Pen & Apple Pencil Pro)
* Expandir a estrutura `PointerEvent` para receber e processar:
  * Rotação axial da caneta (*Barrel Roll / Twist*).
  * Azimute e Altitude nativos da ponta.
* Modulação do aspecto elíptico e rotação da ponta do pincel conforme o giro físico da caneta do artista (essencial para canetas chanfradas, marcadores e caligrafia).

#### 2.3. Dinâmicas de Carimbo e Jitter Cromático
* **Color Jitter**: Permitir modulação estocástica fina de matiz, saturação e brilho (*Hue/Sat/Brightness Jitter*) por carimbo individual (recurso chave para pintura de conceito, folhagens e texturas complexas).
* **Tangential Angle Follow**: Alinhamento contínuo automático do ângulo da ponta à tangente instantânea da curva de movimento.

---

### ⚡ FASE 3: THROUGHPUT DE CARIMBOS & PINCÉIS GIGANTES (Dab Engine de Alta Carga)
> **Objetivo**: Garantir que pincéis texturizados de 500px a 2000px mantenham taxa fluida sem sobrecarregar a CPU (alcançar o padrão de performance do Procreate Valkyrie e Photoshop).

#### 3.1. Vetorização SIMD AVX2 no Loop Interno de Carimbos
* Vetorizar a amostragem de `brushHeightTexture` e `canvasHeightTexture` dentro do `DabRenderer.cpp` com instruções SIMD (AVX2/FMA) para processar blocos de 8 pixels por instrução.
* Eliminar gargalos de divisão de ponto flutuante na interpolação de textura.

#### 3.2. Level of Detail (LOD) Adaptativo de Carimbo
* Para pincéis de grande diâmetro (> 250px), calcular o espaçamento analítico e a densidade de amostras em função da velocidade angular e do zoom visual.
* Redução de até 50% na quantidade de carimbos gerados sem nenhuma perda perceptual visível para o artista.

#### 3.3. Cache de Carimbo Invariante (*Stamp Mask Caching*)
* Para traços contínuos com parâmetros de raio e textura estáveis, pré-calcular o buffer circular do carimbo em memória rápida e realizar cópia de bloco com blend em vez de recálculo trigonométrico pixel a pixel.

---

### 💾 FASE 4: ESCALABILIDADE DE FORMATO & MEMÓRIA (Heavy-Duty Canvas / 600 DPI)
> **Objetivo**: Permitir que o Lumenia suporte telas para impressão comercial (ex: A3 a 600 DPI, ~70 Megapixels) com dezenas de camadas sem risco de encerramento do processo por falta de memória RAM.

#### 4.1. Compressão de Tiles Inativos em Memória RAM (LZ4 Streaming)
* Implementar compressão sem perdas **LZ4** para blocos de tiles pertencentes a camadas inativas ou ocultas.
* O LZ4 opera na velocidade de leitura da memória (~3 a 5 GB/s), descompactando o tile instantaneamente apenas se a camada for reativada para desenho.
* **Economia**: Redução de até 70% na pegada de RAM em projetos com 20+ camadas.

#### 4.2. Copy-on-Write (COW) em Camadas e Histórico
* Na duplicação de camadas ou na gravação de passos de Undo, reaproveitar ponteiros imutáveis de tiles inalterados em vez de clonar blocos de memória idênticos.

#### 4.3. Paginação de Segurança em Disco (*Scratch Disk / Tile Swapping*)
* Dotar o `TileGrid` e o `TileUndoManager` de capacidade de descarregar blocos antigos de histórico para arquivos temporários no disco quando a utilização de RAM física ultrapassar o limite pré-configurado pelo usuário.

---

### 🖥️ FASE 5: PIPELINE DE VIEWPORT DE 120 FPS (Hardware Acceleration)
> **Objetivo**: Desacoplar a exibição da tela da CPU, garantindo rotação, zoom e navegação instantâneos em resoluções 4K sem roubar tempo de processamento do traço.

#### 5.1. Composição e Exibição de Viewport via Texturas GPU
* Atualmente, a CPU compõe todos os tiles modificados em um `PixelBuffer` unificado e transfere o frame para o Python/Qt via memória do sistema.
* **Evolução Arquitetural**:
  * Os tiles sujos são enviados diretamente como sub-texturas para a memória de vídeo da GPU (OpenGL / Vulkan / DirectX).
  * A composição final de camadas, máscaras de corte (*clipping*) e o zoom/pan/rotação em tempo real são processados por fragment shaders na GPU.
* **Impacto no Produto**:
  * A CPU fica com 100% de sua capacidade dedicada ao cálculo do traço de tinta.
  * O viewport atinge taxa de atualização de 60 a 120 FPS cravados em qualquer nível de zoom.

---

## 3. MATRIZ COMPARATIVA DE RISCO E IMPACTO

| Fase | Foco Principal | Ganho Arquitetural (ARCcC) | Ganho de Produto (Artista) | Nível de Risco |
| :---: | :--- | :--- | :--- | :---: |
| **Fase 1** | Higiene e Contratos | Limite < 500 LOC, código limpo, contratos `IRenderContext`, bindings atômicos. | Estabilidade máxima, zero regressões, facilidade para evolução de recursos. | **Mínimo** |
| **Fase 2** | Ciência de Cor | Separação formal de modelos cromáticos e dinâmicas de entrada. | **Mistura de cores realista (adeus às bordas cinzas)**; suporte à caneta com rotação (*barrel roll*). | **Baixo** |
| **Fase 3** | Throughput de Pincel | SIMD puro concentrado em `raster/`. | **Pincéis massivos (500px a 2000px) sem queda de FPS** ou travamentos. | **Médio** |
| **Fase 4** | Gestão de Memória | Encapsulamento estrito de armazenamento em `canvas/`. | **Suporte a ilustrações de 600 DPI para impressão comercial** com dezenas de camadas sem estourar a RAM. | **Médio** |
| **Fase 5** | Viewport GPU | Fronteira estrita entre motor nativo e pipeline de renderização visual. | **Navegação, pan e rotação de tela a 120 FPS** com aceleração gráfica total. | **Alto** |

---

## 4. DIRETRIZES DE EXECUÇÃO E PRÓXIMOS PASSOS

1. **Pré-requisito Mandatório**: A **Fase 1** deve ser integralmente executada e verificada antes de qualquer alteração algorítmica de cores (Fase 2) ou de memória (Fase 4). Isso garante que o motor conte com testes independentes e arquivos com menos de 500 LOC, facilitando revisões atômicas.
2. **Paridade de Ambientes**: Todas as modificações de código devem ser replicadas e validadas simultaneamente em ambos os workspaces do projeto.
3. **Verificação Contínua**: Cada entrega deve ser acompanhada de testes automatizados e aferição de tempos de ciclo no Cockpit de Telemetria do sistema.

---

*Documento homologado como diretriz de engenharia para a evolução da Camada 1 do ecossistema Lumenia.*
