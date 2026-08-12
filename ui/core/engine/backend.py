"""
ui.core.engine.backend — Contrato EngineBackend + PointerEvent
================================================================
ABC que todo motor futuro (Rust/WGPU, OpenGL, software, etc.) DEVE implementar
para ser plugado na casca do Lumenia. Os métodos espelham o conjunto que o
antigo BridgeClient (PyO3) expunha, agora como contrato puro.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PointerEvent:
    """Ponto já convertido para o espaço do canvas (resultado de to_canvas)."""

    x: float
    y: float
    pressure: float
    timestamp: float


class EngineBackend(ABC):
    """
    Contrato de um motor de pintura plugável.

    Um backend é um objeto autossuficiente que gerencia:
      - a superfície de renderização (init_renderer com HWND);
      - o viewport/câmera (zoom, pan, rotação → to_canvas);
      - o pipeline de pincel/borracha (start/paint/end stroke + parâmetros);
      - o despacho assíncrono de comandos (dispatch).
    """

    name: str = "unnamed"

    # ── Disponibilidade & ciclo de vida ──────────────────────────────────

    @property
    def available(self) -> bool:
        """True se o binário/recursos do motor puderem ser carregados."""
        return True

    @abstractmethod
    def init_renderer(self, hwnd: int, width: int, height: int, canvas_w: int, canvas_h: int) -> None:
        """Cria a superfície de renderização a partir do HWND nativo da janela."""

    @abstractmethod
    def resize(self, width: int, height: int) -> None:
        """Redimensiona a superfície de renderização (view reescale)."""

    @abstractmethod
    def render(self, pan_x: float, pan_y: float, zoom: float, rotation_rad: float) -> None:
        """Renderiza o quadro atual com a câmera informada."""

    # ── Traço (stroke) ───────────────────────────────────────────────────

    @abstractmethod
    def start_stroke(self, x: float, y: float, pressure: float) -> None:
        """Inicia um traço (coordenadas no espaço do canvas)."""

    @abstractmethod
    def paint_stroke(self, x: float, y: float, pressure: float) -> None:
        """Continua um traço em andamento."""

    @abstractmethod
    def end_stroke(self) -> None:
        """Finaliza o traço atual."""

    @abstractmethod
    def clear_canvas(self) -> None:
        """Limpa o canvas (documento ativo)."""

    # ── Pincel ───────────────────────────────────────────────────────────

    @abstractmethod
    def set_brush_color(self, r: float, g: float, b: float) -> None: ...

    @abstractmethod
    def set_brush_size(self, size: float) -> None: ...

    @abstractmethod
    def set_brush_pressure(self, pressure: float) -> None: ...

    @abstractmethod
    def set_brush_contrast(self, contrast: float) -> None: ...

    @abstractmethod
    def set_brush_invert_height(self, invert: bool) -> None: ...

    @abstractmethod
    def set_pressure_curve_power(self, power: float) -> None: ...

    @abstractmethod
    def set_brush_spacing(self, spacing: float) -> None: ...

    @abstractmethod
    def set_brush_opacity(self, opacity: float) -> None: ...

    @abstractmethod
    def set_stabilizer_weight(self, weight: float) -> None: ...

    @abstractmethod
    def set_min_density_active(self, active: bool) -> None: ...

    @abstractmethod
    def set_min_density_value(self, value: float) -> None: ...

    # ── Texturas (shape / heightmap) ─────────────────────────────────────

    @abstractmethod
    def set_shape_texture(self, pixels: bytes, width: int, height: int) -> None: ...

    @abstractmethod
    def set_heightmap_texture(self, pixels: bytes, width: int, height: int) -> None: ...

    # ── Viewport / Câmera ────────────────────────────────────────────────

    @abstractmethod
    def update_view(self, zoom: float, pan_x: float, pan_y: float, rotation: float) -> None:
        """Atualiza a transformação de viewport do motor."""

    @abstractmethod
    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> PointerEvent:
        """Converte coordenadas de tela para o espaço do canvas."""

    # ── Despacho de comandos ─────────────────────────────────────────────

    @abstractmethod
    def dispatch(self, command: Any) -> None:
        """Despacha um comando (DrawCommand, SetBrushColorCommand, ...) para o motor.

        O backend decide se o processamento é síncrono ou em worker thread.
        """