# 🎨 MANIFESTO ARQUITETURAL DA INTERFACE DO LUMENIA
## A Filosofia do "Cockpit Canvas-First" e o Design System 2.0

---

## 1. A Filosofia: Por que o Lumenia é Radicalmente Diferente?

Softwares de desenho digital tradicionais (como Photoshop, Paint Tool SAI, Clip Studio Paint e Krita) foram concebidos sob o paradigma de desktop dos anos 1990 e 2000:
- **Docks estáticos e pesados** que ocupam 30% a 50% da área útil do monitor.
- **Painéis rígidos e travados** que forçam o artista a desviar a caneta e o olhar do centro da sua criação para ajustar uma propriedade.
- **Poluição visual constante**: dezenas de barras de ferramentas, subferramentas e inspetores sempre abertos, mesmo quando não estão sendo utilizados.

O **Lumenia** foi construído a partir de uma premissa oposta: **o Estado de Fluxo (*Flow State*) do artista é sagrado.**

> **Princípio Central**: *O Canvas é o protagonista absoluto. Nenhum controle deve existir na tela a menos que o artista esteja ativamente precisando dele. E quando necessário, o controle deve flutuar o mais próximo possível da ponta da caneta, com latência zero e estética profissional.*

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             LUMENIA WORKSPACE                            │
│ ┌──┐ ┌────────────────────────────────────────────────────────────┐ ┌──┐ │
│ │S │ │                      CANVAS ELEVADO                        │ │S │ │
│ │I │ │                                                            │ │I │ │
│ │D │ │    ┌─────────────────────────┐                             │ │D │ │
│ │E │ │    │  Floating Quick Bar ⚡  │ (Arrastável / Auto-Recolhe)  │ │E │ │
│ │B │ │    └─────────────────────────┘                             │ │B │ │
│ │A │ │                                                            │ │A │ │
│ │R │ │    ┌──────────────────────────────────────────────┐        │ │R │ │
│ │  │ │    │ Secondary Contextual Bar (Ajustes da Tool)   │        │ │  │ │
│ │L │ │    └──────────────────────────────────────────────┘        │ │R │ │
│ └──┘ └────────────────────────────────────────────────────────────┘ └──┘ │
│        ▲ Gavetas deslizam suavemente sob demanda (Drawers) ▲             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. A Estrutura da Interface Espacial do Lumenia

### 🗄️ Camada 1 — Gavetas Deslizantes com Pinagem (*Smart Drawers*)
Em vez de colunas de docks que esmagam o canvas horizontalmente:
- **Sidebars Laterais Mínimas (`SidebarWidget`)**: Apenas 40px de largura com ícones vetoriais nítidos em cada extremidade da tela (esquerda e direita).
- **Gavetas Retráteis (`WorkspaceDrawer`)**: Ao clicar em um ícone (ex: Camadas, Pincéis, Geometria), a gaveta desliza sobre o canvas sem redimensionar ou distorcer a visão do documento.
- **Sistema de Pinagem (*Pin Button*)**: Um clique no alfinete do cabeçalho (`DrawerHeader`) converte a gaveta temporária em um dock fixo. Ao desfixar, ela volta ao comportamento ágil de recolhimento automático ao clicar fora.

---

### ⚡ Camada 2 — A Barra Rápida Flutuante (*Floating Toolbar*)
Projetada para que o artista nunca precise fazer movimentos longos com o braço ou a caneta:
- **Flutuação Livre sobre o Canvas (`FloatingToolbar`)**: Pode ser posicionada em qualquer coordenada do workspace.
- **Docking Magnético Inteligente**: Quando aproximada das bordas superior, inferior ou laterais do canvas, ela se atrai suavemente para posições de ancoragem ideais.
- **Auto-Recolhimento por Inatividade**: Detecta quando o artista começou a pintar e reduz sua opacidade ou se recolhe para não bloquear o traço.
- **Catálogo de Ferramentas Customizável**: Diálogo moderno com pré-visualização em tempo real (`ToolbarLivePreview`) onde o usuário ativa ou desativa exatamente os botões que deseja em seu fluxo de trabalho.

---

### 🎛️ Camada 3 — A Barra Contextual Secundária (*Secondary Toolbar*)
Localizada na linha de visão imediata do artista, adapta-se instantaneamente à ferramenta selecionada:
- **Orientação Responsiva Dual**:
  - **Modo Horizontal (40px)**: Barra de topo compacta com controles em linha horizontal.
  - **Modo Vertical (206px)**: Barra em coluna compacta para telas panorâmicas ou laterais.
- **Contexto em Tempo Real**:
  - **Pincel / Borracha**: Espaçamento, suavização, contraste, estabilizador.
  - **Conta-Gotas**: Amostragem de ponto (1x1, 3x3, 5x5, 11x11), modo mesclado (Merged Layers), swatch de cor dinâmico.
  - **Balde de Tinta / Varinha**: Tolerância percentual, expansão em pixels, contiguidade.
  - **Formas Vetoriais**: Seletor de forma, modo de contorno/preenchimento, espessura, opacidade e gerador de cantos/estrelas.
  - **Distorção / Smudge**: Stretch, pickup de pigmento, taxa de mescla física.
  - **Texto**: Tipografia, tamanho, negrito, itálico, alinhamento.

---

### 🪟 Camada 4 — Janelas Avançadas Flutuantes (*Advanced Floating Dialogs*)
Para ajustes profundos de engenharia de pintura e geometria (ex: `AdvancedPanel` para dinâmica de pincéis e `AdvancedGeometryDialog` para perspectiva 6P):
- **Design Sem Bordas Translúcido**: Janelas frameless com cantos arredondados (`border-radius: 8px`), cabeçalho de arrasto integrado e fundo semitransparente.
- **Ancoragem Geométrica Inteligente (`show_near`)**: Calculam automaticamente o retângulo ocupado pelas gavetas e abrem adjacentes a elas, sem sobrepor a área de pintura ativa e sem transbordar os limites do monitor.
- **Abas e Seções Colapsáveis (`CollapsibleSection`)**: Agrupamento em sanfonas animadas com setas indicadoras para organizar dezenas de parâmetros complexos sem poluição.

---

## 3. O Design System Lumenia V2 (Tokens & Modularity)

O sistema visual do Lumenia é totalmente desacoplado da lógica operacional através de uma arquitetura centralizada de tokens de design.

```
┌─────────────────────────────────────────────────────────────┐
│                    THEME MANAGER (Singleton)                │
├─────────────────────────────────────────────────────────────┤
│ 1. Temas JSON: dark_default, lumenia_purple, cyberpunk,    │
│    oled_black, lumenia_light, paper_white, nordic_frost... │
│ 2. Módulos QSS: 01_globals ... 10_advanced_windows.qss     │
│ 3. Compilador de Tokens: @BG_DARKEST, @ACCENT, @BORDER...   │
│ 4. Sinal Reativo: themeChanged(theme_name)                  │
└─────────────────────────────────────────────────────────────┘
```

### 🧩 Catálogo de Componentes Canônicos

1. **`ToggleSwitch` ([`ui/core/widgets/toggle/toggle_switch.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/ui/core/widgets/toggle/toggle_switch.py))**:
   - Switch animado de alto padrão inspirado em interfaces móveis modernas.
   - Interpolação suave de posição via `QPropertyAnimation` (120ms InOutQuad).
   - Cores de fundo, indicador e borda reagem instantaneamente a trocas de tema.

2. **`CompactSlider` ([`plugins/ui/brush_plugin/compact_slider.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/plugins/ui/brush_plugin/compact_slider.py))**:
   - Barra preenchida proporcionalmente (`QPainter`) com cor de acento e opacidade calibrada.
   - Botões laterais de acessibilidade com auto-repeat para decremento `[-]` e incremento `[+]`.
   - Cursor `SplitHCursor` para ajuste tátil rápido arrastando horizontalmente.

3. **`LabeledSlider` ([`ui/core/widgets/slider/labeled_slider.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/ui/core/widgets/slider/labeled_slider.py))**:
   - Header informativo com valor em destaque colorido com o token de acento.
   - Suporte a divisores decimais, sufixos de unidade e pinagem de parâmetros.
   - Botões circulares de passo lateral.

4. **`ToolHeaderLabel` ([`ui/core/widgets/tool_options/base.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/ui/core/widgets/tool_options/base.py))**:
   - Cabeçalho compacto com ícones vetoriais SVG recoloridos dinamicamente conforme o acento ativo.

---

## 4. Integração de Baixa Latência com o Motor Nativo C++

Diferente de interfaces web-based (Electron) pesadas e lentas, a UI do Lumenia é renderizada nativamente via Qt/C++ e se comunica diretamente com a **PaintEngineFacade C++** através de bindings pybind11 de altíssima performance:

| Componente de UI | Parâmetro na UI | Destino no Motor C++ |
| :--- | :--- | :--- |
| **AdvancedPanel** | Slider de Estabilização (0..95%) | `DynamicStabilizer::set_stabilization_percentage()` |
| **AdvancedPanel** | Jitter de Tamanho e Ângulo | `BrushProfile::tip::jitter_size / jitter_angle` |
| **GeometryDialog** | Câmera 3D (Yaw, Pitch, FOV) | `CurvilinearPerspectiveRuler::set_camera()` |
| **GeometryDialog** | Magnetismo e Guias | `CurvilinearPerspectiveRuler::snap_point()` |
| **GeometryDialog** | Eixos de Simetria (2..32) | `SymmetryEngine::set_radial_segments()` |
| **LayersHeader** | Modos de Mesclagem (Normal, Add...) | `BlendEngine::blend_tiles_simd()` |

---

## 5. Resumo da Visão do Produto

O Lumenia une **a potência de cálculo e precisão do C++** com **a ergonomia e beleza visual de um cockpit moderno**. Ele não tenta imitar o passado: ele redefine o espaço de trabalho da pintura digital para colocar o foco do artista onde ele realmente importa — no traço.
