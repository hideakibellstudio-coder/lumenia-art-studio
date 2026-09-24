"""Seção 2 do painel avançado: forma, dureza, ângulo e proporção da ponta."""
from __future__ import annotations

from ui.core.i18n import tr
from ui.core.state import BrushState

from ..brush_engine_writer import BrushEngineWriter
from ..panel_thumbnails import create_default_shape_pixmap
from .base import AdvancedSection


class TipGeometrySection(AdvancedSection):
    def __init__(self, brush: BrushState, writer: BrushEngineWriter) -> None:
        super().__init__(tr("brush.sec_tip_geometry", "2. Geometria da Ponta"), brush, writer)
        self.cmb_shape = self.engine_combo([
            tr("brush.tip_soft", "Ponta Suave (Radial)"),
            tr("brush.tip_hard", "Ponta Dura (Circular)"),
            tr("brush.tip_bristles", "Cerdas Secas"),
            tr("brush.tip_flat", "Quadrado / Chato"),
        ], self._on_shape_preset)
        self.shape_preview = self.preview_header(
            self.cmb_shape, tr("brush.load_tip_png", "Carregar PNG da Ponta"), self._load_shape)
        self.shape_preview.setPixmap(create_default_shape_pixmap())
        self.sl_hardness = self.engine_slider(
            tr("brush.tip_hardness", "Dureza da Ponta (Hardness)"), 0, 100, 100, "%",
            "hardness", 100.0, writer.hardness, profile_default=0.85)
        self.sl_angle = self.engine_slider(
            tr("brush.tip_angle", "Ângulo da Ponta"), 0, 360, 0, "°",
            "tip_angle", 1.0, lambda v: writer.tip("angle", v))
        self.sl_press_angle = self.engine_slider(
            tr("brush.pressure_angle", "Ângulo por Pressão"), 0, 360, 0, "°",
            "pressure_to_angle", 1.0, lambda v: writer.root("pressure_to_angle", v))
        self.sl_aspect = self.engine_slider(
            tr("brush.aspect_ratio", "Elipse / Proporção"), 1, 100, 100, "%",
            "tip_aspect", 100.0, lambda v: writer.tip("aspect_ratio", v), profile_default=1.0)
        self.chk_follow = self.engine_check(
            tr("brush.follow_stroke", "Seguir Direção do Traço (Follow Stroke)"),
            "follow_stroke", lambda on: writer.tip("follow_stroke", on))

    def _on_shape_preset(self, index: int) -> None:
        self._writer.shape_preset(index)
        self.refresh_preview()

    def _load_shape(self) -> None:
        if self._writer.load_texture(self, is_shape=True):
            self.refresh_preview()

    def refresh_preview(self) -> None:
        pixmap = self._writer.shape_preview()
        if pixmap is not None:
            self.shape_preview.setPixmap(pixmap)
