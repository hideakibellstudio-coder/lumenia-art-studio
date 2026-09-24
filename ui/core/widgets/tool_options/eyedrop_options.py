"""EyedropOptionsWidget — página do conta-gotas no painel de pincel.

View do ToolState ("eyedrop") e do BrushState (a cor do pincel é a última
cor capturada). Até 2026-09-24 o painel repassava a cor à mão
(`set_captured_color`) e o widget publicava o dicionário inteiro a cada clique.
"""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.i18n import tr
from ui.core.state import BrushState, ToolState
from .base import ToolHeaderLabel, ModernOptionCheckBox
from .bound_view import ToolOptionsView

# Índice do combo de amostragem ↔ raio de amostragem em pixels (1x1, 3x3, 5x5, 11x11).
SAMPLE_RADII = (0, 1, 2, 5)


class EyedropOptionsWidget(ToolOptionsView):
    def __init__(self, tool_state: ToolState, brush_state: BrushState, parent=None):
        super().__init__(tool_state, "eyedrop", parent)
        self.setObjectName("EyedropOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        brush_state.colorChanged.connect(self._show_color)
        self._show_color(brush_state.color)
        self.bind()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.header_lbl = ToolHeaderLabel(tr("tools.eyedropper", "Conta-Gotas"), icon_name="eyedrop")
        layout.addWidget(self.header_lbl)

        row_sample = QtWidgets.QHBoxLayout()
        row_sample.setContentsMargins(0, 0, 0, 0)
        row_sample.setSpacing(4)
        self.lbl_s = QtWidgets.QLabel()
        self.lbl_s.setProperty("muted", "true")
        self.combo_sample = QtWidgets.QComboBox()
        self.combo_sample.addItems([
            tr("tools.sample_1x1", "1x1 Ponto"),
            tr("tools.sample_3x3", "3x3 Média"),
            tr("tools.sample_5x5", "5x5 Média"),
            tr("tools.sample_11x11", "11x11 Média")
        ])
        self.combo_sample.setFixedHeight(22)
        self.combo_sample.currentIndexChanged.connect(lambda i: self.publish(sample_radius=SAMPLE_RADII[i]))
        row_sample.addWidget(self.lbl_s)
        row_sample.addWidget(self.combo_sample, 1)
        layout.addLayout(row_sample)

        self.chk_sample_all = ModernOptionCheckBox("")
        self.chk_sample_all.toggled.connect(lambda x: self.publish(sample_all=x))
        layout.addWidget(self.chk_sample_all)

        self.chk_show_loupe = ModernOptionCheckBox("")
        self.chk_show_loupe.toggled.connect(lambda x: self.publish(show_loupe=x))
        layout.addWidget(self.chk_show_loupe)

        layout.addSpacing(2)

        self.card_color = QtWidgets.QFrame()
        self.card_color.setFixedHeight(42)
        card_layout = QtWidgets.QHBoxLayout(self.card_color)
        card_layout.setContentsMargins(6, 4, 6, 4)
        card_layout.setSpacing(8)

        self.swatch_preview = QtWidgets.QFrame()
        self.swatch_preview.setFixedSize(28, 28)
        card_layout.addWidget(self.swatch_preview)

        info_layout = QtWidgets.QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        self.lbl_hex = QtWidgets.QLabel()
        self.lbl_hex.setProperty("heading", "true")
        self.lbl_rgb = QtWidgets.QLabel()
        self.lbl_rgb.setProperty("muted", "true")

        info_layout.addWidget(self.lbl_hex)
        info_layout.addWidget(self.lbl_rgb)
        card_layout.addLayout(info_layout, 1)

        layout.addWidget(self.card_color)
        layout.addStretch()

    def show_options(self, o):
        self.combo_sample.setCurrentIndex(SAMPLE_RADII.index(o["sample_radius"]))
        self.chk_sample_all.setChecked(o["sample_all"])
        self.chk_show_loupe.setChecked(o["show_loupe"])

    def retranslate_ui(self):
        self.lbl_s.setText(f"{tr('tools.sample', 'Amostra')}:")
        self.chk_sample_all.setText(tr("tools.sample_all_layers", "Todas as Camadas"))
        self.chk_sample_all.setToolTip(tr("tools.sample_all_tooltip", "Amostrar todas as camadas mescladas (Merged)"))
        self.chk_show_loupe.setText(tr("tools.loupe", "Lupa Dinâmica 4×"))
        self.chk_show_loupe.setToolTip(tr("tools.loupe_tooltip", "Exibir lupa de ampliação 4x no cursor ao clicar/arrastar"))

    def _show_color(self, color: QtGui.QColor):
        hex_str = color.name().upper()
        self.lbl_hex.setText(hex_str)
        self.lbl_rgb.setText(f"RGB: {color.red()}, {color.green()}, {color.blue()}")
        self.swatch_preview.setStyleSheet(
            f"background-color: {hex_str}; border-radius: 4px; border: 1px solid rgba(255,255,255,0.3);"
        )

    def _apply_theme(self, *_):
        theme = ThemeManager.instance()
        bg_card = theme.get_color("bg_card", "#181825")
        border = theme.get_color("border", "#313244")
        self.card_color.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 6px;
            }}
        """)
