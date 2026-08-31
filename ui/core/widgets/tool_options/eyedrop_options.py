"""EyedropOptionsWidget."""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.i18n import tr, I18nManager
from .base import ToolHeaderLabel, ModernOptionCheckBox


class EyedropOptionsWidget(QtWidgets.QWidget):
    """Painel de configurações da ferramenta Conta-Gotas (Fit Compacto)."""

    settingsChanged = QtCore.Signal(dict)
    colorCaptured   = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EyedropOptionsWidget")
        self._current_color = QtGui.QColor(0, 0, 0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.header_lbl = ToolHeaderLabel(tr("tools.eyedropper", "Conta-Gotas"), icon_name="eyedrop")
        layout.addWidget(self.header_lbl)

        row_sample = QtWidgets.QHBoxLayout()
        row_sample.setContentsMargins(0, 0, 0, 0)
        row_sample.setSpacing(4)
        self.lbl_s = QtWidgets.QLabel(f"{tr('tools.sample', 'Amostra')}:")
        self.lbl_s.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.combo_sample = QtWidgets.QComboBox()
        self.combo_sample.addItems([
            tr("tools.sample_1x1", "1x1 Ponto"),
            tr("tools.sample_3x3", "3x3 Média"),
            tr("tools.sample_5x5", "5x5 Média"),
            tr("tools.sample_11x11", "11x11 Média")
        ])
        self.combo_sample.setFixedHeight(22)
        self.combo_sample.setStyleSheet("font-size: 10px; padding: 1px 4px;")
        self.combo_sample.currentIndexChanged.connect(self._emit_changes)
        row_sample.addWidget(self.lbl_s)
        row_sample.addWidget(self.combo_sample, 1)
        layout.addLayout(row_sample)

        self.chk_sample_all = ModernOptionCheckBox(tr("tools.sample_all_layers", "Todas as Camadas"))
        self.chk_sample_all.setToolTip(tr("tools.sample_all_tooltip", "Amostrar todas as camadas mescladas (Merged)"))
        self.chk_sample_all.setChecked(True)
        self.chk_sample_all.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_sample_all)

        self.chk_show_loupe = ModernOptionCheckBox(tr("tools.loupe", "Lupa Dinâmica 4×"))
        self.chk_show_loupe.setToolTip(tr("tools.loupe_tooltip", "Exibir lupa de ampliação 4x no cursor ao clicar/arrastar"))
        self.chk_show_loupe.setChecked(True)
        self.chk_show_loupe.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_show_loupe)

        layout.addSpacing(2)

        self.card_color = QtWidgets.QFrame()
        self.card_color.setFixedHeight(42)
        card_layout = QtWidgets.QHBoxLayout(self.card_color)
        card_layout.setContentsMargins(6, 4, 6, 4)
        card_layout.setSpacing(8)

        self.swatch_preview = QtWidgets.QFrame()
        self.swatch_preview.setFixedSize(28, 28)
        self.swatch_preview.setStyleSheet(
            "background-color: #000000; border-radius: 4px; border: 1px solid rgba(255,255,255,0.25);"
        )
        card_layout.addWidget(self.swatch_preview)

        info_layout = QtWidgets.QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        self.lbl_hex = QtWidgets.QLabel("#000000")
        self.lbl_hex.setStyleSheet("font-size: 11px; font-weight: bold; font-family: monospace;")
        self.lbl_rgb = QtWidgets.QLabel("RGB: 0, 0, 0")
        self.lbl_rgb.setStyleSheet("font-size: 9px; color: #a1a1aa;")

        info_layout.addWidget(self.lbl_hex)
        info_layout.addWidget(self.lbl_rgb)
        card_layout.addLayout(info_layout, 1)

        layout.addWidget(self.card_color)
        layout.addStretch()

    def retranslate_ui(self):
        if hasattr(self, "lbl_s"):
            self.lbl_s.setText(f"{tr('tools.sample', 'Amostra')}:")
        if hasattr(self, "chk_sample_all"):
            self.chk_sample_all.setText(tr("tools.sample_all_layers", "Todas as Camadas"))
            self.chk_sample_all.setToolTip(tr("tools.sample_all_tooltip", "Amostrar todas as camadas mescladas (Merged)"))
        if hasattr(self, "chk_show_loupe"):
            self.chk_show_loupe.setText(tr("tools.loupe", "Lupa Dinâmica 4×"))
            self.chk_show_loupe.setToolTip(tr("tools.loupe_tooltip", "Exibir lupa de ampliação 4x no cursor ao clicar/arrastar"))

    def set_captured_color(self, color: QtGui.QColor):
        self._current_color = color
        hex_str = color.name().upper()
        self.lbl_hex.setText(hex_str)
        self.lbl_rgb.setText(f"RGB: {color.red()}, {color.green()}, {color.blue()}")
        self.swatch_preview.setStyleSheet(
            f"background-color: {hex_str}; border-radius: 4px; border: 1px solid rgba(255,255,255,0.3);"
        )

    def _emit_changes(self):
        sample_map = {0: "1x1 Ponto Único", 1: "3x3 Média", 2: "5x5 Média", 3: "11x11 Média"}
        radius_map = {0: 0, 1: 1, 2: 2, 3: 5}
        idx = self.combo_sample.currentIndex()
        settings = {
            "sample_size": sample_map.get(idx, "1x1 Ponto Único"),
            "sample_radius": radius_map.get(idx, 0),
            "sample_all": self.chk_sample_all.isChecked(),
            "show_loupe": self.chk_show_loupe.isChecked(),
        }
        self.settingsChanged.emit(settings)

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
