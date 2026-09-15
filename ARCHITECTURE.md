# 🏛️ ARQUITETURA TÉCNICA PROFUNDA — LUMENIA PAINTING ENGINE

Este documento descreve a arquitetura de software, os padrões de engenharia, os algoritmos matemáticos e a estrutura de módulos do **Lumenia**.

---

## 1. Visão Geral da Arquitetura do Sistema

O Lumenia adota uma separação estrita em camadas baseada no padrão **Boundary-Control-Entity (BCE)**, integrando um frontend em **Python/PySide6 (Qt6)** a um motor de processamento nativo em **C++20 acelerado por SIMD** (`aladyn_engine_native`).

```
┌────────────────────────────────────────────────────────────────────────┐
│                        BOUNDARY (Camada Visual)                        │
│  - MainWindow & Docking Layout Manager                                 │
│  - CanvasWidget (QOpenGLWidget / QPainter Viewport com View Zoom/Rot)  │
│  - ToolSidebar, MenuBar, ColorWheelHUD, Dialogs                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Sinais / Eventos Qt
┌───────────────────────────────────▼────────────────────────────────────┐
│                        CONTROL (Lógica e Coordenação)                  │
│  - PluginManager (Ciclo de Vida, Injeção de Contexto & Resolução DFS)  │
│  - LayerManager (Ordem de Pilha, Grupos, Merge Down, Camada de Papel)  │
│  - SelectionController (Varinha Mágica, Laços, Marching Ants 60 FPS)   │
│  - TransformController (8 Alças, Pivô Móvel, Matriz Afim Bicúbica)     │
│  - HistoryManager (Undo/Redo Ilimitado com Snapshots Diferenciais)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Dados / Matrizes NumPy / C-Buffer
┌───────────────────────────────────▼────────────────────────────────────┐
│                   ALADYN NATIVE ENGINE (C++20 / SIMD)                  │
│  - Catmull-Rom Inking Spline Interpolator (Zero Input Lag)             │
│  - Bicubic Resampling Kernel (Matriz de Convolução com Pivô Móvel)    │
│  - SIMD Alpha Blending & Stamp Dabbing (Premultiplied Alpha)           │
│  - Color Space Matrix Transformers (sRGB, Display P3, Soft CMYK)       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. O Motor Nativo C++20 (ALADYN Native Engine)

O motor nativo reside no módulo binário `aladyn_engine_native.pyd` e na sua camada de interface Python (`ui/engine_backends/aladyn.py`).

### 🖋️ A. Interpolação Spline Catmull-Rom para Inking
Para garantir que traços rápidos ou lentos mantenham curvatura suave e afilamento orgânico sem o atraso típico de filtros de média móvel pesados, o motor implementa uma **Spline Cúbica de Catmull-Rom**:

Dado quatro pontos de controle sequenciais da caneta $\mathbf{P}_0, \mathbf{P}_1, \mathbf{P}_2, \mathbf{P}_3$ com intervalo paramétrico $t \in [0, 1]$:

$$\mathbf{C}(t) = \frac{1}{2} \begin{bmatrix} 1 & t & t^2 & t^3 \end{bmatrix} \begin{bmatrix} 0 & 2 & 0 & 0 \\ -1 & 0 & 1 & 0 \\ 2 & -5 & 4 & -1 \\ -1 & 3 & -3 & 1 \end{bmatrix} \begin{bmatrix} \mathbf{P}_0 \\ \mathbf{P}_1 \\ \mathbf{P}_2 \\ \mathbf{P}_3 \end{bmatrix}$$

*   **Propriedades:** A curva passa exatamente pelos nós intermediários $\mathbf{P}_1$ e $\mathbf{P}_2$ com continuidade $C^1$ de tangentes.
*   **Afilamento Dinâmico:** A pressão física $p(t)$ e o raio $r(t)$ são interpolados monotonicamente ao longo do comprimento de arco do traço, evitando variações bruscas de espessura.

---

### 🔄 B. Algoritmo de Transformação Afim & Interpolação Bicúbica
A ferramenta de Transformação Livre (`Ctrl+T`) utiliza uma matriz afim homogênea $3 \times 3$ combinando translação para a origem do pivô, rotação por ângulo $\theta$, escala anisotrópica $(s_x, s_y)$, espelhamentos e translação de volta ao espaço do canvas:

$$\mathbf{M} = \mathbf{T}(x_{\text{pivô}}, y_{\text{pivô}}) \cdot \mathbf{R}(\theta) \cdot \mathbf{S}(s_x, s_y) \cdot \mathbf{T}(-x_{\text{pivô}}, -y_{\text{pivô}})$$

Para a amostragem de pixels, o motor utiliza o **Kernel Bicúbico de Mitchell-Netravali / Catmull-Rom** em uma vizinhança $4 \times 4$ de pixels vizinhos:

$$W(x) = \begin{cases} (a + 2)|x|^3 - (a + 3)|x|^2 + 1 & \text{se } |x| \le 1 \\ a|x|^3 - 5a|x|^2 + 8a|x| - 4a & \text{se } 1 < |x| < 2 \\ 0 & \text{caso contrário} \end{cases}$$

*(com parâmetro cúbico $a = -0.5$ para máxima preservação de contraste em linearts).*

---

### ⚡ C. Composição Alfa Pré-Multiplicada com SIMD
A sobreposição de pinceladas (*Dabs*) sobre o canvas utiliza composição com alfa pré-multiplicado para evitar o escurecimento ou halos cinzentos nas bordas de traços semitransparentes:

$$\mathbf{C}_{\text{out}} = \mathbf{C}_{\text{src}} + \mathbf{C}_{\text{dst}} \cdot (1 - \alpha_{\text{src}})$$
$$\alpha_{\text{out}} = \alpha_{\text{src}} + \alpha_{\text{dst}} \cdot (1 - \alpha_{\text{src}})$$

Processado em blocos paralelos de 128-bit/256-bit (SSE2 / AVX2) diretamente no buffer de memória C++.

---

## 3. Pipeline de Camadas & Gerenciamento de Documentos

O sistema de camadas reside em `ui/core/document/` e `ui/boundary/orchestrator/`:

```
┌─────────────────────────────────────────────────────────────┐
│                    CanvasDocument                           │
│  - Width, Height, DPI, ColorSpaceProfile (sRGB/P3/CMYK)     │
│                                                             │
│  ├── LayerGroup: "Background & Sketch"                      │
│  │   ├── Layer: "Paper Base (Layer 0 - Cor Fixa)"           │
│  │   └── Layer: "Rough Sketch" (Opacity: 40%, Blend: Normal)│
│  │                                                          │
│  └── LayerGroup: "Lineart & Colors"                         │
│      ├── Layer: "Flat Colors" (Blend: Normal)               │
│      └── Layer: "Clean Ink" (Blend: Normal, Alpha Lock: On) │
└─────────────────────────────────────────────────────────────┘
```

*   **Grupos de Camadas:** Árvores com visibilidade recursiva. A desativação de um grupo oculta todos os seus filhos sem alterar suas propriedades individuais.
*   **Merge Down:** Mescla a camada ativa sobre a camada inferior imediata, combinando os buffers de pixels através de um canal temporário de composição e preservando o histórico de Undo/Redo.
*   **Camada 0 (Cor de Papel):** Camada base com renderização contínua de fundo personalizável sem ocupar memória desnecessária de bitmap rasterizado.

---

## 4. Arquitetura de Plugins & Extensibilidade

O Lumenia possui um sistema de plugins dinâmico gerenciado por `ui/core/plugins/manager.py`:

### Ciclo de Vida do Plugin:
1.  **Descoberta (`discover_plugins`):** Varredura dos diretórios `plugins/system/` e `plugins/ui/`.
2.  **Validação de Metadados (`PluginMetadata`):** Verificação de ID, versão, categoria e declaração de dependências.
3.  **Ordenação Topológica com DFS:** Resolução da ordem de ativação com detecção de ciclos e cache temporário para evitar instanciações redundantes.
4.  **Injeção de Contexto (`PluginContext`):** O plugin recebe APIs de logging, acesso a serviços da interface e registro de ações no menu sem acoplamento a globais.
5.  **Ativação (`activate`):** Registro de widgets em docas, ferramentas na barra lateral e manipuladores de eventos de desenho.

---

## 5. Gerenciamento de Cores & Prova Cromática

Implementado em `ui/core/document/color_profile.py`:

*   **Display P3 & sRGB:** Matrizes de conversão linear e correção gama $\gamma = 2.2$ para suporte nativo a monitores de ampla gama (*Wide Color Gamut*).
*   **Soft-Proofing CMYK (Simulação de Impressão):** Modelo matricial que simula as curvas de ganho de ponto e absorção de tinta do perfil ISO Coated v2 diretamente no viewport RGB em tempo real.
*   **Simulador de Daltonismo:** Transformação de espectro baseada no modelo de Brettel para Protanopia (cegueira ao vermelho), Deuteranopia (verde) e Tritanopia (azul).
*   **Lupa HUD (4x Loupe):** Extração de submatriz $7 \times 7$ ao redor do cursor com ampliação bicúbica e anel concêntrico de contraste.

---

## 6. Diretrizes de Otimização & Desempenho no Windows

1.  **Eliminação de Processos Invisíveis de Console:** O formatador de logs (`ui/core/logger.py`) utiliza chamadas Win32 nativas via `ctypes.windll.kernel32.SetConsoleMode` para suporte a cores ANSI, sem recorrer a `os.system("")` (que gerava spawns de `cmd.exe` no boot).
2.  **Renderização sem Flicker:** Duplo buffer (*Double Buffering*) no `CanvasWidget` com eventos de repaint limitados à taxa de atualização do monitor (V-Sync a 60/120 Hz).
3.  **Memória Controlada:** Buffers de desfazer/refazer utilizam cópias por diferença de bounding box modificada (*Dirty Region Tiles*) em vez de duplicar o canvas inteiro a cada pincelada.
