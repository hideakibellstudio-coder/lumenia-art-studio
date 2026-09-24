"""Propriedades de retrocompatibilidade do painel de pincel (sliders e colunas).

Separado de panel.py em 2026-09-22 (449 linhas, na parede dos 450).
"""
from __future__ import annotations

from typing import Dict
from PySide6 import QtWidgets
from ui.core.widgets.compact_slider import CompactSlider
from .components import ToolSelectionColumn


class BrushPanelCompatAccessorsMixin:
    """Mixin extraído de panel.py (métodos movidos sem alteração)."""

    # ── Retrocompatibilidade de Propriedades de Sliders e Colunas ─────────
    @property
    def qs_size(self) -> CompactSlider:
        return self.sliders_section.size_slider

    @property
    def qs_opacity(self) -> CompactSlider:
        return self.sliders_section.opacity_slider

    @property
    def size_slider(self) -> CompactSlider:
        return self.sliders_section.size_slider

    @property
    def opacity_slider(self) -> CompactSlider:
        return self.sliders_section.opacity_slider

    @property
    def contrast_slider(self) -> CompactSlider:
        return self.sliders_section.contrast_slider

    @property
    def pressure_slider(self) -> CompactSlider:
        return self.sliders_section.pressure_slider

    @property
    def curve_slider(self) -> CompactSlider:
        return self.sliders_section.curve_slider

    @property
    def stabilizer_slider(self) -> CompactSlider:
        return self.sliders_section.stabilizer_slider

    @property
    def spacing_slider(self) -> CompactSlider:
        return self.sliders_section.spacing_slider

    @property
    def min_density_slider(self) -> CompactSlider:
        return self.sliders_section.min_density_slider

    @property
    def lbl_quick(self) -> QtWidgets.QLabel:
        return self.sliders_section.lbl_quick

    @property
    def _quick_sliders(self):
        return self.sliders_section.all_sliders

    @property
    def _tool_buttons(self) -> Dict[str, QtWidgets.QToolButton]:
        return self.tool_column.tool_buttons

    @property
    def tool_col_box(self) -> ToolSelectionColumn:
        return self.tool_column
