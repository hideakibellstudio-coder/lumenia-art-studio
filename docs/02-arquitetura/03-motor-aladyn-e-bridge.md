# ⚡ ALADYN ENGINE & PyBind11 Bridge

O **ALADYN ENGINE** é o motor nativo de pintura digital de ultra-baixa latência do Lumenia. Implementado inteiramente em **C++20**, foi projetado para execução em 60–240 FPS mesmo sob alta pressão de eventos de caneta stylus e tablets digitalizadores.

---

## 🏛️ 1. Arquitetura do ALADYN ENGINE (`engine/`)

### A. Fachada Única: `PaintEngineFacade`
Localizada em `engine/boundary/public-api/PaintEngineFacade.hpp`:
- Expõe todos os métodos públicos de desenho, camadas, transformações, mipmapping e canal de telemetria.
- Encapsula totalmente as estruturas internas do motor (`LayerStack`, `StrokeOrchestrator`, `DynamicStabilizer`), prevenindo acoplamentos indevidos.
- **A fachada e uma camada de traducao, nao de logica.** Cada metodo publico traduz argumentos e delega para um orquestrador de `engine/boundary/orchestrator/` (ver D). Qualquer metodo que cresca alem de ~4 linhas indica logica que pertence a um orquestrador -- foi o acumulo desse tipo de metodo que levou o arquivo a 929 LOC (Zona Vermelha com excecao declarada) antes da decomposicao.

### B. Pilha de Camadas: `LayerStack` e `LayerNode`
Localizada em `engine/core/document/LayerStack.cpp` e `LayerNode.hpp`:
- Representa a árvore hierárquica de camadas (camadas de desenho, pastas/grupos e camadas de filtro não-destrutivas).
- Cada nó possui um `uint64_t m_documentUid` que espelha deterministicamente o UID da camada no Python.
- Composição de cores multi-thread acelerada com suporte a blending canônico (Normal, Multiply, Screen, Overlay, etc.).

### C. Orquestrador de Traço: `StrokeOrchestrator` & `DynamicStabilizer`
Localizado em `engine/core/stroke/`:
- **Estabilização Cinemática**: O algoritmo calcula uma média exponencial ponderada da posição e velocidade da caneta, eliminando tremores manuais sem causar perda de precisão ou "efeito elástico" excessivo.
- **Interpolação Hermite / Catmull-Rom**: Pontos intermediários de traço são interpolados com alta precisão subpixel, garantindo curvas contínuas mesmo em movimentos ultrarrápidos da stylus.
- **Latência**: Processamento de cada evento em menos de $1.2\text{ms}$.

### D. Orquestradores (`engine/boundary/orchestrator/`)
Codigo que a fachada delega, um assunto por arquivo. Todos expoem apenas funcoes estaticas e recebem explicitamente o estado de que precisam -- nenhum guarda estado proprio:

| Arquivo | Assunto |
| :--- | :--- |
| `DocumentContext.hpp` | Contrato agregado (pilha, compositor, buffer de saida, cor de fundo, geracao do documento, mipmap) usado pelos demais; concentra `touch()` e a recomposicao. |
| `LayerStackOrchestrator.hpp` | Mutacoes da pilha de camadas e propriedades de camada. |
| `LayerDirtyRegion.hpp` | Calculo da regiao suja de uma mudanca puramente visual (habilita `compositeRegion` em vez de recomposicao total). |
| `DocumentStateOrchestrator` | Redimensionamento de canvas, transacoes de camada, undo/redo e resync de geometria. |
| `StrokeOrchestrator` | Fast-path nativo de traco (`*StrokeRaw`) e renderizacao de segmento. |
| `StrokeSessionOrchestrator` | Sessao de traco pelo caminho `PointerEvent` e snapshot de telemetria. |
| `SnapOrchestrator` | Guias, curvilinear (6P), perspectiva e os componentes de snap da Fase D0. |
| `SelectionOrchestrator` / `TransformOrchestrator` / `FloodFillOrchestrator` / `BufferPasteOrchestrator` | Selecao, transformacao livre, balde e colagem de buffers. |
| `RasterExportOrchestrator` | Saida raster: buffer de camada, miniatura, buffer de display e conversao de perfil de cor. |
| `MemoryOrchestrator` | Compressao de tiles inativos e metricas de memoria. |
| `BrushEngineFactory.hpp` | Unico ponto que conhece a lista concreta de motores de pincel. |

---

## 🌉 2. Camada Bridge PyBind11 (`bridge/`)

A ponte entre o C++20 e o Python 3.11+ é implementada via **PyBind11**:

- **`bridge/core/bindings/`**:
  - `bind_layers.cpp`: Vincula operações de camadas, ordenação, visibilidade, blend modes e identidades estáveis de UID.
  - `bind_math_brush.cpp`: Vincula parâmetros de pincel, raio, opacidade, fluxo e curvas de pressão.
  - `engine_bindings.cpp`: Módulo raiz CPython (`aladyn_engine_native.cp314-win_amd64.pyd`).
  - `BindingsCommon.hpp`: único ponto que inclui o motor, e só por `engine/boundary/public-api/AladynEngine.hpp` (a API pública; `tests/test_arccc_cxx_layers.py`).
- **Contratos de Tipagem (`bridge/boundary/contracts/aladyn_engine_native.pyi`)**:
  - Fornece anotações de tipo completas (Type Hints) e stubs de documentação para o analisador estático (MyPy/PyLance) e para o ARCcC Navigator.

### Garantias de Memória e Posse de Buffers:
- Nenhum ponteiro C++ cru é exposto diretamente ao Python sem proprietário seguro.
- Métodos como `get_layer_pixel_buffer` e `get_composite_rgba_buffer` exportam cópias de buffer imutáveis (`bytes`) encapsuladas em objetos gerenciados pelo Python, prevenindo acessos a memória liberada (*Use-After-Free*).

---

## 📐 3. Fundamentos Matemáticos

### A. Interpolação Spline Catmull-Rom (Inking)
Dados quatro pontos de controle sequenciais da caneta $\mathbf{P}_0, \mathbf{P}_1, \mathbf{P}_2, \mathbf{P}_3$ com parâmetro $t \in [0, 1]$:

$$\mathbf{C}(t) = \frac{1}{2} \begin{bmatrix} 1 & t & t^2 & t^3 \end{bmatrix} \begin{bmatrix} 0 & 2 & 0 & 0 \\ -1 & 0 & 1 & 0 \\ 2 & -5 & 4 & -1 \\ -1 & 3 & -3 & 1 \end{bmatrix} \begin{bmatrix} \mathbf{P}_0 \\ \mathbf{P}_1 \\ \mathbf{P}_2 \\ \mathbf{P}_3 \end{bmatrix}$$

A curva passa exatamente pelos nós intermediários $\mathbf{P}_1$ e $\mathbf{P}_2$ com continuidade $C^1$ de tangentes; pressão $p(t)$ e raio $r(t)$ são interpolados monotonicamente ao longo do comprimento de arco, evitando variações bruscas de espessura.

### B. Transformação Afim & Reamostragem Bicúbica
A ferramenta de Transformação Livre (delegada ao backend via `AladynTransformMixin`) utiliza uma matriz afim homogênea $3 \times 3$ combinando translação para o pivô, rotação $\theta$, escala anisotrópica $(s_x, s_y)$ e translação de volta:

$$\mathbf{M} = \mathbf{T}(x_{\text{pivô}}, y_{\text{pivô}}) \cdot \mathbf{R}(\theta) \cdot \mathbf{S}(s_x, s_y) \cdot \mathbf{T}(-x_{\text{pivô}}, -y_{\text{pivô}})$$

A amostragem de pixels usa o kernel bicúbico de Mitchell-Netravali/Catmull-Rom em uma vizinhança $4 \times 4$:

$$W(x) = \begin{cases} (a + 2)|x|^3 - (a + 3)|x|^2 + 1 & \text{se } |x| \le 1 \\ a|x|^3 - 5a|x|^2 + 8a|x| - 4a & \text{se } 1 < |x| < 2 \\ 0 & \text{caso contrário} \end{cases}$$

*(com $a = -0.5$ para máxima preservação de contraste em linearts).*

### C. Composição Alfa Pré-Multiplicada com SIMD
A sobreposição de *dabs* usa alfa pré-multiplicado, evitando halos cinzentos em bordas semitransparentes:

$$\mathbf{C}_{\text{out}} = \mathbf{C}_{\text{src}} + \mathbf{C}_{\text{dst}} \cdot (1 - \alpha_{\text{src}})$$
$$\alpha_{\text{out}} = \alpha_{\text{src}} + \alpha_{\text{dst}} \cdot (1 - \alpha_{\text{src}})$$

Processado em blocos paralelos de 128/256-bit (SSE2/AVX2) diretamente no buffer de memória C++.
