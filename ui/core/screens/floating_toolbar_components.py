"""
FloatingToolbarComponents — Componentes Visuais para Configurações da Barra Flutuante
======================================================================================
Encapsula a moldura de pré-visualização ao vivo (ToolbarLivePreview) e o cartão
tátil de alternância de visibilidade de ferramenta (ToolToggleCard).
"""

from __future__ import annotations

from typing import List, Optional
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon
from ui.core.tools import TOOL_META
from ui.core.widgets.toggle.toggle_switch import ToggleSwitch


class ToolbarLivePreview(QtWidgets.QFrame):
    """Miniatura gráfica da toolbar atualizando os botões ativos em tempo real."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(54)
        self._active_tools: List[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(6)
        self.layout.setAlignment(QtCore.Qt.AlignCenter)

    def set_tools(self, tool_ids: List[str]) -> None:
        self._active_tools = list(tool_ids)
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tm = ThemeManager.instance()
        handle = QtWidgets.QLabel("⋮⋮")
        handle.setStyleSheet(
            f"color: {tm.get_color('text_muted')}; font-size: 13px; font-weight: bold; margin-right: 4px;"
        )
        self.layout.addWidget(handle)

        icon_color = tm.get_color("text_main")
        icon_bg = tm.get_color("bg_card")
        for tid in self._active_tools:
            meta = TOOL_META.get(tid, {})
            icon_key = meta.get("icon", "brush")
            btn = QtWidgets.QLabel()
            btn.setFixedSize(28, 28)
            btn.setAlignment(QtCore.Qt.AlignCenter)
            btn.setStyleSheet(f"background: {icon_bg}; border-radius: 6px;")
            icon = get_icon(icon_key, color=icon_color)
            if icon and not icon.isNull():
                btn.setPixmap(icon.pixmap(16, 16))
            self.layout.addWidget(btn)

        self.update_style()

    def update_style(self) -> None:
        tm = ThemeManager.instance()
        bg = tm.get_color("bg_card")
        border = tm.get_color("border")
        self.setStyleSheet(f"""
            ToolbarLivePreview {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)


class ToolToggleCard(QtWidgets.QFrame):
    """Cartão individual de ferramenta com switch liga/desliga."""

    toggled = QtCore.Signal(str, bool)

    def __init__(self, tool_id: str, is_active: bool = True, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.tool_id = tool_id
        self.is_active = is_active
        self.meta = TOOL_META.get(tool_id, {"name": tool_id.capitalize(), "icon": "brush"})

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self.update_style)
        self.update_style()

    def _build_ui(self) -> None:
        self.setFixedHeight(52)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        self.icon_lbl = QtWidgets.QLabel()
        self.icon_lbl.setFixedSize(28, 28)
        self.icon_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.icon_lbl)

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setAlignment(QtCore.Qt.AlignVCenter)

        self.name_lbl = QtWidgets.QLabel()
        self.name_lbl.setStyleSheet("font-size: 11px; font-weight: bold;")

        self.shortcut_lbl = QtWidgets.QLabel()
        self.shortcut_lbl.setStyleSheet("font-size: 9px;")

        self.retranslate_ui()

        text_layout.addWidget(self.name_lbl)
        text_layout.addWidget(self.shortcut_lbl)
        layout.addLayout(text_layout)
        layout.addStretch()

        self.switch = ToggleSwitch()
        self.switch.setChecked(self.is_active)
        self.switch.toggled.connect(self._on_toggled)
        layout.addWidget(self.switch)

    def retranslate_ui(self) -> None:
        from ui.core.tools import get_tool_name
        from ui.core.i18n import tr
        self.name_lbl.setText(get_tool_name(self.tool_id))
        shortcut = self.meta.get("shortcut", "")
        if shortcut:
            self.shortcut_lbl.setText(tr("dialogs.floating_toolbar_shortcut", f"Atalho: [{shortcut}]").replace("{key}", shortcut))
        else:
            self.shortcut_lbl.setText(tr("dialogs.floating_toolbar_no_shortcut", "Sem atalho"))

    def _on_toggled(self, checked: bool) -> None:
        self.is_active = checked
        self.toggled.emit(self.tool_id, checked)
        self.update_style()

    def set_active_state(self, active: bool) -> None:
        self.is_active = active
        self.switch.blockSignals(True)
        self.switch.setChecked(active)
        self.switch.blockSignals(False)
        self.update_style()

    def update_style(self) -> None:
        tm = ThemeManager.instance()
        bg = tm.get_color("bg_card_hover") if self.is_active else tm.get_color("bg_card")
        border = tm.get_color("accent") if self.is_active else tm.get_color("border")
        text_color = tm.get_color("text_main")
        muted = tm.get_color("text_muted")
        icon_bg = tm.get_color("accent_bg") if self.is_active else tm.get_color("bg_input")
        icon_color = tm.get_color("text_main")
        icon = get_icon(self.meta.get("icon", "brush"), color=icon_color)
        if icon and not icon.isNull():
            self.icon_lbl.setPixmap(icon.pixmap(16, 16))
        self.icon_lbl.setStyleSheet(f"background: {icon_bg}; border-radius: 6px;")
        self.shortcut_lbl.setStyleSheet(f"font-size: 9px; color: {muted};")
        self.setStyleSheet(f"""
            ToolToggleCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QLabel {{
                color: {text_color};
            }}
        """)
