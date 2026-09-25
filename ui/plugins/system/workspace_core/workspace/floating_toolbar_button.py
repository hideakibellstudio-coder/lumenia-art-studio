"""FloatingToolbarButton — botão de ferramenta da barra flutuante.

Separado de floating_toolbar.py em 2026-09-22 (o arquivo tinha 445 linhas, na
"parede dos 450"). Classe movida sem alteração.
"""
from typing import Optional
from PySide6 import QtWidgets, QtCore
from ui.infrastructure.icons import get_icon
from ui.infrastructure.theme.manager import ThemeManager
from ui.core.tools import TOOL_META


class FloatingToolbarButton(QtWidgets.QPushButton):
    """Botão de ferramenta individual da barra flutuante."""

    def __init__(self, tool_id: str, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.tool_id = tool_id
        meta = TOOL_META.get(tool_id, {"name": tool_id.capitalize(), "icon": "brush"})
        self.icon_key = meta["icon"]
        from ui.core.tools import get_tool_name
        self.tool_name = get_tool_name(tool_id)
        self.setCheckable(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip(self.tool_name)
        self.update_scale()
        self._apply_style(active=False)

    def update_scale(self, scale: Optional[float] = None) -> None:
        s = scale if scale is not None else ThemeManager.instance().ui_scale
        btn_sz = max(24, int(38 * s))
        ico_sz = max(14, int(22 * s))
        self.setFixedSize(btn_sz, btn_sz)
        self.setIconSize(QtCore.QSize(ico_sz, ico_sz))

    def retranslate_ui(self) -> None:
        from ui.core.tools import get_tool_name
        self.tool_name = get_tool_name(self.tool_id)
        self.setToolTip(self.tool_name)

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        self._apply_style(active=active)

    def _apply_style(self, active: bool) -> None:
        theme = ThemeManager.instance()
        accent = theme.get_color("accent")
        bg_hover = theme.get_color("accent_muted")

        if active:
            self.setIcon(get_icon(self.icon_key, color="FG_PRIMARY"))
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    border: none;
                    border-radius: 8px;
                    padding: 0px;
                }}
            """)
        else:
            self.setIcon(get_icon(self.icon_key, color="text_main"))
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: 8px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {bg_hover};
                }}
            """)
