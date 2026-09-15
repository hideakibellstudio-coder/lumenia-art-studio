# ⚡ ALADYN ENGINE & PyBind11 Bridge

O **ALADYN ENGINE** é o motor nativo de pintura digital de ultra-baixa latência do Lumenia. Implementado inteiramente em **C++20**, foi projetado para execução em 60–240 FPS mesmo sob alta pressão de eventos de caneta stylus e tablets digitalizadores.

---

## 🏛️ 1. Arquitetura do ALADYN ENGINE (`engine/`)

### A. Fachada Única: `PaintEngineFacade`
Localizada em `engine/boundary/public-api/PaintEngineFacade.hpp`:
- Expõe todos os métodos públicos de desenho, camadas, transformações, mipmapping e canal de telemetria.
- Encapsula totalmente as estruturas internas do motor (`LayerStack`, `StrokeOrchestrator`, `DynamicStabilizer`), prevenindo acoplamentos indevidos.

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

---

## 🌉 2. Camada Bridge PyBind11 (`bridge/`)

A ponte entre o C++20 e o Python 3.11+ é implementada via **PyBind11**:

- **`bridge/core/bindings/`**:
  - `bind_layers.cpp`: Vincula operações de camadas, ordenação, visibilidade, blend modes e identidades estáveis de UID.
  - `bind_math_brush.cpp`: Vincula parâmetros de pincel, raio, opacidade, fluxo e curvas de pressão.
  - `aladyn_engine_native.cpp`: Módulo raiz CPython (`aladyn_engine_native.cp314-win_amd64.pyd`).
- **Contratos de Tipagem (`bridge/boundary/contracts/aladyn_engine_native.pyi`)**:
  - Fornece anotações de tipo completas (Type Hints) e stubs de documentação para o analisador estático (MyPy/PyLance) e para o ARCcC Navigator.

### Garantias de Memória e Posse de Buffers:
- Nenhum ponteiro C++ cru é exposto diretamente ao Python sem proprietário seguro.
- Métodos como `get_layer_pixel_buffer` e `get_composite_rgba_buffer` exportam cópias de buffer imutáveis (`bytes`) encapsuladas em objetos gerenciados pelo Python, prevenindo acessos a memória liberada (*Use-After-Free*).\n