"""
BrushDropdown — Botão Dropdown de Presets / Ferramentas do ALADYN ENGINE
========================================================================
Mostra o preset ativo da ferramenta e abre o seletor; a escolha vai para o BrushState.
"""

from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtWidgets

from ui.core.state import BrushState
from ui.infrastructure.theme.manager import ThemeManager
from ui.infrastructure.i18n import tr, I18nManager
from .presets_data import get_preset_display_name
from .brush_selector_popup import (
    BrushSelectorPopup,
    get_default_preset_for_category,
    abbreviate_name,
    ABBREVIATIONS,
)

__all__ = ["BrushDropdown", "BrushSelectorPopup", "get_default_preset_for_category", "abbreviate_name", "ABBREVIATIONS"]

class BrushDropdown(QtWidgets.QToolButton):
    """
    Botão que mostra o preset ativo e abre o seletor de presets.

    Não guarda qual preset cada ferramenta usa: isso é do `BrushState`
    (`preset(tool)` / `select_preset(...)`). Escolher um preset aqui só pede ao
    estado; o rótulo muda quando o estado avisa (`presetSelected`).
    """

    # Ferramentas que têm categoria de preset própria.
    _PRESET_TOOLS = ("brush", "eraser", "smudge")

    def __init__(self, brush_state: BrushState, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("BrushDropdown")
        self.setFixedHeight(26)
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._state = brush_state
        self._popup: Optional[BrushSelectorPopup] = None
        self._active_preset: str = "Pincel Redondo"
        self._current_tool_id: str = "brush"

        brush_state.presetSelected.connect(self._on_state_preset_selected)
        self.retranslate_ui()
        self.clicked.connect(self._open_popup)

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self._apply_style()

    @property
    def active_preset(self) -> str:
        return self._active_preset

    def retranslate_ui(self):
        disp = get_preset_display_name(self._active_preset)
        self.setText(f"{disp} ▾")
        self.setToolTip(f"{tr('tools.brush', 'Pincel')}: {disp}")

    def sync_to_tool(self, tool_id: str) -> None:
        """Reaplica o preset da ferramenta que acabou de ficar ativa.

        Se a ferramenta nunca teve preset escolhido, usa o primeiro da categoria.
        Ferramentas sem categoria (balde, seleção...) não mudam o pincel.
        """
        self._current_tool_id = tool_id
        if tool_id not in self._PRESET_TOOLS:
            return
        remembered = self._state.preset(tool_id)
        if remembered is not None:
            name, data = remembered
        else:
            data = get_default_preset_for_category(tool_id)
            if data is None:
                return
            name = data.get("label", "Pincel Redondo")
        self._state.select_preset(tool_id, name, data)

    def set_preset(self, name: str) -> None:
        self._active_preset = name
        disp = get_preset_display_name(name)
        self.setText(f"{disp} ▾")
        self.setToolTip(f"{tr('tools.brush', 'Pincel')}: {disp}")
        if self._popup:
            self._popup.set_active_recipe(name)

    def _preset_tool(self) -> str:
        return self._current_tool_id if self._current_tool_id in self._PRESET_TOOLS else "brush"

    def _on_state_preset_selected(self, tool_id: str, name: str, data: dict) -> None:
        if tool_id != self._preset_tool():
            return
        self.set_preset(name)
        if self._popup:
            self._popup.show_category(data.get("category_id", tool_id))

    def _open_popup(self) -> None:
        if self._popup is None:
            self._popup = BrushSelectorPopup(self.window())
            self._popup.preset_selected.connect(self._on_preset_selected)

        remembered = self._state.preset(self._preset_tool())
        if remembered is not None and "category_id" in remembered[1]:
            self._popup.show_category(remembered[1]["category_id"])

        self._popup.set_active_recipe(self._active_preset)
        pos = self.mapToGlobal(QtCore.QPoint(-12, self.height() - 8))
        self._popup.move(pos)
        self._popup.show()

    def _on_preset_selected(self, name: str, data: dict) -> None:
        record = dict(data)
        record["label"] = name
        self._state.select_preset(self._preset_tool(), name, record)

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel") or "#1e1e24"
        border = theme.get_color("border") or "#2e2e38"
        text_main = theme.get_color("text_main") or "#f3f4f6"
        accent = theme.get_color("accent") or "#6366f1"

        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: bold;
                color: {text_main};
                text-align: left;
            }}
            QToolButton:hover {{
                border-color: {accent};
            }}
        """)
