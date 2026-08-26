"""Base controls for tool options widgets."""

from PySide6 import QtCore, QtGui, QtWidgets
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


class ModernOptionSlider(QtWidgets.QWidget):
    """Slider horizontal compacto com label e indicador de valor para opções de ferramentas."""

    valueChanged = QtCore.Signal(int)

    def __init__(self, label: str, min_val: int, max_val: int, suffix: str = "", parent=None):
        super().__init__(parent)
        self._suffix = suffix
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(max_val)
        self.slider.setFixedHeight(18)

        self.lbl_val = QtWidgets.QLabel(f"{max_val}{suffix}")
        self.lbl_val.setFixedWidth(32)
        self.lbl_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_val.setStyleSheet("font-size: 10px; font-weight: bold;")

        self.slider.valueChanged.connect(self._on_change)

        layout.addWidget(lbl)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.lbl_val)

    def _on_change(self, val: int):
        self.lbl_val.setText(f"{val}{self._suffix}")
        self.valueChanged.emit(val)

    def setValue(self, val: int):
        self.slider.setValue(val)
        self.lbl_val.setText(f"{val}{self._suffix}")

    def value(self) -> int:
        return self.slider.value()
