"""Formas vetoriais: tipo, modo de desenho, espessura, cores e o parâmetro extra do tipo.

O parâmetro extra depende do tipo de forma (raio do canto no retângulo, lados
no polígono, pontas na estrela) e mostra o valor guardado no ToolState. Até
2026-09-24 trocar o tipo zerava o slider (0 ou 5) em vez de mostrar o valor.

As cores seguem a cor do pincel pela regra `ShapeColorLink` (ui/core/state);
esta view só mostra e deixa escolher outra.
"""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.infrastructure.i18n import tr
from ui.infrastructure.icons import get_icon
from ui.core.widgets.compact_slider import CompactSlider
from ui.core.widgets.shape_dropdown import ShapeDropdown

from .base import (
    OrientedOptionsView, Text, color_button, header_row, paint_swatch, set_combo_items, set_value, slider,
    value_label, combo,
)

_DRAW_MODES = ("both", "stroke", "fill")


def _extra_field(shape_type: str):
    """(campo nas opções, mínimo, máximo, sufixo, rótulo) do parâmetro extra, ou None."""
    if shape_type == "shape_rect":
        return "corner_radius", 0, 100, "px", tr("tool_options.radius", "Raio:")
    if shape_type == "shape_polygon":
        return "polygon_sides", 3, 16, "", tr("tool_options.sides", "Lados:")
    if shape_type == "shape_star":
        return "star_points", 3, 16, "", tr("tool_options.points", "Pontas:")
    return None


class ShapesOptionsView(OrientedOptionsView):
    def __init__(self, tool_state, orientation, parent=None):
        super().__init__(tool_state, "shapes", orientation, parent)

    def build(self, layout):
        v = self.vertical
        self.lbl_icon = None
        if v:
            row, self.lbl_icon, _ = header_row(
                self, "shape_line", Text("tool_options.shapes_title", "FORMAS VETORIAIS"))
            layout.addLayout(row)
        self.shape_dropdown = ShapeDropdown()
        self.cbo_mode = combo()
        layout.addWidget(self.shape_dropdown)
        layout.addWidget(self.cbo_mode)

        self.lbl_stroke = QtWidgets.QLabel()
        self.lbl_border, self.lbl_fill = QtWidgets.QLabel(), QtWidgets.QLabel()
        self.btn_stroke_color = color_button(22 if v else 20)
        self.btn_fill_color = color_button(22 if v else 20)
        self.lbl_extra = QtWidgets.QLabel()
        self.lbl_extra.setProperty("muted", "true")
        self.lbl_extra_val = QtWidgets.QLabel()
        self.lbl_extra_val.setProperty("heading", "true")
        self.lbl_stroke_val = self.lbl_opacity = self.lbl_opacity_val = None

        if v:
            self.slider_stroke = CompactSlider("", 1, 100, "px")
            layout.addWidget(self.slider_stroke)
            colors = QtWidgets.QHBoxLayout()
            for w in (self.lbl_border, self.btn_stroke_color, self.lbl_fill, self.btn_fill_color):
                colors.addWidget(w)
            colors.addStretch()
            layout.addLayout(colors)
            for button in (self.btn_stroke_color, self.btn_fill_color):
                button.setCursor(QtCore.Qt.PointingHandCursor)
            self.slider_opacity = CompactSlider("", 0, 100, "%")
            layout.addWidget(self.slider_opacity)
            extra = QtWidgets.QHBoxLayout()
            extra.addWidget(self.lbl_extra)
            extra.addStretch()
            extra.addWidget(self.lbl_extra_val)
            layout.addLayout(extra)
            self.slider_extra = slider(0, 100)
            layout.addWidget(self.slider_extra)
        else:
            self.slider_stroke = slider(1, 100, 50)
            self.lbl_stroke_val = value_label("")
            self.lbl_opacity = QtWidgets.QLabel()
            self.slider_opacity = slider(0, 100, 45)
            self.lbl_opacity_val = value_label("")
            self.slider_extra = slider(0, 100, 45)
            for w in (self.lbl_stroke, self.slider_stroke, self.lbl_stroke_val, self.lbl_border,
                      self.btn_stroke_color, self.lbl_fill, self.btn_fill_color, self.lbl_opacity,
                      self.slider_opacity, self.lbl_opacity_val, self.lbl_extra, self.slider_extra,
                      self.lbl_extra_val):
                layout.addWidget(w)

        self.shape_dropdown.shape_changed.connect(lambda sid, _label: self.publish(shape_type=sid))
        self.cbo_mode.currentIndexChanged.connect(lambda i: self.publish(draw_mode=_DRAW_MODES[i]))
        self.slider_stroke.valueChanged.connect(lambda x: self.publish(stroke_width=x))
        self.slider_opacity.valueChanged.connect(self._on_opacity_edited)
        self.slider_extra.valueChanged.connect(self._on_extra_edited)
        self.btn_stroke_color.clicked.connect(self._pick_stroke_color)
        self.btn_fill_color.clicked.connect(self._pick_fill_color)

    # ── Edição → estado ───────────────────────────────────────────────────

    def _on_opacity_edited(self, percent: int) -> None:
        fill = QtGui.QColor(self.options()["fill_color"])
        fill.setAlpha(int(percent * 255 / 100))
        self.publish(fill_opacity=percent / 100.0, fill_color=fill)

    def _on_extra_edited(self, value: int) -> None:
        extra = _extra_field(self.options()["shape_type"])
        if extra is not None:
            self.publish(**{extra[0]: value})

    def _pick_stroke_color(self) -> None:
        color = QtWidgets.QColorDialog.getColor(
            self.options()["stroke_color"], self, tr("secondary_bar.stroke_color", "Cor de Contorno"))
        if color.isValid():
            self.publish(stroke_color=color)

    def _pick_fill_color(self) -> None:
        color = QtWidgets.QColorDialog.getColor(
            self.options()["fill_color"], self, tr("secondary_bar.fill_color", "Cor de Preenchimento"),
            QtWidgets.QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.publish(fill_color=color, fill_opacity=color.alphaF())

    # ── Estado → tela ─────────────────────────────────────────────────────

    def show_options(self, o):
        shape = o["shape_type"]
        self.shape_dropdown.set_shape(shape)  # não emite; também põe o ícone
        if self.lbl_icon is not None:
            self.lbl_icon.setPixmap(get_icon(shape).pixmap(14, 14))
        self.cbo_mode.setCurrentIndex(_DRAW_MODES.index(o["draw_mode"]))
        set_value(self.slider_stroke, o["stroke_width"])
        paint_swatch(self.btn_stroke_color, o["stroke_color"])
        paint_swatch(self.btn_fill_color, o["fill_color"])
        opacity = round(o["fill_opacity"] * 100)
        set_value(self.slider_opacity, opacity)
        if not self.vertical:
            self.lbl_stroke_val.setText(f"{o['stroke_width']}px")
            self.lbl_opacity_val.setText(f"{opacity}%")
        self._show_extra(o)

    def _show_extra(self, o: dict) -> None:
        extra = _extra_field(o["shape_type"])
        for w in (self.lbl_extra, self.slider_extra, self.lbl_extra_val):
            w.setVisible(extra is not None)
        if extra is None:
            return
        field, low, high, suffix, caption = extra
        self.lbl_extra.setText(caption)
        self.slider_extra.setRange(low, high)
        set_value(self.slider_extra, o[field])
        self.lbl_extra_val.setText(f"{o[field]}{suffix}")

    def retranslate_ui(self):
        set_combo_items(self.cbo_mode, [
            tr("tool_options.shapes_stroke_and_fill", "Contorno & Preenchimento"),
            tr("tool_options.shapes_stroke_only", "Apenas Contorno"),
            tr("tool_options.shapes_fill_only", "Apenas Preenchimento"),
        ])
        self.lbl_border.setText(tr("tool_options.border", "Borda:"))
        self.lbl_fill.setText(tr("tool_options.fill", "Fundo:"))
        if self.vertical:
            self.slider_stroke.setPrefix(tr("tool_options.stroke", "Traço:"))
            self.slider_opacity.setPrefix(tr("tool_options.fill_opacity", "Opac. Fundo:"))
        else:
            self.lbl_stroke.setText(tr("tool_options.stroke", "Traço:"))
            self.lbl_opacity.setText(tr("tool_options.opacity", "Opac:"))
        extra = _extra_field(self.options()["shape_type"])
        if extra is not None:
            self.lbl_extra.setText(extra[4])
