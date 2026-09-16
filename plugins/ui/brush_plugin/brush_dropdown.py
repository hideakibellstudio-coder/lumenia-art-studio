"""
BrushDropdown — Botão Dropdown de Presets / Ferramentas do ALADYN ENGINE
========================================================================
Exibe a receita ativa e dispara a troca no ALADYN ENGINE com suporte a persistência.
"""

from __future__ import annotations

from typing import Dict, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.i18n import tr, I18nManager
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
    Botão Dropdown Personalizado para o Painel de Pincéis da Lumenia UI.
    Exibe a receita ativa e dispara a troca no ALADYN ENGINE com suporte a persistência por ferramenta.
    """

    preset_changed = QtCore.Signal(str, dict)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("BrushDropdown")
        self.setFixedHeight(26)
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._popup: Optional[BrushSelectorPopup] = None
        self._active_preset: str = "Pincel Redondo"

        # Estado de persistência isolado por ferramenta para evitar poluição cruzada
        self._current_tool_id: str = "brush"
        self._tool_preset_state: Dict[str, Optional[Dict[str, Any]]] = {
            "brush": None,
            "eraser": None,
            "smudge": None,
        }

        self.retranslate_ui()
        self.clicked.connect(self._open_popup)

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self._apply_style()

    def retranslate_ui(self):
        disp = get_preset_display_name(self._active_preset)
        self.setText(f"{disp} ▾")
        self.setToolTip(f"{tr('tools.brush', 'Pincel')}: {disp}")

    def sync_to_tool(self, tool_id: str) -> None:
        """
        Sincroniza imediatamente o dropdown e a aba do popup quando a ferramenta ativa muda.
        """
        self._current_tool_id = tool_id

        # Recupera o estado persistido da ferramenta ou pega o primeiro padrão da categoria
        preset_info = self._tool_preset_state.get(tool_id)

        if not preset_info:
            if tool_id == "eraser":
                preset_info = get_default_preset_for_category("eraser")
            elif tool_id == "smudge":
                preset_info = get_default_preset_for_category("smudge")
            elif tool_id == "brush":
                preset_info = get_default_preset_for_category("brush")

        if preset_info:
            name = preset_info.get("label", "Pincel Redondo")
            self.set_preset(name)

            # Salva como ativo na persistência da ferramenta correspondente
            self._tool_preset_state[tool_id] = preset_info

            # Sincroniza aba do popup
            cat_id = preset_info.get("category_id", tool_id if tool_id in ["eraser", "smudge"] else "brush")
            if self._popup:
                self._popup._on_tab_clicked(cat_id)
                self._popup.set_active_recipe(name)

            # Dispara aplicação no backend
            self._apply_preset_backend(name, preset_info)
            self.preset_changed.emit(name, preset_info)

    def set_preset(self, name: str) -> None:
        self._active_preset = name
        disp = get_preset_display_name(name)
        self.setText(f"{disp} ▾")
        self.setToolTip(f"{tr('tools.brush', 'Pincel')}: {disp}")
        if self._popup:
            self._popup.set_active_recipe(name)

    def _open_popup(self) -> None:
        if self._popup is None:
            self._popup = BrushSelectorPopup(self.window())
            self._popup.preset_selected.connect(self._on_preset_selected)

        # Sincroniza aba do popup com base no preset ativo ou ferramenta ativa
        active_state = self._tool_preset_state.get(self._current_tool_id)
        if active_state and "category_id" in active_state:
            self._popup._on_tab_clicked(active_state["category_id"])

        self._popup.set_active_recipe(self._active_preset)
        pos = self.mapToGlobal(QtCore.QPoint(-12, self.height() - 8))
        self._popup.move(pos)
        self._popup.show()

    def _on_preset_selected(self, name: str, data: dict) -> None:
        self.set_preset(name)

        # Atualiza a persistência ESTRITAMENTE da ferramenta atualmente ativa
        current_tool = getattr(self, "_current_tool_id", "brush")
        save_data = dict(data)
        save_data["label"] = name
        if current_tool in self._tool_preset_state:
            self._tool_preset_state[current_tool] = save_data
        else:
            self._tool_preset_state["brush"] = save_data

        self._apply_preset_backend(name, data)
        self.preset_changed.emit(name, data)

    def _apply_preset_backend(self, name: str, data: dict) -> None:
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return

        if backend:
            backend.apply_brush_preset_dict(data)

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
