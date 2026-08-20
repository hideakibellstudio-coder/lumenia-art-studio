"""
ui.core.widgets.tool_options_widgets — Widgets de Configurações Específicas por Ferramenta
==========================================================================================
Contém os painéis de propriedades específicos para:
  - Conta-Gotas (Eyedropper)
  - Balde de Tinta (Bucket Fill)
  - Varinha Mágica (Magic Wand)
  - Transformações (Transform)
  - Ferramentas de Seleção (Rect, Ellipse, Lasso)
"""

from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon


class ToolHeaderLabel(QtWidgets.QWidget):
    """Header compacto com ícone vetorial SVG para painéis de ferramentas."""

    def __init__(self, text: str, icon_name: str = "", parent=None):
        super().__init__(parent)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 1, 0, 2)
        lay.setSpacing(4)

        if icon_name:
            icon_lbl = QtWidgets.QLabel(self)
            icon_lbl.setFixedSize(14, 14)
            icon = get_icon(icon_name, color="#ff5252")
            if not icon.isNull():
                icon_lbl.setPixmap(icon.pixmap(14, 14))
            lay.addWidget(icon_lbl)

        lbl = QtWidgets.QLabel(text.upper(), self)
        lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #ff5252;")
        lay.addWidget(lbl)
        lay.addStretch()


class ModernOptionCheckBox(QtWidgets.QCheckBox):
    """Checkbox ultra-compacto para o painel de opções de ferramentas."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setStyleSheet("font-size: 10px; spacing: 4px; padding: 1px 0px;")


# ── 1. OPÇÕES DO CONTA-GOTAS (EYEDROPPER) ────────────────────────────────────

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

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Header com ícone vetorial
        layout.addWidget(ToolHeaderLabel("Conta-Gotas", icon_name="eyedrop"))

        # Tamanho da Amostra
        row_sample = QtWidgets.QHBoxLayout()
        row_sample.setContentsMargins(0, 0, 0, 0)
        row_sample.setSpacing(4)
        lbl_s = QtWidgets.QLabel("Amostra:")
        lbl_s.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.combo_sample = QtWidgets.QComboBox()
        self.combo_sample.addItems(["1x1 Ponto", "3x3 Média", "5x5 Média", "11x11 Média"])
        self.combo_sample.setFixedHeight(22)
        self.combo_sample.setStyleSheet("font-size: 10px; padding: 1px 4px;")
        self.combo_sample.currentIndexChanged.connect(self._emit_changes)
        row_sample.addWidget(lbl_s)
        row_sample.addWidget(self.combo_sample, 1)
        layout.addLayout(row_sample)

        # Checkboxes Compactos
        self.chk_sample_all = ModernOptionCheckBox("Todas as Camadas")
        self.chk_sample_all.setToolTip("Amostrar todas as camadas mescladas (Merged)")
        self.chk_sample_all.setChecked(True)
        self.chk_sample_all.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_sample_all)

        self.chk_show_loupe = ModernOptionCheckBox("Lupa Dinâmica 4×")
        self.chk_show_loupe.setToolTip("Exibir lupa de ampliação 4x no cursor ao clicar/arrastar")
        self.chk_show_loupe.setChecked(True)
        self.chk_show_loupe.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_show_loupe)

        layout.addSpacing(2)

        # Card de Amostra da Cor Capturada (Compacto)
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
        info_layout.setSpacing(0)
        info_layout.setAlignment(QtCore.Qt.AlignVCenter)
        self.lbl_hex = QtWidgets.QLabel("HEX: #000000")
        self.lbl_hex.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.lbl_rgb = QtWidgets.QLabel("RGB: 0, 0, 0")
        self.lbl_rgb.setStyleSheet("font-size: 9px; color: #888888;")
        info_layout.addWidget(self.lbl_hex)
        info_layout.addWidget(self.lbl_rgb)
        card_layout.addLayout(info_layout, 1)

        layout.addWidget(self.card_color)
        layout.addStretch()

    def set_captured_color(self, color: QtGui.QColor):
        self._current_color = color
        hex_str = color.name().upper()
        self.swatch_preview.setStyleSheet(
            f"background-color: {hex_str}; border-radius: 4px; border: 1px solid rgba(255,255,255,0.3);"
        )
        self.lbl_hex.setText(f"HEX: {hex_str}")
        self.lbl_rgb.setText(f"RGB: {color.red()}, {color.green()}, {color.blue()}")

    def get_settings(self) -> dict:
        radius_map = {0: 0, 1: 1, 2: 2, 3: 5}
        idx = self.combo_sample.currentIndex()
        return {
            "sample_size": self.combo_sample.currentText(),
            "sample_radius": radius_map.get(idx, 0),
            "sample_all": self.chk_sample_all.isChecked(),
            "show_loupe": self.chk_show_loupe.isChecked(),
        }

    def _emit_changes(self):
        self.settingsChanged.emit(self.get_settings())

    def _apply_theme(self):
        is_dark = getattr(ThemeManager.instance(), "is_dark", True)
        bg_card = "#18181b" if is_dark else "#f4f4f5"
        border = "#27272a" if is_dark else "#e4e4e7"
        self.card_color.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 6px;
            }}
        """)


# ── 2. OPÇÕES DO BALDE DE TINTA (BUCKET FILL) ────────────────────────────────

class BucketOptionsWidget(QtWidgets.QWidget):
    """Painel de configurações da ferramenta Balde de Tinta (Fit Compacto e Rico)."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BucketOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel("Balde de Tinta", icon_name="bucket"))

        # 1. Tolerância (0..100%)
        tol_layout = QtWidgets.QHBoxLayout()
        tol_layout.setContentsMargins(0, 0, 0, 0)
        tol_layout.setSpacing(4)
        lbl_t = QtWidgets.QLabel("Tol:")
        lbl_t.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.slider_tol = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_tol.setRange(0, 100)
        self.slider_tol.setValue(20)
        self.slider_tol.setFixedHeight(18)
        self.lbl_tol_val = QtWidgets.QLabel("20%")
        self.lbl_tol_val.setFixedWidth(28)
        self.lbl_tol_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_tol_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_tol.valueChanged.connect(lambda v: self.lbl_tol_val.setText(f"{v}%"))
        self.slider_tol.valueChanged.connect(self._emit_changes)

        tol_layout.addWidget(lbl_t)
        tol_layout.addWidget(self.slider_tol, 1)
        tol_layout.addWidget(self.lbl_tol_val)
        layout.addLayout(tol_layout)

        # 2. Expansão / Sangria (-10..+10 px)
        exp_layout = QtWidgets.QHBoxLayout()
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.setSpacing(4)
        lbl_e = QtWidgets.QLabel("Exp:")
        lbl_e.setToolTip("Expande o preenchimento sob o traço para evitar halos e linhas brancas")
        lbl_e.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.slider_exp = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_exp.setRange(-10, 10)
        self.slider_exp.setValue(1)
        self.slider_exp.setFixedHeight(18)
        self.lbl_exp_val = QtWidgets.QLabel("+1px")
        self.lbl_exp_val.setFixedWidth(28)
        self.lbl_exp_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_exp_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_exp.valueChanged.connect(lambda v: self.lbl_exp_val.setText(f"{v:+d}px" if v != 0 else "0px"))
        self.slider_exp.valueChanged.connect(self._emit_changes)

        exp_layout.addWidget(lbl_e)
        exp_layout.addWidget(self.slider_exp, 1)
        exp_layout.addWidget(self.lbl_exp_val)
        layout.addLayout(exp_layout)

        # 3. Gap Closing / Fechamento de Frestas (0..5 px)
        gap_layout = QtWidgets.QHBoxLayout()
        gap_layout.setContentsMargins(0, 0, 0, 0)
        gap_layout.setSpacing(4)
        lbl_g = QtWidgets.QLabel("Gap:")
        lbl_g.setToolTip("Fecha furos e aberturas no traço para evitar que a tinta vase para fora")
        lbl_g.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.slider_gap = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_gap.setRange(0, 5)
        self.slider_gap.setValue(0)
        self.slider_gap.setFixedHeight(18)
        self.lbl_gap_val = QtWidgets.QLabel("0px")
        self.lbl_gap_val.setFixedWidth(28)
        self.lbl_gap_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_gap_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_gap.valueChanged.connect(lambda v: self.lbl_gap_val.setText(f"{v}px"))
        self.slider_gap.valueChanged.connect(self._emit_changes)

        gap_layout.addWidget(lbl_g)
        gap_layout.addWidget(self.slider_gap, 1)
        gap_layout.addWidget(self.lbl_gap_val)
        layout.addLayout(gap_layout)

        layout.addSpacing(2)

        # 4. Checkboxes Compactos
        self.chk_contiguous = ModernOptionCheckBox("Contíguo (Conectado)")
        self.chk_contiguous.setChecked(True)
        self.chk_contiguous.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_contiguous)

        self.chk_aa = ModernOptionCheckBox("Anti-Aliasing Suave")
        self.chk_aa.setChecked(True)
        self.chk_aa.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_aa)

        self.chk_sample_all = ModernOptionCheckBox("Todas as Camadas")
        self.chk_sample_all.setToolTip("Preencher considerando a imagem mesclada ou apenas a camada atual")
        self.chk_sample_all.setChecked(True)
        self.chk_sample_all.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_sample_all)

        layout.addStretch()

    def get_settings(self) -> dict:
        return {
            "tolerance": self.slider_tol.value(),
            "expand_px": self.slider_exp.value(),
            "gap_closing_px": self.slider_gap.value(),
            "contiguous": self.chk_contiguous.isChecked(),
            "aa": self.chk_aa.isChecked(),
            "sample_all": self.chk_sample_all.isChecked(),
        }

    def _emit_changes(self):
        self.settingsChanged.emit(self.get_settings())


# ── 3. OPÇÕES DA VARINHA MÁGICA (MAGIC WAND) ─────────────────────────────────

class WandOptionsWidget(QtWidgets.QWidget):
    """Painel de configurações da ferramenta Varinha Mágica (Fit Compacto)."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WandOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel("Varinha Mágica", icon_name="wand"))

        tol_layout = QtWidgets.QHBoxLayout()
        tol_layout.setContentsMargins(0, 0, 0, 0)
        tol_layout.setSpacing(4)
        lbl_t = QtWidgets.QLabel("Tol:")
        lbl_t.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.slider_tol = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_tol.setRange(0, 100)
        self.slider_tol.setValue(32)
        self.slider_tol.setFixedHeight(18)
        self.lbl_tol_val = QtWidgets.QLabel("32%")
        self.lbl_tol_val.setFixedWidth(28)
        self.lbl_tol_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_tol_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_tol.valueChanged.connect(lambda v: self.lbl_tol_val.setText(f"{v}%"))
        self.slider_tol.valueChanged.connect(self._emit_changes)

        tol_layout.addWidget(lbl_t)
        tol_layout.addWidget(self.slider_tol, 1)
        tol_layout.addWidget(self.lbl_tol_val)
        layout.addLayout(tol_layout)

        self.chk_contiguous = ModernOptionCheckBox("Contíguo")
        self.chk_contiguous.setChecked(True)
        self.chk_contiguous.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_contiguous)

        self.chk_sample_all = ModernOptionCheckBox("Todas as Camadas")
        self.chk_sample_all.setChecked(True)
        self.chk_sample_all.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_sample_all)

        layout.addStretch()

    def get_settings(self) -> dict:
        return {
            "tolerance": self.slider_tol.value(),
            "contiguous": self.chk_contiguous.isChecked(),
            "sample_all": self.chk_sample_all.isChecked(),
        }

    def _emit_changes(self):
        self.settingsChanged.emit(self.get_settings())


# ── 4. OPÇÕES DE TRANSFORMAÇÃO (TRANSFORM) ───────────────────────────────────

class TransformOptionsWidget(QtWidgets.QWidget):
    """Painel de configurações da ferramenta Transformação (Fit Compacto)."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TransformOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel("Transformar", icon_name="transform"))

        row_mode = QtWidgets.QHBoxLayout()
        row_mode.setContentsMargins(0, 0, 0, 0)
        row_mode.setSpacing(4)
        lbl_m = QtWidgets.QLabel("Modo:")
        lbl_m.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems(["Livre", "Proporcional", "Distorcer"])
        self.combo_mode.setFixedHeight(22)
        self.combo_mode.setStyleSheet("font-size: 10px; padding: 1px 4px;")
        row_mode.addWidget(lbl_m)
        row_mode.addWidget(self.combo_mode, 1)
        layout.addLayout(row_mode)

        self.chk_bicubic = ModernOptionCheckBox("Interpolação Bicúbica")
        self.chk_bicubic.setChecked(True)
        layout.addWidget(self.chk_bicubic)

        layout.addStretch()


# ── 5. OPÇÕES DE SELEÇÃO (SELECTION) ─────────────────────────────────────────

class SelectionOptionsWidget(QtWidgets.QWidget):
    """Painel de configurações das ferramentas de Seleção (Fit Compacto)."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SelectionOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel("Seleção", icon_name="select_rect"))

        row_mode = QtWidgets.QHBoxLayout()
        row_mode.setContentsMargins(0, 0, 0, 0)
        row_mode.setSpacing(4)
        lbl_m = QtWidgets.QLabel("Modo:")
        lbl_m.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems(["Nova", "Adicionar (+)", "Subtrair (-)", "Interseção (∩)"])
        self.combo_mode.setFixedHeight(22)
        self.combo_mode.setStyleSheet("font-size: 10px; padding: 1px 4px;")
        row_mode.addWidget(lbl_m)
        row_mode.addWidget(self.combo_mode, 1)
        layout.addLayout(row_mode)

        self.chk_aa = ModernOptionCheckBox("Anti-Aliasing")
        self.chk_aa.setChecked(True)
        layout.addWidget(self.chk_aa)

        layout.addStretch()
