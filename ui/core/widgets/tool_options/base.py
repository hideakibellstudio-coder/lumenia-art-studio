"""Base controls for tool options widgets."""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.icons import get_icon
from ui.core.theme.manager import ThemeManager


class ToolHeaderLabel(QtWidgets.QWidget):
    """Header compacto com ícone vetorial SVG para painéis de ferramentas.

    A cor do ícone e do texto segue o token 'accent' do ThemeManager e
    se atualiza automaticamente ao trocar de tema.
    """

    def __init__(self, text: str, icon_name: str = "", parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._text = text.upper()
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 1, 0, 2)
        lay.setSpacing(4)

        self._icon_lbl: QtWidgets.QLabel | None = None
        if icon_name:
            self._icon_lbl = QtWidgets.QLabel(self)
            self._icon_lbl.setFixedSize(14, 14)
            lay.addWidget(self._icon_lbl)

        self._lbl = QtWidgets.QLabel(self._text, self)
        self._lbl.setStyleSheet("font-size: 10px; font-weight: bold;")
        lay.addWidget(self._lbl)
        lay.addStretch()

        ThemeManager.instance().themeChanged.connect(self._apply_accent)
        self._apply_accent()

    def _apply_accent(self, *_):
        accent = ThemeManager.instance().get_color("accent", "#6366f1")
        self._lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {accent};")
        if self._icon_lbl and self._icon_name:
            icon = get_icon(self._icon_name, color=accent)
            if not icon.isNull():
                self._icon_lbl.setPixmap(icon.pixmap(14, 14))


class ModernOptionCheckBox(QtWidgets.QCheckBox):
    """Checkbox ultra-compacto para o painel de opções de ferramentas.

    A aparência visual (indicator) é controlada pelo QSS global do ThemeManager.
    Não são necessárias cores hardcoded aqui.
    """

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setStyleSheet("font-size: 10px; spacing: 4px; padding: 1px 0px;")
