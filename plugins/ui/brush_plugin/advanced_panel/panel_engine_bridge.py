"""
PanelEngineBridgeMixin — Sincronização e Callbacks do Painel Avançado com o Motor
===================================================================================
Trata os sinais dos sliders, checkboxes e combos conectando-os diretamente ao backend Aladyn.
"""

from __future__ import annotations

import logging
from PySide6 import QtCore, QtGui

logger = logging.getLogger(__name__)


class PanelEngineBridgeMixin:
    """Mixin que implementa todos os slots de interação entre AdvancedPanel e EngineRegistry."""

    @property
    def _backend(self):
        from ui.core.engine.registry import EngineRegistry
        return EngineRegistry.instance().get_backend()

    def _on_brush_size_changed(self, v):
        b = self._backend
        if b:
            b.set_brush_size(float(v))

    def _on_brush_opacity_changed(self, v):
        b = self._backend
        if b:
            b.set_brush_opacity(float(v / 100.0))

    def _on_min_size(self, v):
        b = self._backend
        if b:
            b.set_brush_param("root", "min_size_percent", float(v / 100.0))

    def _on_min_opacity(self, v):
        b = self._backend
        if b:
            b.set_brush_param("root", "min_opacity_percent", float(v / 100.0))

    def _on_blend_mode(self, idx: int):
        b = self._backend
        if b:
            b.set_brush_param("root", "blend_mode", int(idx))

    def _on_vel_size(self, _s):
        b = self._backend
        if b:
            b.set_brush_param("root", "velocity_size_enabled", bool(self.chk_vel_size.isChecked()))

    def _on_stroke_taper_changed(self, _s):
        b = self._backend
        if b and hasattr(self, "chk_stroke_taper"):
            b.set_brush_param("root", "stroke_taper_enabled", bool(self.chk_stroke_taper.isChecked()))

    def _on_stabilizer_changed(self, v):
        b = self._backend
        if b:
            b.set_stabilizer_weight(float(v) / 100.0)

    def _on_tip_hardness(self, v):
        b = self._backend
        if b:
            b.set_brush_hardness(float(v / 100.0))

    def _on_press_angle(self, v):
        b = self._backend
        if b:
            b.set_brush_param("root", "pressure_to_angle", float(v))

    def _on_jit_pos(self, v):
        b = self._backend
        # O slider é 0–100 %; BrushTip.jitterPosition é 0.0–1.0 (multiplicado
        # por 2×raio no motor). Escrever o valor cru dispersava os dabs por
        # cem vezes o raio.
        if b:
            b.set_brush_param("tip", "jitter_position", float(v / 100.0))

    def _on_b_grain_contrast(self, v):
        b = self._backend
        if b:
            b.set_brush_grain_contrast(float(v / 100.0))

    def _on_spacing_changed(self, v):
        b = self._backend
        if b:
            b.set_brush_spacing(float(v / 100.0))

    def update_shape_preview_from_engine(self):
        b = self._backend
        if b:
            try:
                buf = b.get_shape_preview_buffer()
                w, h = b.get_shape_preview_dimensions()
                if buf and w > 0 and h > 0:
                    img = QtGui.QImage(bytes(buf), w, h, w, QtGui.QImage.Format_Grayscale8)
                    pix = QtGui.QPixmap.fromImage(img).scaled(46, 46, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    if hasattr(self, "shape_preview"):
                        self.shape_preview.setPixmap(pix)
            except Exception as e:
                logger.debug(f"Shape preview read error: {e}")

    def update_brush_height_preview_from_engine(self):
        b = self._backend
        if b:
            try:
                buf = b.get_brush_height_preview_buffer()
                w, h = b.get_brush_height_preview_dimensions()
                if buf and w > 0 and h > 0:
                    img = QtGui.QImage(bytes(buf), w, h, w, QtGui.QImage.Format_Grayscale8)
                    pix = QtGui.QPixmap.fromImage(img).scaled(46, 46, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    if hasattr(self, "preview_b_grain"):
                        self.preview_b_grain.setPixmap(pix)
            except Exception as e:
                logger.debug(f"Brush height preview read error: {e}")

    def _on_shape_preset_changed(self, idx: int):
        b = self._backend
        if b:
            b.set_shape_preset(idx)
            self.update_shape_preview_from_engine()

    def _on_b_grain_preset_changed(self, idx: int):
        b = self._backend
        if b:
            b.set_brush_height_preset(idx)
            self.update_brush_height_preview_from_engine()

    def _on_b_grain_enabled(self, _s):
        b = self._backend
        if b:
            b.set_brush_grain_enabled(bool(self.chk_b_grain.isChecked()))

    def _on_b_grain_scale(self, v):
        b = self._backend
        if b:
            b.set_brush_grain_scale(float(v / 100.0))

    def _on_tip_angle(self, v):
        b = self._backend
        if b:
            b.set_brush_param("tip", "angle", float(v))

    def _on_tip_aspect(self, v):
        b = self._backend
        if b:
            b.set_brush_param("tip", "aspect_ratio", float(v / 100.0))

    def _on_tip_follow(self, _s):
        b = self._backend
        if b:
            b.set_brush_param("tip", "follow_stroke", bool(self.chk_follow.isChecked()))

    def _on_jit_size(self, v):
        b = self._backend
        if b:
            b.set_brush_param("tip", "jitter_size", float(v / 100.0))

    def _on_jit_angle(self, v):
        b = self._backend
        if b:
            # Slider 0–100 %; BrushTip.jitterAngle é 0.0–1.0 (× 180° no motor).
            b.set_brush_param("tip", "jitter_angle", float(v / 100.0))

    def _on_tab(self, idx):
        self.stack.setCurrentIndex(idx)

    def _draw_default_thumbnails(self):
        from .panel_thumbnails import create_default_shape_pixmap, create_default_grain_pixmap
        if hasattr(self, "shape_preview"):
            self.shape_preview.setPixmap(create_default_shape_pixmap())
        if hasattr(self, "preview_b_grain"):
            self.preview_b_grain.setPixmap(create_default_grain_pixmap())
