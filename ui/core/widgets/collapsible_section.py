"""
CollapsibleSection
──────────────────
Seção com cabeçalho clicável que expande/colapsa o conteúdo.
Independente de tema — usa objectName para estilização via QSS.
"""
from PySide6 import QtWidgets, QtCore, QtGui


class CollapsibleSection(QtWidgets.QWidget):
    def __init__(self, title: str, parent=None, expanded: bool = True):
        super().__init__(parent)
        self._expanded = expanded

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────
        self._header = QtWidgets.QWidget()
        self._header.setObjectName("CollapsHeader")
        self._header.setCursor(QtCore.Qt.PointingHandCursor)
        self._header.setFixedHeight(26)

        hl = QtWidgets.QHBoxLayout(self._header)
        hl.setContentsMargins(6, 0, 6, 0)
        hl.setSpacing(6)

        self._arrow = QtWidgets.QLabel("▾" if expanded else "▸")
        self._arrow.setObjectName("CollapsArrow")
        self._arrow.setFixedWidth(12)

        self._title_lbl = QtWidgets.QLabel(title)
        self._title_lbl.setObjectName("CollapsTitle")

        hl.addWidget(self._arrow)
        hl.addWidget(self._title_lbl)
        hl.addStretch()
        outer.addWidget(self._header)

        # ── Content wrapper ───────────────────────────────────────────
        self._content = QtWidgets.QWidget()
        self._content.setObjectName("CollapsContent")
        self._content_layout = QtWidgets.QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 4, 4, 8)
        self._content_layout.setSpacing(6)
        outer.addWidget(self._content)

        self._content.setVisible(expanded)

        # Click on header
        self._header.mousePressEvent = self._toggle

    def _toggle(self, _event=None):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._arrow.setText("▾" if self._expanded else "▸")

    def add_widget(self, widget: QtWidgets.QWidget):
        self._content_layout.addWidget(widget)

    def add_layout(self, layout: QtWidgets.QLayout):
        self._content_layout.addLayout(layout)

    def set_title(self, title: str):
        self._title_lbl.setText(title)
