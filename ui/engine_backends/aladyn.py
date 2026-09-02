"""
AladynBackend — Adaptador do ALADYN ENGINE (C++ PyBind11 / aladyn_engine_native)
================================================================================
Adaptador central que implementa a interface `EngineBackend` da Lumenia UI e conversa
diretamente com a `PaintEngineFacade` do ALADYN ENGINE.

Arquitetura ARCcC:
Herda recursivamente de mixins atômicos especializados por domínio:
- AladynMdiMixin: Gerenciamento multi-documento e isolamento de instâncias C++.
- AladynSelectionMixin: Motor de seleções (retângulo, elipse, laço, varinha mágica).
- AladynTransformMixin: Motor de transformações (escala, rotação, flip, translação).
- AladynGeometryMixin: Guias de perspectiva, simetria e snap.
- AladynLayerMixin: Camadas, pastas, filtros, ordenação e undo/redo.
- AladynBrushMixin: Parâmetros de pincéis, curvas dinâmicas e presets.
- AladynStrokeMixin: Ciclo de vida do traço, fast-path raw, flood fill e telemetria.
- AladynColorMixin: Amostragem de cor e perfis ICC.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtGui import QImage
from ui.core.engine.backend import EngineBackend, PointerEvent

from .aladyn_mdi_mixin import AladynMdiMixin
from .aladyn_selection_mixin import AladynSelectionMixin
from .aladyn_transform_mixin import AladynTransformMixin
from .aladyn_geometry_mixin import AladynGeometryMixin
from .aladyn_layer_mixin import AladynLayerMixin
from .aladyn_brush_mixin import AladynBrushMixin
from .aladyn_stroke_mixin import AladynStrokeMixin
from .aladyn_color_mixin import AladynColorMixin

logger = logging.getLogger(__name__)


class AladynBackend(
    AladynMdiMixin,
    AladynSelectionMixin,
    AladynTransformMixin,
    AladynGeometryMixin,
    AladynLayerMixin,
    AladynBrushMixin,
    AladynStrokeMixin,
    AladynColorMixin,
    EngineBackend,
):
    """Backend nativo que encapsula e orquestra a PaintEngineFacade do ALADYN ENGINE."""

    name = "aladyn"

    def __init__(self) -> None:
        self._native: Any = None
        self._facade: Any = None
        self._width: int = 800
        self._height: int = 600
        self.last_telemetry: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._action_stack: list[tuple[str, int]] = []
        self._redo_stack: list[tuple[str, int]] = []
        self._is_filling: bool = False
        self.__init_mdi__()

        try:
            import aladyn_engine_native
            self._native = aladyn_engine_native
            logger.info("[AladynBackend] Módulo nativo aladyn_engine_native carregado com sucesso.")
        except Exception as e:
            logger.info(
                f"[AladynBackend] aladyn_engine_native indisponível "
                f"({type(e).__name__}: {e}). Modo casca pura mantido."
            )
            self._native = None

    # ── Disponibilidade & ciclo de vida ──────────────────────────────────

    @property
    def available(self) -> bool:
        return self._native is not None

    def init_renderer(self, hwnd: int, width: int, height: int, canvas_w: int, canvas_h: int) -> None:
        if self._native is None:
            return
        try:
            self._width = max(1, canvas_w)
            self._height = max(1, canvas_h)
            from ui.core.document.manager import DocumentManager
            active_doc = DocumentManager.instance().active_document()
            uid = active_doc.uid if active_doc else "default_doc"
            self.set_active_document_context(uid, self._width, self._height)
            logger.info(f"[AladynBackend] Contexto C++ inicializado para doc '{uid}' ({self._width}x{self._height}).")
        except Exception as e:
            logger.error(f"[AladynBackend] Falha ao inicializar PaintEngineFacade: {e}")
            self._facade = None

    def resize(self, width: int, height: int) -> None:
        if self._facade:
            self._width = max(1, width)
            self._height = max(1, height)
            self._facade.resize_canvas(self._width, self._height)

    def render(self, pan_x: float, pan_y: float, zoom: float, rotation_rad: float) -> None:
        # A renderização do ALADYN ENGINE ocorre diretamente via buffer de pixels RGBA em get_pixel_buffer()
        pass

    # ── Viewport / Câmera ────────────────────────────────────────────────

    def update_view(self, zoom: float, pan_x: float, pan_y: float, rotation: float) -> None:
        pass

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> PointerEvent:
        return PointerEvent(x=screen_x, y=screen_y, pressure=pressure, timestamp=timestamp)

    # ── Buffer de Pixels & QImage ────────────────────────────────────────

    def get_pixel_buffer(self) -> Any:
        if self._facade:
            return self._facade.get_pixel_buffer()
        return None

    def get_display_pixel_buffer(self) -> Any:
        if self._facade:
            if hasattr(self._facade, "get_display_pixel_buffer"):
                return self._facade.get_display_pixel_buffer()
            return self._facade.get_pixel_buffer()
        return None

    def get_qimage(self) -> Optional[QImage]:
        if self._facade:
            memview = self.get_display_pixel_buffer()
            if memview:
                w, h = self._facade.get_width(), self._facade.get_height()
                return QImage(memview, w, h, w * 4, QImage.Format_RGBA8888)
        return None

    def dispatch(self, command: Any) -> None:
        pass
