# Conectando uma Engine Externa ao Lumenia

> **Audiência:** Desenvolvedor que quer plugar um motor de renderização (Rust, C++, Python, DLL externa, processo remoto, etc.) na casca do Lumenia sem modificar nenhum código de UI.

---

## Visão geral da arquitetura

O Lumenia é dividido em duas partes independentes:

| Camada | Responsabilidade |
|---|---|
| **Casca (UI)** | Janela Qt, docas, paleta de cores, camadas, navegador, shortcuts |
| **Motor (Engine)** | Renderização, pipeline de pincel, câmera, superfície WGPU/GL/Software |

A comunicação entre as duas camadas passa por **um único contrato** — a classe abstrata `EngineBackend` em [`ui/core/engine/backend.py`](../ui/core/engine/backend.py). A casca nunca conhece qual motor está rodando; o motor nunca conhece a UI.

```
┌─────────────────────────── Casca (ui/) ────────────────────────────┐
│                                                                     │
│   CanvasWidget ──► EngineRegistry.get_backend() ──► EngineBackend  │
│        ▲                                                   │        │
│   WorkspaceContainer                                       │        │
│   BrushPlugin, ColorPlugin, LayersPlugin...                │        │
│                                                            │        │
└────────────────────────────────────────────────────────────│────────┘
                                                             │
                                              ┌──────────────▼──────────────┐
                                              │  ui/engine_backends/        │
                                              │  ← ÚNICO PONTO DE           │
                                              │     ACOPLAMENTO EXTERNO →   │
                                              │                             │
                                              │  WgpuRustBackend            │
                                              │  MinhaEngineBackend  ← novo │
                                              └─────────────────────────────┘
```

---

## O contrato `EngineBackend`

Todo motor externo deve implementar a ABC em [`ui/core/engine/backend.py`](../ui/core/engine/backend.py).

### Grupos de métodos obrigatórios

#### 1. Ciclo de vida da superfície

```python
def init_renderer(self, hwnd: int, width: int, height: int,
                  canvas_w: int, canvas_h: int) -> None: ...
def resize(self, width: int, height: int) -> None: ...
def render(self, pan_x: float, pan_y: float,
           zoom: float, rotation_rad: float) -> None: ...
def clear_canvas(self) -> None: ...
```

- `init_renderer` recebe o **HWND nativo** do `CanvasWidget`. O motor pode criar sua própria janela filha ou renderizar direto na handle. É chamado uma vez após `showEvent`.
- `render` é chamado a cada frame (60 Hz em modo de traço, on-demand em modo idle).

#### 2. Pipeline de traço (stroke)

```python
def start_stroke(self, x, y, pressure) -> None: ...
def paint_stroke(self, x, y, pressure) -> None: ...
def end_stroke(self) -> None: ...
```

Coordenadas já convertidas para o **espaço do canvas** (após `to_canvas`).

#### 3. Parâmetros de pincel

```python
def set_brush_color(self, r, g, b) -> None: ...
def set_brush_size(self, size) -> None: ...
def set_brush_opacity(self, opacity) -> None: ...
def set_brush_pressure(self, pressure) -> None: ...
def set_brush_contrast(self, contrast) -> None: ...
def set_brush_spacing(self, spacing) -> None: ...
def set_brush_invert_height(self, invert) -> None: ...
def set_pressure_curve_power(self, power) -> None: ...
def set_stabilizer_weight(self, weight) -> None: ...
def set_min_density_active(self, active) -> None: ...
def set_min_density_value(self, value) -> None: ...
```

Todos chamados automaticamente pelos painéis de UI sempre que o usuário muda um controle.

#### 4. Texturas de pincel

```python
def set_shape_texture(self, pixels: bytes, width: int, height: int) -> None: ...
def set_heightmap_texture(self, pixels: bytes, width: int, height: int) -> None: ...
```

`pixels` = buffer RGBA (width × height × 4 bytes).

#### 5. Câmera / Viewport

```python
def update_view(self, zoom, pan_x, pan_y, rotation) -> None: ...

def to_canvas(self, screen_x, screen_y, pressure, timestamp) -> PointerEvent: ...
```

- `update_view` — chamado ao pan/zoom/rotação pelo usuário.
- `to_canvas` — **converte coordenadas** de tela para o espaço do canvas (a transformação inversa da câmera). Deve retornar um `PointerEvent(x, y, pressure, timestamp)`.

#### 6. Despacho de comandos (opcional)

```python
def dispatch(self, command: Any) -> None: ...
```

Se você quiser usar o sistema de `Command Objects` (`DrawCommand`, `StartStrokeCommand`, etc.), este método os recebe. Se não precisar, pode implementar como no-op.

#### 7. Disponibilidade

```python
@property
def available(self) -> bool: ...
```

Retorne `True` apenas se o binário/recursos do motor puderem ser carregados. Se `False`, o `EngineRegistry` ignora este backend e a casca roda em modo casca pura (canvas vazio).

---

## Guia passo a passo

### Passo 1 — Criar o adaptador

Crie `ui/engine_backends/minha_engine.py`:

```python
from ui.core.engine.backend import EngineBackend, PointerEvent


class MinhaEngineBackend(EngineBackend):
    """
    Adaptador para <Nome da Engine>.
    Único arquivo autorizado a importar o binário externo.
    """
    name = "minha_engine"

    def __init__(self) -> None:
        self._api = None
        try:
            # Pode ser: import ctypes / import minha_lib / socket.connect(...)
            import minha_engine_lib
            self._api = minha_engine_lib.init()
        except ImportError:
            pass  # → available == False → casca roda sem motor

    @property
    def available(self) -> bool:
        return self._api is not None

    # ── Ciclo de vida ──────────────────────────────────────────────────────

    def init_renderer(self, hwnd, width, height, canvas_w, canvas_h):
        self._api.create_surface(hwnd, width, height, canvas_w, canvas_h)

    def resize(self, width, height):
        self._api.resize(width, height)

    def render(self, pan_x, pan_y, zoom, rotation_rad):
        self._api.render_frame(pan_x, pan_y, zoom, rotation_rad)

    def clear_canvas(self):
        self._api.clear()

    # ── Traço ──────────────────────────────────────────────────────────────

    def start_stroke(self, x, y, pressure):
        self._api.stroke_begin(x, y, pressure)

    def paint_stroke(self, x, y, pressure):
        self._api.stroke_point(x, y, pressure)

    def end_stroke(self):
        self._api.stroke_end()

    # ── Pincel ─────────────────────────────────────────────────────────────

    def set_brush_color(self, r, g, b):       self._api.set_color(r, g, b)
    def set_brush_size(self, size):           self._api.set_size(size)
    def set_brush_opacity(self, opacity):     self._api.set_opacity(opacity)
    def set_brush_pressure(self, pressure):   self._api.set_pressure(pressure)
    def set_brush_contrast(self, contrast):   self._api.set_contrast(contrast)
    def set_brush_spacing(self, spacing):     self._api.set_spacing(spacing)
    def set_brush_invert_height(self, inv):   self._api.set_invert_height(inv)
    def set_pressure_curve_power(self, p):    self._api.set_pressure_curve(p)
    def set_stabilizer_weight(self, w):       self._api.set_stabilizer(w)
    def set_min_density_active(self, active): self._api.set_min_density_mode(active)
    def set_min_density_value(self, value):   self._api.set_min_density(value)

    # ── Texturas ───────────────────────────────────────────────────────────

    def set_shape_texture(self, pixels, w, h):
        self._api.upload_shape(pixels, w, h)

    def set_heightmap_texture(self, pixels, w, h):
        self._api.upload_heightmap(pixels, w, h)

    # ── Câmera ─────────────────────────────────────────────────────────────

    def update_view(self, zoom, pan_x, pan_y, rotation):
        self._api.set_camera(zoom, pan_x, pan_y, rotation)

    def to_canvas(self, screen_x, screen_y, pressure, timestamp) -> PointerEvent:
        cx, cy = self._api.screen_to_canvas(screen_x, screen_y)
        return PointerEvent(cx, cy, pressure, timestamp)

    # ── Despacho ───────────────────────────────────────────────────────────

    def dispatch(self, command):
        # Se usar Command Objects, delegue aqui. Caso contrário, deixe como no-op.
        pass
```

### Passo 2 — Registrar na factory

Em [`ui/engine_backends/__init__.py`](../ui/engine_backends/__init__.py), adicione seu backend à função `create_backends()`:

```python
def create_backends():
    backends = []

    # Backend Rust legado (existente):
    try:
        from ui.engine_backends.wgpu_rust import WgpuRustBackend
        backends.append(WgpuRustBackend())
    except Exception as e:
        logger.warning(f"WgpuRustBackend indisponível: {e}")

    # ✅ Seu novo backend — adicione aqui:
    try:
        from ui.engine_backends.minha_engine import MinhaEngineBackend
        backends.append(MinhaEngineBackend())
    except Exception as e:
        logger.warning(f"MinhaEngineBackend indisponível: {e}")

    return backends
```

> **Prioridade:** O `EngineRegistry` ativa o **primeiro** da lista cujo `available` for `True`. Coloque seu backend antes do Rust se quiser que ele tenha prioridade.

### Passo 3 — Nada mais

A casca descobre e usa o backend automaticamente no boot. Nenhum código de UI precisa ser tocado.

---

## Fluxo de dados durante um traço

```
Tablet / Mouse
    │
    ▼ (evento Qt: TabletEvent / mousePressEvent)
CanvasWidget
    │
    ├─► backend.to_canvas(screen_x, screen_y, pressure, ts)
    │         └─► PointerEvent(canvas_x, canvas_y, pressure, ts)
    │
    ├─► backend.start_stroke(canvas_x, canvas_y, pressure)   # pressionar
    ├─► backend.paint_stroke(canvas_x, canvas_y, pressure)   # mover (loop)
    └─► backend.end_stroke()                                  # soltar

    Em paralelo, a cada frame Qt (QTimer 60 Hz em modo de traço):
    └─► backend.render(pan_x, pan_y, zoom, rotation_rad)
```

Os parâmetros de pincel (cor, tamanho, opacidade…) são enviados diretamente pelos painéis de UI via sinais Qt → `WorkspaceContainer` → `backend.set_brush_*()`, antes que o primeiro `start_stroke` ocorra.

---

## Variantes de integração

| Tipo de engine | Como implementar o `__init__` do adaptador |
|---|---|
| **Binário Python (`.pyd` / extensão C)** | `import minha_engine_lib` |
| **DLL C/C++ via ctypes** | `ctypes.CDLL("minha_engine.dll")` |
| **Processo separado via socket/pipe** | `socket.connect(("localhost", 9000))` |
| **Motor Python puro** | Import direto da classe/módulo |
| **Motor remoto via gRPC** | `stub = MyEngineStub(channel)` |

Em todos os casos, apenas o arquivo `ui/engine_backends/minha_engine.py` precisa existir. A casca não sabe a diferença.

---

## Regras que não devem ser quebradas

> [!IMPORTANT]
> `import engine_core` (ou qualquer binário de motor) é permitido **somente** dentro de `ui/engine_backends/*.py`. Jamais importe um motor diretamente em `ui/core/`, `plugins/` ou qualquer outro módulo da casca.

> [!NOTE]
> Se o binário não estiver presente, `available` deve retornar `False` sem levantar exceção. A casca continuará em modo casca pura (canvas vazio, todos os painéis funcionando normalmente).

> [!TIP]
> Se precisar de **dois motores simultaneamente** (ex.: um para renderização, outro para simulação de física), implemente dois backends separados e registre os dois. O `WorkspaceContainer` pode consultar backends adicionais via `EngineRegistry` se você estender a lógica de despacho.

---

## Arquivos relevantes

| Arquivo | Papel |
|---|---|
| [`ui/core/engine/backend.py`](../ui/core/engine/backend.py) | Contrato ABC — não modificar sem consenso |
| [`ui/core/engine/registry.py`](../ui/core/engine/registry.py) | Singleton que detém o backend ativo |
| [`ui/engine_backends/__init__.py`](../ui/engine_backends/__init__.py) | Factory — **adicione seu backend aqui** |
| [`ui/engine_backends/wgpu_rust.py`](../ui/engine_backends/wgpu_rust.py) | Exemplo de adaptador (motor Rust legado) |
| [`plugins/system/workspace_core/workspace/canvas/render_widget.py`](../plugins/system/workspace_core/workspace/canvas/render_widget.py) | `CanvasWidget` — consumidor do backend |
