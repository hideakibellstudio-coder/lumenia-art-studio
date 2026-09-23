"""Diálogo avançado do painel de pincel e sincronização bidirecional com ele.

Separado de panel.py em 2026-09-22 (449 linhas, na parede dos 450).
"""
from __future__ import annotations

from .advanced_panel import AdvancedPanel


class BrushPanelAdvancedSyncMixin:
    """Mixin extraído de panel.py (métodos movidos sem alteração)."""

    def _open_advanced_dialog(self) -> None:
        if self._adv_panel is None:
            self._adv_panel = AdvancedPanel(self)
            self._adv_panel.sizeChanged.connect(self._sync_size_from_adv)
            self._adv_panel.opacityChanged.connect(self._sync_opacity_from_adv)
            self._adv_panel.stabilizerWeightChanged.connect(self._sync_stabilizer_from_adv)
            self._adv_panel.spacingChanged.connect(self._sync_spacing_from_adv)
            self._adv_panel.contrastChanged.connect(self._sync_contrast_from_adv)

            self._adv_panel.pressureChanged.connect(self.pressureChanged.emit)
            self._adv_panel.pressureCurvePowerChanged.connect(self.pressureCurvePowerChanged.emit)
            self._adv_panel.minDensityActiveChanged.connect(self.minDensityActiveChanged.emit)
            self._adv_panel.minDensityValueChanged.connect(self.minDensityValueChanged.emit)
            self._adv_panel.invertHeightChanged.connect(self.invertHeightChanged.emit)
            self._adv_panel.loadShapeRequested.connect(self.loadShapeRequested.emit)
            self._adv_panel.loadHeightmapRequested.connect(self.loadHeightmapRequested.emit)
            self._adv_panel.pinToggled.connect(self._on_pin_toggled)

        if self._adv_panel.isVisible():
            self._adv_panel.hide()
        else:
            self._adv_panel.sync_from_engine_profile()
            self._adv_panel.show_near(self.btn_adv)

    def _sync_size_from_adv(self, val: float) -> None:
        self.sliders_section.sync_size(val)
        self.sizeChanged.emit(val)
        if hasattr(self, "stroke_preview"):
            self.stroke_preview.update_preview()

    def _sync_opacity_from_adv(self, val: float) -> None:
        self.sliders_section.sync_opacity(val)
        self.opacityChanged.emit(val)
        if hasattr(self, "stroke_preview"):
            self.stroke_preview.update_preview()

    def _sync_stabilizer_from_adv(self, val: float) -> None:
        self.sliders_section.sync_stabilizer(val)
        self.stabilizerWeightChanged.emit(val)

    def _sync_spacing_from_adv(self, val: float) -> None:
        self.sliders_section.sync_spacing(val)
        self.spacingChanged.emit(val)

    def _sync_contrast_from_adv(self, val: float) -> None:
        self.sliders_section.sync_contrast(val)
        self.contrastChanged.emit(val)

    def _on_pin_toggled(self, param_name: str, is_pinned: bool) -> None:
        self.sliders_section.set_pinned_visible(param_name, is_pinned)
