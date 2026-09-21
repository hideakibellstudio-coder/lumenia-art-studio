"""ShapesOptionsWidget."""

from PySide6 import QtCore, QtGui, QtWidgets
from .base import ToolHeaderLabel
from ui.core.widgets.shape_dropdown import ShapeDropdown, get_shape_label
from ui.core.widgets.compact_slider import CompactSlider
from ui.core.i18n import tr, I18nManager
from ui.core.tool_settings import normalize_tool_settings


class ShapesOptionsWidget(QtWidgets.QWidget):
    """Painel de configurações das Formas Vetoriais no Painel de Ferramentas."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ShapesOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._stroke_color = QtGui.QColor(0, 0, 0, 255)
        self._fill_color = QtGui.QColor(0, 0, 0, 255)
        self._build_ui()
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel(tr("tools.shapes", "Formas"), icon_name="shapes"))

        # 1. Tipo de Forma (Grid Dropdown Popover)
        row_shape = QtWidgets.QHBoxLayout()
        row_shape.setContentsMargins(0, 0, 0, 0)
        row_shape.setSpacing(4)
        self.lbl_s = QtWidgets.QLabel(f"{tr('shapes.shape_label', 'Forma')}:")
        self.lbl_s.setProperty("muted", "true")
        self.shape_dropdown = ShapeDropdown(self)
        self.shape_dropdown.set_shape("shape_line", get_shape_label("shape_line"))
        self.shape_dropdown.shape_changed.connect(self._on_shape_dropdown_changed)
        row_shape.addWidget(self.lbl_s)
        row_shape.addWidget(self.shape_dropdown, 1)
        layout.addLayout(row_shape)

        # Modo (Ambos / Contorno / Preenchimento)
        row_mode = QtWidgets.QHBoxLayout()
        row_mode.setContentsMargins(0, 0, 0, 0)
        row_mode.setSpacing(4)
        self.lbl_m = QtWidgets.QLabel(f"{tr('tools.selection_mode', 'Modo')}:")
        self.lbl_m.setProperty("muted", "true")
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems([
            tr("shapes.mode_both", "Contorno e Fundo"),
            tr("shapes.mode_stroke", "Apenas Contorno"),
            tr("shapes.mode_fill", "Apenas Fundo")
        ])
        self.combo_mode.setFixedHeight(22)
        self.combo_mode.currentIndexChanged.connect(self._emit_changes)
        row_mode.addWidget(self.lbl_m)
        row_mode.addWidget(self.combo_mode, 1)
        layout.addLayout(row_mode)

        # Espessura do Traço
        row_stroke = QtWidgets.QHBoxLayout()
        row_stroke.setContentsMargins(0, 0, 0, 0)
        row_stroke.setSpacing(4)
        self.lbl_w = QtWidgets.QLabel(f"{tr('shapes.stroke_width', 'Traço')}:")
        self.lbl_w.setProperty("muted", "true")
        self.spin_width = QtWidgets.QSpinBox()
        self.spin_width.setRange(1, 100)
        self.spin_width.setValue(4)
        self.spin_width.setSuffix("px")
        self.spin_width.setFixedHeight(22)
        self.spin_width.valueChanged.connect(self._emit_changes)
        row_stroke.addWidget(self.lbl_w)
        row_stroke.addWidget(self.spin_width, 1)
        layout.addLayout(row_stroke)

        # Cores (Contorno e Preenchimento)
        row_colors = QtWidgets.QHBoxLayout()
        row_colors.setContentsMargins(0, 0, 0, 0)
        row_colors.setSpacing(6)

        self.lbl_c1 = QtWidgets.QLabel(f"{tr('shapes.border_color', 'Borda')}:")
        self.lbl_c1.setProperty("muted", "true")
        self.btn_stroke_col = QtWidgets.QPushButton()
        self.btn_stroke_col.setFixedSize(22, 22)
        self.btn_stroke_col.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_stroke_col.clicked.connect(self._pick_stroke_color)

        self.lbl_c2 = QtWidgets.QLabel(f"{tr('shapes.fill_color', 'Fundo')}:")
        self.lbl_c2.setProperty("muted", "true")
        self.btn_fill_col = QtWidgets.QPushButton()
        self.btn_fill_col.setFixedSize(22, 22)
        self.btn_fill_col.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_fill_col.clicked.connect(self._pick_fill_color)

        self._update_color_buttons()

        row_colors.addWidget(self.lbl_c1)
        row_colors.addWidget(self.btn_stroke_col)
        row_colors.addWidget(self.lbl_c2)
        row_colors.addWidget(self.btn_fill_col)
        row_colors.addStretch()
        layout.addLayout(row_colors)

        # Opacidade do Preenchimento (0..100%, padrão 100% sólido)
        self.slider_fill_opac = CompactSlider(f"{tr('shapes.fill_opacity', 'Opac. Fundo')}:", 0, 100, "%")
        self.slider_fill_opac.setValue(100)
        self.slider_fill_opac.valueChanged.connect(self._on_fill_opac_changed)
        layout.addWidget(self.slider_fill_opac)

        # Controle dinâmico (Raio dos cantos / Lados / Pontas)
        self.row_extra = QtWidgets.QHBoxLayout()
        self.row_extra.setContentsMargins(0, 0, 0, 0)
        self.row_extra.setSpacing(4)
        self.lbl_extra = QtWidgets.QLabel(f"{tr('shapes.corners', 'Cantos')}:")
        self.lbl_extra.setStyleSheet("font-size: 10px;")
        self.spin_extra = QtWidgets.QSpinBox()
        self.spin_extra.setRange(0, 100)
        self.spin_extra.setValue(0)
        self.spin_extra.setSuffix("px")
        self.spin_extra.setFixedHeight(22)
        self.spin_extra.setStyleSheet("font-size: 10px;")
        self.spin_extra.valueChanged.connect(self._emit_changes)
        self.row_extra.addWidget(self.lbl_extra)
        self.row_extra.addWidget(self.spin_extra, 1)
        layout.addLayout(self.row_extra)

        # Padrão inicial: Linha Reta (esconde controles de cantos/lados)
        self.lbl_extra.hide()
        self.spin_extra.hide()

        layout.addStretch()

    def retranslate_ui(self):
        if hasattr(self, "lbl_s"):
            self.lbl_s.setText(f"{tr('shapes.shape_label', 'Forma')}:")
        if hasattr(self, "lbl_m"):
            self.lbl_m.setText(f"{tr('tools.selection_mode', 'Modo')}:")
        if hasattr(self, "lbl_w"):
            self.lbl_w.setText(f"{tr('shapes.stroke_width', 'Traço')}:")
        if hasattr(self, "lbl_c1"):
            self.lbl_c1.setText(f"{tr('shapes.border_color', 'Borda')}:")
        if hasattr(self, "lbl_c2"):
            self.lbl_c2.setText(f"{tr('shapes.fill_color', 'Fundo')}:")
        if hasattr(self, "slider_fill_opac"):
            self.slider_fill_opac.setPrefix(f"{tr('shapes.fill_opacity', 'Opac. Fundo')}:")

    def _update_color_buttons(self):
        self.btn_stroke_col.setStyleSheet(f"background-color: {self._stroke_color.name()}; border: 1px solid rgba(255,255,255,0.4); border-radius: 4px;")
        self.btn_fill_col.setStyleSheet(f"background-color: {self._fill_color.name()}; border: 1px solid rgba(255,255,255,0.4); border-radius: 4px;")

    def _on_fill_opac_changed(self, val: int):
        alpha = int(val * 255 / 100)
        self._fill_color.setAlpha(alpha)
        self._emit_changes()

    def _pick_stroke_color(self):
        col = QtWidgets.QColorDialog.getColor(self._stroke_color, self, tr("shapes.stroke_color_title", "Cor da Borda"), QtWidgets.QColorDialog.ShowAlphaChannel)
        if col.isValid():
            self._stroke_color = col
            self._update_color_buttons()
            self._emit_changes()

    def _pick_fill_color(self):
        col = QtWidgets.QColorDialog.getColor(self._fill_color, self, tr("shapes.fill_color_title", "Cor do Preenchimento"), QtWidgets.QColorDialog.ShowAlphaChannel)
        if col.isValid():
            self._fill_color = col
            self.slider_fill_opac.blockSignals(True)
            self.slider_fill_opac.setValue(int(col.alphaF() * 100))
            self.slider_fill_opac.blockSignals(False)
            self._update_color_buttons()
            self._emit_changes()

    def _on_shape_dropdown_changed(self, shape_id: str, label: str):
        if shape_id == "shape_rect":
            self.lbl_extra.setText(f"{tr('shapes.corners', 'Cantos')}:")
            self.spin_extra.setRange(0, 100)
            self.spin_extra.setSuffix("px")
            self.spin_extra.setValue(0)
            self.lbl_extra.show()
            self.spin_extra.show()
        elif shape_id in ("shape_line", "shape_ellipse"):
            self.lbl_extra.hide()
            self.spin_extra.hide()
        elif shape_id == "shape_polygon":
            self.lbl_extra.setText(f"{tr('shapes.sides', 'Lados')}:")
            self.spin_extra.setRange(3, 16)
            self.spin_extra.setSuffix("")
            self.spin_extra.setValue(5)
            self.lbl_extra.show()
            self.spin_extra.show()
        elif shape_id == "shape_star":
            self.lbl_extra.setText(f"{tr('shapes.points', 'Pontas')}:")
            self.spin_extra.setRange(3, 16)
            self.spin_extra.setSuffix("")
            self.spin_extra.setValue(5)
            self.lbl_extra.show()
            self.spin_extra.show()
        self._emit_changes()

    def set_active_shape_type(self, shape_id: str):
        self.shape_dropdown.set_shape(shape_id)
        self._on_shape_dropdown_changed(shape_id, self.shape_dropdown.shape_label())

    def set_active_color(self, color: QtGui.QColor):
        self._stroke_color = QtGui.QColor(color)
        opac_val = self.slider_fill_opac.value() if hasattr(self, "slider_fill_opac") else 100
        alpha = int(opac_val * 255 / 100)
        self._fill_color = QtGui.QColor(color.red(), color.green(), color.blue(), alpha)
        self._update_color_buttons()
        self._emit_changes()

    def _emit_changes(self):
        draw_modes = ["both", "stroke", "fill"]
        st = self.shape_dropdown.shape_id()
        dm = draw_modes[self.combo_mode.currentIndex()]
        sw = self.spin_width.value()
        fill_opac = (self.slider_fill_opac.value() / 100.0) if hasattr(self, "slider_fill_opac") else 1.0

        cfg = normalize_tool_settings("shapes", {
            "shape_type": st,
            "draw_mode": dm,
            "stroke_width": sw,
            "stroke_color": self._stroke_color,
            "fill_color": self._fill_color,
            "fill_opacity": fill_opac,
        })
        if st == "shape_rect":
            cfg["corner_radius"] = self.spin_extra.value()
        elif st == "shape_polygon":
            cfg["polygon_sides"] = self.spin_extra.value()
        elif st == "shape_star":
            cfg["star_points"] = self.spin_extra.value()

        self.settingsChanged.emit(cfg)
