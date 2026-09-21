"""
GridMetricCard — Card Métrico Compacto Reutilizável
===================================================
Card métrico compacto para exibição em grid com dot colorido, título,
valor principal, subtítulo explicativo e barra visual opcional.
Suporta tematização dinâmica em tempo real via ThemeManager.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager


class GridMetricCard(QtWidgets.QFrame):
    """Card métrico compacto para exibição em grid com título, valor principal, subtítulo e barra opcional."""

    def __init__(
        self,
        title: str,
        initial_val: str = "0",
        subtitle: str = "",
        tag_color: str = None,
        show_bar: bool = False,
        bar_max: int = 100,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("GridMetricCard")
        if tag_color is None:
            tag_color = ThemeManager.instance().get_color("TELEMETRY_STAGE_KINEMATICS", "#38bdf8")
        self._tag_color = tag_color
        self._show_bar = show_bar
        self._bar_max = bar_max

        lo = QtWidgets.QVBoxLayout(self)
        lo.setContentsMargins(10, 8, 10, 8)
        lo.setSpacing(3)

        # Cabeçalho: Dot colorido + Título
        hdr_lo = QtWidgets.QHBoxLayout()
        hdr_lo.setSpacing(5)
        self.dot = QtWidgets.QLabel("■")
        self.dot.setStyleSheet(f"color: {tag_color}; font-size: 8px;")
        self.lbl_title = QtWidgets.QLabel(title.upper())
        self.lbl_title.setObjectName("CardTitle")
        hdr_lo.addWidget(self.dot)
        hdr_lo.addWidget(self.lbl_title, 1)
        lo.addLayout(hdr_lo)

        # Valor Principal
        self.lbl_val = QtWidgets.QLabel(initial_val)
        self.lbl_val.setObjectName("CardValue")
        lo.addWidget(self.lbl_val)

        # Subtítulo explicativo
        self.lbl_sub = QtWidgets.QLabel(subtitle)
        self.lbl_sub.setObjectName("CardSubtitle")
        lo.addWidget(self.lbl_sub)

        # Barra visual opcional (ex: pressão, velocidade)
        if show_bar:
            self.bar = QtWidgets.QProgressBar()
            self.bar.setRange(0, bar_max)
            self.bar.setValue(0)
            self.bar.setFixedHeight(6)
            self.bar.setTextVisible(False)
            lo.addWidget(self.bar)
        else:
            self.bar = None

        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)

    @property
    def title(self) -> str:
        return self.lbl_title.text()

    @property
    def value(self) -> str:
        return self.lbl_val.text()

    @property
    def subtitle(self) -> str:
        return self.lbl_sub.text()

    def get_info(self) -> tuple[str, str, str]:
        """Retorna (título, valor_principal, subtítulo) do card."""
        return (self.lbl_title.text(), self.lbl_val.text(), self.lbl_sub.text())

    def set_value(
        self,
        val_str: str,
        sub_str: str | None = None,
        bar_val: int | None = None,
        color: str | None = None,
    ) -> None:
        self.lbl_val.setText(val_str)
        if sub_str is not None:
            self.lbl_sub.setText(sub_str)
        if self.bar and bar_val is not None:
            self.bar.setValue(min(self._bar_max, max(0, bar_val)))
        if color:
            self.lbl_val.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold; font-family: monospace;")
        else:
            self.lbl_val.setStyleSheet("")

    def _apply_theme(self, *args) -> None:
        tm = ThemeManager.instance()
        bg = tm.get_color("bg_panel", "#181a20")
        border = tm.get_color("border", "#2a2d36")
        muted = tm.get_color("text_sec", "#9ca3af")
        text = tm.get_color("text_main", "#f3f4f6")
        accent = self._tag_color

        self.setStyleSheet(f"""
            QFrame#GridMetricCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QFrame#GridMetricCard:hover {{
                border-color: {accent};
            }}
            QLabel#CardTitle {{
                color: {muted};
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            QLabel#CardValue {{
                color: {text};
                font-size: 15px;
                font-weight: bold;
                font-family: monospace;
            }}
            QLabel#CardSubtitle {{
                color: {muted};
                font-size: 9px;
            }}
            QProgressBar {{
                background-color: rgba(0, 0, 0, 0.4);
                border: 1px solid {border};
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {accent};
                border-radius: 2px;
            }}
        """)
