"""DrawerContentContainer component for Workspace Dock System."""

from typing import Dict, Set
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from .drawer_header import DrawerHeader
from .dock_animator import DockAnimator


class DrawerContentContainer(QtWidgets.QWidget):
    """Contêiner físico do conteúdo da gaveta com suporte a empilhamento."""

    def __init__(self, side: str = "left", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.side = side
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = DrawerHeader("", side=side, parent=self)
        layout.addWidget(self.header)

        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.scroll_content = QtWidgets.QWidget()
        self.scroll_content.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.scroll_content.setMaximumWidth(DockAnimator.DRAWER_WIDTH)
        self.panels_layout   = QtWidgets.QVBoxLayout(self.scroll_content)
        self.panels_layout.setContentsMargins(0, 0, 0, 0)
        self.panels_layout.setSpacing(0)

        self.spacer = QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.spacer_added = True
        self.panels_layout.addItem(self.spacer)

        if self.scroll_area.viewport():
            self.scroll_area.viewport().setAttribute(QtCore.Qt.WA_StyledBackground, True)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

        self._panels: Dict[str, QtWidgets.QWidget] = {}

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()
        self.ensurePolished()

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        border   = theme.get_color("border",   "#2e2e38")

        c = QtGui.QColor(bg_panel)
        for w in (self, self.scroll_area, self.scroll_area.viewport(), self.scroll_content):
            if w:
                p = w.palette()
                p.setColor(QtGui.QPalette.Window, c)
                p.setColor(QtGui.QPalette.Base, c)
                w.setPalette(p)

        border_side = "border-right" if self.side == "left" else "border-left"
        self.setStyleSheet(f"""
            DrawerContentContainer {{
                background-color: {bg_panel};
                {border_side}: 1px solid {border};
            }}
            QScrollArea, QScrollArea > QWidget > QWidget {{
                background-color: {bg_panel};
                border: none;
            }}
        """)

    def add_panel_widget(self, panel_id: str, title: str, widget: QtWidgets.QWidget) -> None:
        if panel_id in self._panels:
            return
        self._panels[panel_id] = widget
        insert_at = max(0, self.panels_layout.count() - (1 if self.spacer_added else 0))
        self.panels_layout.insertWidget(insert_at, widget)
        widget.hide()

    def remove_panel_widget(self, panel_id: str) -> None:
        widget = self._panels.pop(panel_id, None)
        if widget:
            try:
                self.panels_layout.removeWidget(widget)
                widget.deleteLater()
            except RuntimeError:
                pass

    def reorder_panel(self, panel_id: str, new_index: int) -> None:
        """Reposiciona o widget de um painel no layout para refletir a ordem da sidebar."""
        widget = self._panels.get(panel_id)
        if not widget:
            return
        try:
            self.panels_layout.removeWidget(widget)
            self.panels_layout.insertWidget(new_index, widget)
        except RuntimeError:
            pass

    def update_spacer(self, active_panel_ids: Set[str]) -> None:
        """Adiciona/remove o spacer de acordo com a política de tamanho dos painéis visíveis."""
        has_expanding = False
        for pid, widget in self._panels.items():
            if pid not in active_panel_ids:
                continue
            try:
                policy = widget.sizePolicy().verticalPolicy()
                if policy in (QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding):
                    has_expanding = True
                    break
            except RuntimeError:
                continue

        if self.spacer_added:
            self.panels_layout.removeItem(self.spacer)
            self.spacer_added = False

        if not has_expanding:
            self.panels_layout.addItem(self.spacer)
            self.spacer_added = True
