"""Seções 4 e 5 do painel avançado: textura (matéria) do pincel e espaçamento."""
from __future__ import annotations

from ui.infrastructure.i18n import tr
from ui.core.state import BrushParam, BrushState

from .brush_engine_writer import BrushEngineWriter
from .panel_thumbnails import create_default_grain_pixmap
from .base import AdvancedSection


class BrushTextureSection(AdvancedSection):
    def __init__(self, brush: BrushState, writer: BrushEngineWriter) -> None:
        super().__init__(tr("brush.sec_texture", "4. Textura do Pincel (Matéria)"), brush, writer)
        self.cmb_b_grain = self.engine_combo([
            tr("brush.grain_fine", "Grão Fino"),
            tr("brush.grain_watercolor", "Papel Aquarela"),
            tr("brush.grain_oil_canvas", "Tela de Óleo"),
            tr("brush.grain_pure_noise", "Ruído Puro"),
        ], self._on_height_preset)
        self.preview_b_grain = self.preview_header(
            self.cmb_b_grain, tr("brush.load_texture_png", "Carregar PNG da Textura"), self._load_height)
        self.preview_b_grain.setPixmap(create_default_grain_pixmap())
        self.chk_b_grain = self.engine_check(
            tr("brush.enable_brush_texture", "Ativar Textura no Pincel"),
            "brush_grain_enabled", writer.grain_enabled, checked=True)
        self.sl_b_scale = self.engine_slider(
            tr("brush.texture_scale", "Escala da Textura"), 10, 500, 100, "%",
            "brush_grain_scale", 100.0, writer.grain_scale, profile_default=1.0)
        self.slider_contrast = self.quick_slider(
            BrushParam.CONTRAST, tr("brush.texture_contrast", "Contraste da Textura (Dureza)"),
            10, 300, 100, "%", 100.0, "contrast", False)
        self.chk_invert = self.quick_check(BrushParam.INVERT_HEIGHT, tr("brush.invert_height", "Inverter Topografia"))

    def _on_height_preset(self, index: int) -> None:
        self._writer.height_preset(index)
        self.refresh_preview()

    def _load_height(self) -> None:
        # Carregar uma topografia liga o grão no motor; a caixa acompanha.
        if self._writer.load_texture(self, is_shape=False):
            self.chk_b_grain.blockSignals(True)
            self.chk_b_grain.setChecked(True)
            self.chk_b_grain.blockSignals(False)
            self.refresh_preview()

    def refresh_preview(self) -> None:
        pixmap = self._writer.height_preview()
        if pixmap is not None:
            self.preview_b_grain.setPixmap(pixmap)


class SpacingSection(AdvancedSection):
    def __init__(self, brush: BrushState, writer: BrushEngineWriter) -> None:
        super().__init__(tr("brush.sec_spacing", "5. Espaçamento do Traço"), brush, writer)
        self.slider_spacing = self.quick_slider(
            BrushParam.SPACING, tr("brush.dab_spacing", "Espaçamento entre Dabs"),
            1, 100, 10, "%", 100.0, "spacing", False)
