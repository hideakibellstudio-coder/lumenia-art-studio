"""ShapesOptionsWidget — página das formas vetoriais no painel de pincel (view do ToolState).

As cores das formas seguem a cor do pincel pela regra `ShapeColorLink`
(ui/core/state); aqui só se mostra e se escolhe outra. Até 2026-09-24 esta
página guardava as próprias cópias das cores, recebia a cor do pincel pelo
painel (`set_active_color`) e republicava o dicionário inteiro ao ser
mostrada, sobrescrevendo o que a barra secundária tinha mudado.
"""

from PySide6 import QtCore, QtWidgets
from .base import ToolHeaderLabel
from .bound_view import ToolOptionsView
from ui.core.widgets.shape_dropdown import ShapeDropdown
from ui.core.widgets.compact_slider import CompactSlider
from ui.infrastructure.i18n import tr
from ui.core.state import ToolState

_DRAW_MODES = ("both", "stroke", "fill")
_SWATCH = "background-color: {}; border: 1px solid rgba(255,255,255,0.4); border-radius: 4px;"


def _extra_field(shape_type: str):
    """(campo nas opções, mínimo, máximo, sufixo, rótulo) do parâmetro extra, ou None."""
    if shape_type == "shape_rect":
        return "corner_radius", 0, 100, "px", f"{tr('shapes.corners', 'Cantos')}:"
    if shape_type == "shape_polygon":
        return "polygon_sides", 3, 16, "", f"{tr('shapes.sides', 'Lados')}:"
    if shape_type == "shape_star":
        return "star_points", 3, 16, "", f"{tr('shapes.points', 'Pontas')}:"
    return None


class ShapesOptionsWidget(ToolOptionsView):
    def __init__(self, tool_state: ToolState, parent=None):
        super().__init__(tool_state, "shapes", parent)
        self.setObjectName("ShapesOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()
        self.bind()

    def _row(self, layout, label: QtWidgets.QLabel, field: QtWidgets.QWidget) -> None:
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(label)
        row.addWidget(field, 1)
        label.setBuddy(field)  # rótulo do controle para o leitor de tela
        layout.addLayout(row)

    def _muted_label(self) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel()
        label.setProperty("muted", "true")
        return label

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(ToolHeaderLabel(tr("tools.shapes", "Formas"), icon_name="shapes"))

        self.lbl_s = self._muted_label()
        self.shape_dropdown = ShapeDropdown(self)
        self.shape_dropdown.shape_changed.connect(lambda sid, _label: self.publish(shape_type=sid))
        self._row(layout, self.lbl_s, self.shape_dropdown)

        self.lbl_m = self._muted_label()
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems(["", "", ""])
        self.combo_mode.setFixedHeight(22)
        self.combo_mode.currentIndexChanged.connect(lambda i: self.publish(draw_mode=_DRAW_MODES[i]))
        self._row(layout, self.lbl_m, self.combo_mode)

        self.lbl_w = self._muted_label()
        self.spin_width = QtWidgets.QSpinBox()
        self.spin_width.setRange(1, 100)
        self.spin_width.setSuffix("px")
        self.spin_width.setFixedHeight(22)
        self.spin_width.valueChanged.connect(lambda v: self.publish(stroke_width=v))
        self._row(layout, self.lbl_w, self.spin_width)

        row_colors = QtWidgets.QHBoxLayout()
        row_colors.setContentsMargins(0, 0, 0, 0)
        row_colors.setSpacing(6)
        self.lbl_c1, self.lbl_c2 = self._muted_label(), self._muted_label()
        self.btn_stroke_col, self.btn_fill_col = QtWidgets.QPushButton(), QtWidgets.QPushButton()
        for button in (self.btn_stroke_col, self.btn_fill_col):
            button.setFixedSize(22, 22)
            button.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_stroke_col.clicked.connect(self._pick_stroke_color)
        self.btn_fill_col.clicked.connect(self._pick_fill_color)
        for w in (self.lbl_c1, self.btn_stroke_col, self.lbl_c2, self.btn_fill_col):
            row_colors.addWidget(w)
        row_colors.addStretch()
        layout.addLayout(row_colors)

        self.slider_fill_opac = CompactSlider("", 0, 100, "%")
        self.slider_fill_opac.valueChanged.connect(self._on_fill_opacity_edited)
        layout.addWidget(self.slider_fill_opac)

        self.lbl_extra = QtWidgets.QLabel()
        self.lbl_extra.setStyleSheet("font-size: 10px;")
        self.spin_extra = QtWidgets.QSpinBox()
        self.spin_extra.setFixedHeight(22)
        self.spin_extra.setStyleSheet("font-size: 10px;")
        self.spin_extra.valueChanged.connect(self._on_extra_edited)
        self._row(layout, self.lbl_extra, self.spin_extra)

        layout.addStretch()

    # ── Edição → estado ───────────────────────────────────────────────────

    def _on_fill_opacity_edited(self, percent: int) -> None:
        fill = self.options()["fill_color"]
        fill.setAlpha(int(percent * 255 / 100))
        self.publish(fill_opacity=percent / 100.0, fill_color=fill)

    def _on_extra_edited(self, value: int) -> None:
        extra = _extra_field(self.options()["shape_type"])
        if extra is not None:
            self.publish(**{extra[0]: value})

    def _pick_stroke_color(self):
        col = QtWidgets.QColorDialog.getColor(self.options()["stroke_color"], self, tr("shapes.stroke_color_title", "Cor da Borda"), QtWidgets.QColorDialog.ShowAlphaChannel)
        if col.isValid():
            self.publish(stroke_color=col)

    def _pick_fill_color(self):
        col = QtWidgets.QColorDialog.getColor(self.options()["fill_color"], self, tr("shapes.fill_color_title", "Cor do Preenchimento"), QtWidgets.QColorDialog.ShowAlphaChannel)
        if col.isValid():
            self.publish(fill_color=col, fill_opacity=col.alphaF())

    # ── Estado → tela ─────────────────────────────────────────────────────

    def show_options(self, o):
        self.shape_dropdown.set_shape(o["shape_type"])  # não emite; também põe o ícone
        self.combo_mode.setCurrentIndex(_DRAW_MODES.index(o["draw_mode"]))
        self.spin_width.setValue(o["stroke_width"])
        self.btn_stroke_col.setStyleSheet(_SWATCH.format(o["stroke_color"].name()))
        self.btn_fill_col.setStyleSheet(_SWATCH.format(o["fill_color"].name()))
        self.slider_fill_opac.setValue(round(o["fill_opacity"] * 100))

        extra = _extra_field(o["shape_type"])
        self.lbl_extra.setVisible(extra is not None)
        self.spin_extra.setVisible(extra is not None)
        if extra is not None:
            field, low, high, suffix, caption = extra
            self.lbl_extra.setText(caption)
            self.spin_extra.setRange(low, high)
            self.spin_extra.setSuffix(suffix)
            self.spin_extra.setValue(o[field])

    def retranslate_ui(self):
        self.lbl_s.setText(f"{tr('shapes.shape_label', 'Forma')}:")
        self.lbl_m.setText(f"{tr('tools.selection_mode', 'Modo')}:")
        for index, (key, fallback) in enumerate((("shapes.mode_both", "Contorno e Fundo"),
                                                 ("shapes.mode_stroke", "Apenas Contorno"),
                                                 ("shapes.mode_fill", "Apenas Fundo"))):
            self.combo_mode.setItemText(index, tr(key, fallback))
        self.lbl_w.setText(f"{tr('shapes.stroke_width', 'Traço')}:")
        self.lbl_c1.setText(f"{tr('shapes.border_color', 'Borda')}:")
        self.lbl_c2.setText(f"{tr('shapes.fill_color', 'Fundo')}:")
        self.slider_fill_opac.setPrefix(f"{tr('shapes.fill_opacity', 'Opac. Fundo')}:")
        extra = _extra_field(self.options()["shape_type"])
        if extra is not None:
            self.lbl_extra.setText(extra[4])
