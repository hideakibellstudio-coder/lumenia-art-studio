"""ToolSelectionColumn — Vertical toolbar column for brush & canvas tools.

Decoupled under ARCcC v2 (< 130 LOC).
"""

from typing import Dict
from PySide6 import QtCore, QtWidgets
from ui.infrastructure.icons import get_icon
from ui.infrastructure.theme.manager import ThemeManager
from ui.core.tools import DEFAULT_TOOLS, TOOL_META, get_tool_name


class ToolSelectionColumn(QtWidgets.QFrame):
    """Vertical tool column widget within BrushSettingsPanel."""

    toolActivated = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ToolColBox")
        self.setFixedWidth(34)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)

        self.tool_buttons: Dict[str, QtWidgets.QToolButton] = {}
        self._tool_bg = QtWidgets.QButtonGroup(self)
        self._tool_bg.setExclusive(True)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 3, 2, 3)
        layout.setSpacing(2)
        layout.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

        for tid in DEFAULT_TOOLS:
            meta = TOOL_META.get(tid, {"name": tid, "icon": tid})
            btn = QtWidgets.QToolButton(self)
            btn.setCheckable(True)
            btn.setFixedSize(28, 28)
            btn.setIconSize(QtCore.QSize(15, 15))
            btn.setToolTip(meta["name"])
            is_active = (tid == "brush")
            btn.setIcon(get_icon(meta["icon"], color="FG_PRIMARY" if is_active else "text_main"))
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, t=tid: self._on_btn_clicked(t))

            if tid == "brush":
                btn.setChecked(True)

            self._tool_bg.addButton(btn)
            self.tool_buttons[tid] = btn
            layout.addWidget(btn)

        layout.addStretch()

    def _on_btn_clicked(self, tool_id: str) -> None:
        self.set_tool_active(tool_id)
        self.toolActivated.emit(tool_id)

    def set_tool_active(self, tool_name: str) -> None:
        """Visual synchronization of active tool button without emitting signal loops."""
        for tid, btn in self.tool_buttons.items():
            btn.blockSignals(True)
            is_active = (tid == tool_name) or (tid == "shapes" and (tool_name.startswith("shape_") or tool_name == "shapes"))
            btn.setChecked(is_active)
            btn.setIcon(get_icon(TOOL_META[tid]["icon"], color="FG_PRIMARY" if is_active else "text_main"))
            btn.blockSignals(False)

    def retranslate_ui(self) -> None:
        for tid, btn in self.tool_buttons.items():
            btn.setToolTip(get_tool_name(tid))

    def apply_theme_style(self, theme: ThemeManager) -> None:
        border = theme.get_color("border")
        accent = theme.get_color("accent")
        bg_hover = theme.get_color("accent_muted")

        self.setStyleSheet(f"""
            QFrame#ToolColBox {{
                background-color: rgba(0, 0, 0, 0.22);
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """)

        tool_style = f"""
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
            }}
            QToolButton:hover {{
                background-color: {bg_hover};
                border: 1px solid {border};
            }}
            QToolButton:checked {{
                background-color: {accent};
                border: 1px solid {border};
            }}
        """
        for tid, btn in self.tool_buttons.items():
            btn.setStyleSheet(tool_style)
            is_active = btn.isChecked()
            btn.setIcon(get_icon(TOOL_META[tid]["icon"], color="FG_PRIMARY" if is_active else "text_main"))
