"""
SecondaryToolBar — Barra Secundária de Opções Contextuais da Ferramenta Ativa (Lumenia V2)
==========================================================================================
Barra flutuante compacta em formato de cápsula que se acopla dinamicamente à FloatingToolbar
ou ao topo do canvas, exibindo as opções contextuais imediatas da ferramenta selecionada.
"""

from __future__ import annotations

from typing import Optional, Dict
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon


class SecondaryToolBar(QtWidgets.QDialog):
    """Barra flutuante secundária exibindo opções contextuais da ferramenta ativa."""

    settingsChanged = QtCore.Signal(str, dict)  # tool_id, settings

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("QDialog { background: transparent; border: none; }")

        self._active_tool_id: str = "eyedrop"
        self._current_color: QtGui.QColor = QtGui.QColor(0, 0, 0)
        self._settings_cache: Dict[str, dict] = {
            "eyedrop": {"sample_size": "1x1 Ponto Único", "sample_radius": 0, "sample_all": True, "show_loupe": True},
            "bucket": {"tolerance": 20, "contiguous": True, "sample_all": True},
        }

        self._build_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(lambda _: self._apply_theme())

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        # Container Cápsula
        self.container = QtWidgets.QWidget(self)
        self.container.setObjectName("SecondaryBarContainer")

        shadow = QtWidgets.QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(8)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QtGui.QColor(0, 0, 0, 140))
        self.container.setGraphicsEffect(shadow)

        self.box_layout = QtWidgets.QHBoxLayout(self.container)
        self.box_layout.setContentsMargins(10, 4, 10, 4)
        self.box_layout.setSpacing(8)
        self.box_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Stack de widgets por ferramenta
        self.stacked_widget = QtWidgets.QStackedWidget(self.container)
        self.stacked_widget.setFixedHeight(30)

        # ── 1. Painel Eyedrop ──────────────────────────────────────────────
        self.panel_eyedrop = QtWidgets.QWidget()
        lay_eye = QtWidgets.QHBoxLayout(self.panel_eyedrop)
        lay_eye.setContentsMargins(0, 0, 0, 0)
        lay_eye.setSpacing(6)

        lbl_eye = QtWidgets.QLabel("💧")
        lbl_eye.setStyleSheet("font-size: 14px;")
        lay_eye.addWidget(lbl_eye)

        self.cbo_sample = QtWidgets.QComboBox()
        self.cbo_sample.addItems(["1x1 Ponto", "3x3 Média", "5x5 Média", "11x11 Média"])
        self.cbo_sample.setFixedHeight(24)
        self.cbo_sample.currentIndexChanged.connect(self._on_eyedrop_changed)
        lay_eye.addWidget(self.cbo_sample)

        self.btn_merged = QtWidgets.QToolButton()
        self.btn_merged.setText("Todas Camadas")
        self.btn_merged.setCheckable(True)
        self.btn_merged.setChecked(True)
        self.btn_merged.setFixedHeight(24)
        self.btn_merged.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_merged.toggled.connect(self._on_eyedrop_changed)
        lay_eye.addWidget(self.btn_merged)

        self.swatch = QtWidgets.QLabel()
        self.swatch.setFixedSize(22, 22)
        self.swatch.setStyleSheet("background: #000000; border-radius: 4px; border: 1px solid rgba(255,255,255,0.3);")
        lay_eye.addWidget(self.swatch)

        self.lbl_hex = QtWidgets.QLabel("#000000")
        self.lbl_hex.setStyleSheet("font-size: 11px; font-weight: bold;")
        lay_eye.addWidget(self.lbl_hex)

        self.stacked_widget.addWidget(self.panel_eyedrop)

        # ── 2. Painel Padrão (Placeholder / Vazio para outras) ──────────────
        self.panel_default = QtWidgets.QWidget()
        lay_def = QtWidgets.QHBoxLayout(self.panel_default)
        lay_def.setContentsMargins(0, 0, 0, 0)
        self.lbl_default = QtWidgets.QLabel("Opções da Ferramenta")
        self.lbl_default.setStyleSheet("font-size: 11px; color: #a1a1aa;")
        lay_def.addWidget(self.lbl_default)
        self.stacked_widget.addWidget(self.panel_default)

        self.box_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(self.container)

    def set_tool(self, tool_id: str):
        self._active_tool_id = tool_id
        if tool_id == "eyedrop":
            self.stacked_widget.setCurrentWidget(self.panel_eyedrop)
            self.show()
            self.adjustSize()
        else:
            # Esconde ou mostra default
            self.hide()

    def set_captured_color(self, color: QtGui.QColor):
        self._current_color = color
        hex_str = color.name().upper()
        self.swatch.setStyleSheet(f"background: {hex_str}; border-radius: 4px; border: 1px solid rgba(255,255,255,0.3);")
        self.lbl_hex.setText(hex_str)

    def _on_eyedrop_changed(self):
        radius_map = {0: 0, 1: 1, 2: 2, 3: 5}
        idx = self.cbo_sample.currentIndex()
        settings = {
            "sample_size": self.cbo_sample.currentText(),
            "sample_radius": radius_map.get(idx, 0),
            "sample_all": self.btn_merged.isChecked(),
            "show_loupe": True,
        }
        self._settings_cache["eyedrop"] = settings
        self.settingsChanged.emit("eyedrop", settings)

    def _apply_theme(self):
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel") or "#1f1f23"
        border = theme.get_color("border") or "#3f3f46"
        text_main = theme.get_color("text_main") or "#ffffff"
        accent = theme.get_color("accent") or "#ff5252"

        self.container.setStyleSheet(f"""
            #SecondaryBarContainer {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QLabel {{
                color: {text_main};
            }}
            QComboBox {{
                background-color: rgba(255,255,255,0.08);
                color: {text_main};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 11px;
            }}
            QToolButton {{
                background-color: rgba(255,255,255,0.08);
                color: {text_main};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
            }}
            QToolButton:checked {{
                background-color: {accent};
                color: #ffffff;
                border: 1px solid {border};
            }}
        """)
