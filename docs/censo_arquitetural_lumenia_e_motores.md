# 🏛️ CENSO ARQUITETURAL COMPLETO: LUMENIA & ALADYN ENGINE

> **Inventário Geral de Engenharia de Software, Interface, Mini-Motores, Plugins e Roteiro Estratégico de Evolução.**

---

## 🗺️ 1. Mapa Topológico do Sistema

O ecossistema **Lumenia** é regido pela Constituição Arquitetural **ARCcC** (*Atomic Recursive Componentization by Contract*) e estruturado no padrão **Boundary-Control-Entity (BCE)**:

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. CAMADA DE PLUGINS & UI (`plugins/`, `ui/boundary/`, `ui/core/screens/`)                            │
│    • PySide6 (Qt6) puramente declarativo e reativo.                                                   │
│    • NUNCA importa `aladyn_engine_native` diretamente.                                                │
│    • Consome o motor UNICAMENTE via `EngineRegistry.instance().get_backend()`.                        │
│    • Plugins isolados: `brush`, `color`, `geometry`, `layers`, `navigator`, `telemetry`, `workspace`. │
├───────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. CAMADA DE BASE CENTRAL (`ui/core/`)                                                               │
│    • Átomos e Moléculas de UI: `CompactSlider`, `CollapsibleSection`, `CardBox`, `ShapeDropdown`.     │
│    • Single Source of Truth do Documento: `Document` e `LocalLayerManager` (`ui/core/document/`).      │
│    • Dinamismo de Temas: `ThemeManager` (`ui/core/theme/`) com design tokens (zero cores hex fixas).  │
│    • Contrato Universal: `EngineBackend` (`ui/core/engine/backend.py`).                               │
├───────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. CAMADA DE PONTE / BACKEND (`ui/engine_backends/`)                                                  │
│    • `AladynBackend` (`aladyn.py`): A ÚNICA camada autorizada a importar `aladyn_engine_native`.      │
│    • 8 Mixins Especializados: Brush, Stroke, Layer, Transform, Selection, Geometry, Color, MDI.      │
│    • Gerenciamento MDI: isolamento absoluto de contextos nativos por aba de documento aberto.        │
│    • Backend experimental: `wgpu_rust.py` (Rust/WGPU).                                               │
├───────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. CAMADA DE MOTOR NATIVO (`engine/`, `aladyn_engine_native`)                                        │
│    • C++20 puro de altíssimo desempenho acelerado por SIMD (AVX2 / SSE2).                             │
│    • Fachada Pública: `PaintEngineFacade` com orquestradores de estado desacoplados.                  │
│    • 8 Mini-Motores Físicos: `Inker`, `Pencil`, `Watercolor`, `OilImpasto`, `Marker`, `Eraser`, etc. │
│    • Estrutura de Canvas: Micro-Tiles 64×64 com alinhamento de 32 bytes (`alignas(32)`).              │
│    • Compositor SIMD com 18 Blend Modes, Perfis de Cor ICC (P3/CMYK) e Transformações Afins.         │
└───────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 2. Censo Detalhado dos Componentes Construídos

### A. Interface Gráfica & Design System (`ui/core/` e `ui/boundary/`)

| Componente | Arquivo / Diretório | Responsabilidade Técnica | Características de Construção |
| :--- | :--- | :--- | :--- |
| **ThemeManager** | `ui/core/theme/manager.py` | Governança de cores e design tokens | Zero `#hex` fixo em código. Troca de temas escuro/claro reativa em tempo de execução via QSS dinâmico. |
| **CompactSlider** | `ui/core/widgets/compact_slider.py` | Controle de valores contínuos e discretos | Sliders com botões de passo fino `+`/`-`, digitação direta, feedback tátil e acessibilidade. |
| **CollapsibleSection** | `ui/core/widgets/collapsible_section.py` | Agrupamento hierárquico expansível | Seções animadas de parâmetros recolhíveis com suporte a estados salvos na sessão. |
| **ShapeDropdown** | `ui/core/widgets/shape_dropdown.py` | Seletor visual de pontas de cerda | Grid de texturas e perfis de pincéis com miniaturas renderizadas em tempo real. |
| **CardBox** | `ui/core/widgets/card_box.py` | Contêiner estrutural de agrupamento | Borda suave, raio de curvatura padronizado e contraste tonal seguindo o token do tema. |
| **Icons System** | `ui/core/icons.py` | Centralização de ativos gráficos | Carregador determinístico de ícones SVG vetorizados com coloração contextual via tema. |
| **MainWindow** | `ui/boundary/orchestrator/main_window.py` | Janela mestre e layout manager | Sistema de docking profissional, barras de ferramentas destacáveis e menus de ações. |
| **Menu Actions** | `ui/boundary/orchestrator/main_window_menu_actions.py` | Roteamento de comandos globais | Despacho de mais de 50 ações de teclado e menu conectadas ao `EngineRegistry`. |
| **Diálogos do Sistema** | `ui/core/screens/` | Janelas modais e utilitárias | `NewDocumentDialog`, `DockSettings`, `CursorSettings`, `FloatingToolbar`, `CurveWindow`, `KeyboardShortcuts`. |

---

### B. Gestão de Documento & Estado (`ui/core/document/`)

| Entidade | Arquivo | Função no Sistema | Garantia Arquitetural |
| :--- | :--- | :--- | :--- |
| **Document** | `document.py` | Entidade atômica do canvas | Guarda dimensões, resolução (DPI), perfil de cores (sRGB, Display P3, Soft CMYK) e histórico. |
| **LocalLayerManager** | `layer_manager.py` | Single Source of Truth das camadas | Árvore de camadas, grupos, visibilidade, opacidade e modos de mesclagem sincronizados via sinais Qt. |
| **Camada 0 de Papel** | `layer_manager.py` | Fundo de canvas contínuo | Renderiza texturas ou cores planas de papel sem alocar bitmaps ou desperdiçar memória RAM. |

---

### C. A Camada de Ponte & Mixins (`ui/engine_backends/`)

Contrato implementado: `EngineBackend` (`ui/core/engine/backend.py`).

| Módulo / Mixin | Arquivo | Responsabilidade Técnica |
| :--- | :--- | :--- |
| **AladynBackend** | `aladyn.py` | Classe central da bridge que herda dos 8 mixins e expõe a API canônica. |
| **AladynBrushMixin** | `aladyn_brush_mixin.py` | Seleção de mini-motores nativos, tamanho, fluxo, opacidade, dinâmica e pontas. |
| **AladynStrokeMixin** | `aladyn_stroke_mixin.py` | Controle do ciclo de vida da caneta: `begin_stroke`, `update_stroke`, `end_stroke`. |
| **AladynLayerMixin** | `aladyn_layer_mixin.py` | Espelhamento da hierarquia de camadas do Python no `LayerStack` nativo em C++. |
| **AladynTransformMixin** | `aladyn_transform_mixin.py` | Controle de transformações afins $3 \times 3$ com pivô livre e reamostragem bicúbica. |
| **AladynSelectionMixin** | `aladyn_selection_mixin.py` | Gerenciamento de máscaras de seleção (varinha mágica, laço, retângulos). |
| **AladynGeometryMixin** | `aladyn_geometry_mixin.py` | Réguas de perspectiva de 1/2/3 pontos e eixos de simetria espelhada/radial. |
| **AladynColorMixin** | `aladyn_color_mixin.py` | Conversão de perfis de cor e amostragem de cores direta dos tiles nativos. |
| **AladynMdiMixin** | `aladyn_mdi_mixin.py` | **Isolamento multi-documento**: gerencia instâncias nativas independentes por aba. |

---

### D. O Motor Nativo C++20 (`engine/` / `aladyn_engine_native`)

#### 1. Os 8 Mini-Motores Físicos de Pincel (`engine/core/engines/`)
Todos os mini-motores herdam do contrato puro abstrato `IBrushEngine.hpp`:

```
               ┌───────────────────────┐
               │    IBrushEngine       │
               │   (Contrato C++20)    │
               └───────────┬───────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ InkerEngine  │    │ PencilEngine │    │WatercolorEng.│
└──────────────┘    └──────────────┘    └──────────────┘
       ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│OilImpastoEng.│    │ MarkerEngine │    │ EraserEngine │
└──────────────┘    └──────────────┘    └──────────────┘
       ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  BlurEngine  │    │ SmudgeEngine │
└──────────────┘    └──────────────┘
```

- **InkerEngine** (`InkerEngine.cpp / .hpp`): Inking de mangá de alta precisão com corte afiado e interpolação cúbica.
- **PencilEngine** (`PencilEngine.cpp / .hpp`): Simulação mineral de grafite sobre a textura de altura do papel.
- **WatercolorEngine** (`WatercolorEngine.cpp / .hpp`): Difusão com borda de acúmulo de pigmento seco (*Watercolor Fringe*).
- **OilImpastoEngine** (`OilImpastoEngine.cpp / .hpp`): Tinta a óleo viscosa com mapa de relevo tridimensional e empasto.
- **MarkerEngine** (`MarkerEngine.cpp / .hpp`): Marcador translúcido cumulativo sem dissolução de camadas secas.
- **EraserEngine** (`EraserEngine.cpp / .hpp`): Subtração vetorial e ponderada do canal alfa preservando dados RGB.
- **BlurEngine** (`BlurEngine.cpp / .hpp`): Convolução espacial adaptativa de vizinhança.
- **SmudgeEngine** (`SmudgeEngine.cpp / .hpp`): Esfuminho com reservatório dinâmico de pigmento e arraste físico.

#### 2. Orquestradores da Fachada Pública (`engine/boundary/public-api/`)
- **`PaintEngineFacade`**: Ponto único de entrada exposto ao Python via PyBind11.
- **`StrokeOrchestrator`**: Roteador do traço em tempo real (Caneta $\to$ Estabilizador $\to$ Interpolação $\to$ Dabbing nos Micro-Tiles).
- **`TransformOrchestrator`**: Matriz afim homogênea $3 \times 3$ com pivô arbitrário e interpolação Mitchell-Netravali ($a = -0.5$).
- **`SelectionOrchestrator`**: Operações booleanas com máscaras de bits (União, Subtração, Interseção) e marching ants a 60 FPS.
- **`BufferPasteOrchestrator`**: Inserção atômica de bitmaps na camada ativa com suporte a alfa pré-multiplicado.
- **`LayerStackOrchestrator`**: Coordenação da pilha de camadas e composição em C++.

#### 3. Rasterização, Canvas e Matemática (`engine/core/`)
- **`TileGrid`**: Grade esparsa de micro-tiles de **64×64 pixels** alinhados a 32 bytes (`alignas(32)`) para registradores AVX2 de 256 bits.
- **`Compositor`**: Fusão paralela de camadas em SIMD com alfa pré-multiplicado e suporte a 18 modos de mesclagem (`BlendEquations.hpp`).
- **`DabRenderer` & `DabInterpolator`**: Rasterização de carimbos circulares com suavização Hermite e interpolação Catmull-Rom.
- **`FloodFill`**: Balde de tinta scanline BFS com tolerância euclidiana RGBA.
- **`TileUndoManager`**: Histórico atômico baseado exclusivamente no delta de blocos modificados.
- **`ColorProfileManager`**: Matrizes de conversão de espaço de cores: sRGB, Display P3 e Soft CMYK.
- **`DynamicStabilizer` & `VelocityTracker`**: Suavização inercial e rastreamento dinâmico de velocidade do cursor.

---

### E. Ecossistema de Plugins (`plugins/`)

| Plugin | Categoria | Função na Interface |
| :--- | :--- | :--- |
| **brush_plugin** | UI / Tool | Painel de controle de pincéis, sliders de raio, fluxo, dureza, espaçamento e seletor de pontas. |
| **color_plugin** | UI / Tool | Seletor de cores HSV/RGB circular, histórico de amostras recentes e paleta de pigmentos. |
| **geometry_plugin** | UI / View | Painel de réguas, guias de perspectiva cônica de 1, 2 e 3 pontos e eixos de simetria radial/espelhada. |
| **layers_plugin** | UI / View | Árvore interativa de camadas com opacidade, modos de blend, bloqueio e reordenação. |
| **navigator_plugin** | UI / View | Miniatura do canvas em tempo real com indicador de câmera, zoom, pan e rotação. |
| **telemetry_plugin** | UI / View | HUD analítico exibindo taxa de quadros (FPS), tempo de frame, memória RAM e tiles alocados. |
| **workspace_core** | System | Persistência de estado da área de trabalho, posições de docking e atalhos de teclado. |

---

## 🧭 3. Guia Estratégico de Áreas para Evolução Cirúrgica

Para evitar a geração de código legado e refatorações cegas, identificamos as **5 grandes áreas funcionais** do projeto. Cada uma pode ser comparada individualmente com as origens de engenharia reversa (PaintTool SAI 2 x64 e Infinite Painter `libpainter.so`):

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ ÁREA 1: ESTABILIZADOR E INKING DE CANETA                                                    │
│ • Estado no Lumenia: `DynamicStabilizer.cpp` + Interpolação Catmull-Rom C1.                  │
│ • Referência das Origens: Fila parabólica w_i=(i+1)^1.4 com Trailing Leash e rotina flush() │
│   do SAI 2, e o Filtro de Kalman 4D do Infinite Painter.                                    │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ ÁREA 2: BALDE DE TINTA (FLOOD FILL) E FECHAMENTO DE VÃOS                                    │
│ • Estado no Lumenia: `FloodFill.cpp` (BFS scanline com tolerância euclidiana).              │
│ • Referência das Origens: Barreira morfológica anti-leak de 1 a 6px e expansão sob a linha   │
│   (Under-Line Snapping) do SAI 2 (app_part_023.c).                                          │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ ÁREA 3: COMPOSIÇÃO DE CAMADAS: CLIPPING GROUP E LOCK OPACITY                                │
│ • Estado no Lumenia: `Layer.hpp`, `Compositor.cpp` e `BlendEquations.hpp`.                  │
│ • Referência das Origens: Máscara de corte estrita (clipping_group) e proteção de           │
│   opacidade (lock_opacity ΔA=0) do SAI 2, eliminando vazamentos de sombra.                  │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ ÁREA 4: A TRÍADE ÚMIDA (BLENDING, DILUIÇÃO E PERSISTÊNCIA)                                  │
│ • Estado no Lumenia: `WatercolorEngine.cpp` e `SmudgeEngine.cpp` (SIMD básico).             │
│ • Referência das Origens: Decaimento exponencial k = exp(-Δd / 4R) e conservação de massa   │
│   do SAI 2, e os mapas de empasto 3D em shaders do Infinite Painter.                        │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ ÁREA 5: TOPOLOGIA DE CANVAS: TILES 32×32 (PÁGINA x86) vs 64×64 (AVX2)                       │
│ • Estado no Lumenia: `TileGrid.hpp` (blocos 64×64 alinhados a 32 bytes para AVX2).          │
│ • Referência das Origens: Mapeamento 1:1 de 4 KB (página virtual da CPU x86/x64) com        │
│   detecção de transparência SIMD de 1 ciclo (_mm_testz_si128) do SAI 2.                     │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```
