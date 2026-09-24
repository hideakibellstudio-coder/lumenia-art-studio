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

import os
import logging
from typing import Any, Optional

os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")

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
from .aladyn_resources_mixin import AladynResourcesMixin
from .aladyn_capabilities_mixin import AladynCapabilitiesMixin
from .native_fallback import nativo_tem

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
    AladynResourcesMixin,
    AladynCapabilitiesMixin,
    EngineBackend,
):
    """Backend nativo que encapsula e orquestra a PaintEngineFacade do ALADYN ENGINE."""

    name = "aladyn"

    def __init__(self) -> None:
        # Todo o estado compartilhado pelos mixins nasce aqui (ver aladyn_base.py).
        # As opções de render ficam no backend para serem reaplicadas a cada
        # facade nova ao trocar de documento.
        self._init_backend_state()
        try:
            from ui.core.config.manager import ConfigManager
            saved_render = ConfigManager.instance().get_section("render")
            self._undo_memory_limit_mb = max(1, int(saved_render.get("undo_limit_mb", 512)))
            self._undo_max_steps = max(1, int(saved_render.get("undo_max_steps", 50)))
            for key in self._render_options:
                if key in saved_render:
                    self._render_options[key] = bool(saved_render[key])
        except Exception:
            logger.debug("[AladynBackend] Configuração de renderização indisponível; usando padrões.", exc_info=True)

        try:
            import aladyn_engine_native
            self._native = aladyn_engine_native
            logger.info("[AladynBackend] Módulo nativo aladyn_engine_native carregado com sucesso.")
            self.set_active_document_context("default_doc", self._width, self._height)
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

    def set_render_options(self, low_latency: bool, linear_gamma: bool, deep_color: bool) -> None:
        self._render_options = {
            "low_latency": bool(low_latency),
            "linear_gamma": bool(linear_gamma),
            "deep_color": bool(deep_color),
        }
        self._push_render_options(self._facade)

    def get_render_options(self) -> dict[str, bool]:
        if self._facade:
            getters = {
                key: getattr(self._facade, f"get_{key}", None)
                for key in self._render_options
            }
            if all(getters.values()):
                return {key: bool(getter()) for key, getter in getters.items()}
        return dict(self._render_options)

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
            self._mark_document_dirty("resize")

    def render(self, pan_x: float, pan_y: float, zoom: float, rotation_rad: float) -> None:
        self._view_state = (float(pan_x), float(pan_y), max(1e-6, float(zoom)), float(rotation_rad))
        # The native facade owns the raster; touching the display accessor here
        # makes the contract explicit and refreshes the generation-backed view.
        if self._facade and nativo_tem(self._facade, "refresh_display", "a tela é atualizada pelo caminho lento"):
            self._facade.refresh_display()
        elif self._facade and nativo_tem(self._facade, "get_display_pixel_buffer", "a tela mostra o buffer bruto, sem cache de exibição"):
            self._facade.get_display_pixel_buffer()


    # ── Viewport / Câmera ────────────────────────────────────────────────

    def update_view(self, zoom: float, pan_x: float, pan_y: float, rotation: float) -> None:
        self.render(pan_x, pan_y, zoom, rotation)

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> PointerEvent:
        return PointerEvent(x=screen_x, y=screen_y, pressure=pressure, timestamp=timestamp)

    # ── Buffer de Pixels & QImage ────────────────────────────────────────

    def get_pixel_buffer(self) -> Optional[bytes]:
        if self._facade:
            return bytes(self._facade.get_pixel_buffer())
        return None

    def get_display_pixel_buffer(self) -> Optional[bytes]:
        if self._facade:
            if nativo_tem(self._facade, "get_display_pixel_buffer", "a tela mostra o buffer bruto, sem cache de exibição"):
                return bytes(self._facade.get_display_pixel_buffer())
            return bytes(self._facade.get_pixel_buffer())
        return None

    def get_qimage(self) -> Optional[QImage]:
        if self._facade:
            memview = self.get_display_pixel_buffer()
            if memview:
                w, h = self._facade.get_width(), self._facade.get_height()
                # Detach from the native buffer; the facade may reuse it on the
                # next render and QImage must remain valid for its full lifetime.
                return QImage(memview, w, h, w * 4, QImage.Format_RGBA8888).copy()
        return None

    def get_layer_pixel_buffer(self, layer_index: int) -> Optional[bytes]:
        if self._facade:
            raw = self._facade.get_layer_pixel_buffer(int(layer_index))
            return bytes(raw) if raw else None
        return None

    def get_document_generation(self) -> int:
        if self._facade:
            return int(self._facade.get_document_generation())
        return 0

    def get_layer_name(self, index: int) -> str:
        if self._facade:
            return str(self._facade.get_layer_name(int(index)))
        return ""

    def begin_layer_transaction(self) -> bool:
        return bool(self._facade and self._facade.begin_layer_transaction())

    def apply_prepared_geometry(self, prepared_uid: str) -> bool:
        prepared = self._doc_facades.get(prepared_uid)
        if not self._facade or prepared is None:
            return False
        result = self._facade.apply_prepared_geometry(prepared)
        self._width, self._height = self._facade.get_width(), self._facade.get_height()
        if result:
            self._mark_document_dirty("prepared_geometry")
        return bool(result)

    def commit_layer_transaction(self) -> int:
        res = int(self._facade.commit_layer_transaction()) if self._facade else 0
        if res:
            self._mark_document_dirty("layer_transaction")
        return res

    def cancel_layer_transaction(self) -> bool:
        if not self._facade:
            return False
        result = self._facade.cancel_layer_transaction()
        self._width, self._height = self._facade.get_width(), self._facade.get_height()
        return bool(result)

    def get_undo_step_id(self) -> int:
        return int(self._facade.get_undo_step_id()) if self._facade else 0

    def get_redo_step_id(self) -> int:
        return int(self._facade.get_redo_step_id()) if self._facade else 0

    def get_history_step_ids(self) -> list[int]:
        return list(self._facade.get_history_step_ids()) if self._facade else []

    def get_qimage_lod(self, zoom: float) -> tuple[Optional[QImage], float]:
        """Retorna QImage pré-filtrada por Box Filter correspondente ao nível LOD ideal para o zoom."""
        if not self._facade:
            return None, 1.0
        if nativo_tem(self._facade, "get_best_lod_level", "zoom afastado desenha em resolução cheia (mais lento)"):
            level = self._facade.get_best_lod_level(zoom)
            if level > 0:
                res = self._facade.get_display_pixel_buffer_lod(level)
                if res is not None:
                    memview, lod_w, lod_h, scale = res
                    return QImage(memview, lod_w, lod_h, lod_w * 4, QImage.Format_RGBA8888).copy(), scale
        return self.get_qimage(), 1.0

    def get_dirty_tile_indices(self) -> list[tuple[int, int]]:
        if self._facade:
            return self._facade.get_dirty_tile_indices()
        return []

    def clear_dirty_tiles(self) -> None:
        if self._facade:
            self._facade.clear_dirty_tiles()

    def dispatch(self, command: Any) -> None:
        from .aladyn_dispatch import dispatch
        dispatch(self, command)
