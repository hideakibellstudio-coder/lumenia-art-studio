"""
panel_rename_popup — Popup flutuante de renomeação de camadas
==============================================================
Submódulo atômico do LayersPanel para edição direta do nome da camada.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtWidgets import QFrame, QLineEdit, QHBoxLayout


class LayerRenamePopup(QFrame):
    """Popup flutuante posicionado sobre o rótulo da camada para renomear com precisão."""

    name_changed = Signal(str)

    def __init__(self, current_name: str, target_rect: QRect, parent=None):
        flags = Qt.Popup | Qt.FramelessWindowHint
        super().__init__(parent, flags)

        self.input_edit = QLineEdit(current_name, self)
        self.input_edit.selectAll()
        self.input_edit.returnPressed.connect(self._on_accept)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.addWidget(self.input_edit)

        from ui.infrastructure.theme.manager import ThemeManager
        tm = ThemeManager.instance()
        bg_panel = tm.get_color("bg_panel", "#1e1e24")
        accent = tm.get_color("accent", "#6366f1")
        text_main = tm.get_color("text_main", "#f3f4f6")

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_panel};
                border: 1.5px solid {accent};
                border-radius: 4px;
            }}
            QLineEdit {{
                background: transparent;
                border: none;
                color: {text_main};
                font-weight: bold;
                font-size: 12px;
            }}
        """)

        self.setGeometry(target_rect)

    def _on_accept(self):
        new_name = self.input_edit.text().strip()
        if new_name:
            self.name_changed.emit(new_name)
        self.close()

    def focusOutEvent(self, event):
        self._on_accept()
        super().focusOutEvent(event)
