"""
PillHandle — Indicador de Reativação de Sidebar
================================================
Widget flutuante filho do workspace_area que aparece quando a SidebarWidget
recolhe totalmente para largura 0.

Comportamento (fiel ao legado):
- Horizontal (36×8px), posicionada no canto superior da área da sidebar (y=16px)
- Hover → dispara expand_timer do AdvancedDockSystem após delay configurável
- Leave → cancela expand_timer
- Drop Shadow vertical para contraste sobre o canvas

REGRA WGPU: Este widget é sempre filho do workspace_area (QWidget comum),
JAMAIS filho do CanvasWidget (HWND WGPU separado).
"""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager


class PillHandle(QtWidgets.QWidget):
    """Pílula de reativação da sidebar — filho do workspace_area.

    Horizontal (36×8px), posicionada no canto superior da região da sidebar,
    a y=16px fixo — idêntico ao comportamento do sistema legado Readback.
    """

    hovered = QtCore.Signal()   # Dispara quando hover entra
    left    = QtCore.Signal()   # Dispara quando mouse sai

    _PILL_W = 36   # Largura: horizontal (igual ao legado: 36px)
    _PILL_H = 8    # Altura:  fina       (igual ao legado:  8px)
    _PILL_Y = 16   # Y fixo no canto superior (igual ao legado: y=16)

    def __init__(self, side: str = "left", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.side = side

        self.setFixedSize(self._PILL_W, self._PILL_H)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.hide()

        # Sombra de profundidade — vertical (offset Y para cápsula horizontal)
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(6)
        shadow.setColor(QtGui.QColor(0, 0, 0, 120))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        # Usa a cor de texto principal com alpha reduzido — idêntico ao legado
        # "rgba(200, 200, 200, 0.6)" normal, branco no hover
        text = theme.get_color("text_muted", "#a0a0b0")
        self.setStyleSheet(f"""
            PillHandle {{
                background-color: rgba(200, 200, 200, 0.55);
                border-radius: 3px;
            }}
            PillHandle:hover {{
                background-color: rgba(255, 255, 255, 0.95);
            }}
        """)

    # ── Hover ─────────────────────────────────────────────────────────────

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self.hovered.emit()
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self.left.emit()
        super().leaveEvent(event)

    # ── Posicionamento ────────────────────────────────────────────────────

    def update_position(self, sidebar_slot_x: int, sidebar_slot_w: int = 54) -> None:
        """Posiciona a pílula estritamente no canto superior da faixa da sidebar (54px).

        Quando o usuário passa o mouse sobre a pílula (ex: x=9..45 na esquerda ou
        x=W-45..W-9 na direita), a sidebar expande sobre a própria área onde o mouse
        já se encontra. Assim, o enterEvent da sidebar dispara automaticamente e
        assume o controle de hover. Quando o mouse sai da sidebar, o leaveEvent a recolhe.
        """
        center_x = sidebar_slot_x + max(0, (sidebar_slot_w - self._PILL_W) // 2)
        self.move(center_x, self._PILL_Y)
        self.raise_()

