"""
BrushDropdown — Dropdown Personalizado de Presets / Ferramentas do ALADYN ENGINE
================================================================================
Apresenta a seleção de receitas do ALADYN ENGINE agrupadas em 9 categorias por abas,
com um grid de 3 colunas, ícones SVG e temas dinâmicos.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.icons import get_icon
from ui.core.theme.manager import ThemeManager
from ui.core.i18n import tr, I18nManager
from .presets_data import (
    BRUSH_CATEGORIES,
    get_preset_display_name,
    get_category_display_name,
)


ABBREVIATIONS: Dict[str, str] = {
    "Pincel Redondo": "Redondo",
    "Pincel Suave": "Suave",
    "Pincel Chato (Flat)": "Flat",
    "Aerógrafo": "Aerógrafo",
    "Lápis 2H (Duro)": "Lápis 2H",
    "Lápis HB (Médio)": "Lápis HB",
    "Lápis 6B (Mole)": "Lápis 6B",
    "Carvão Vegetal": "Carvão",
    "Giz de Pastel": "Pastel",
    "G-Pen (Mangá)": "G-Pen",
    "Pena Redonda": "Pena Red.",
    "Nanquim Técnico": "Nanquim",
    "Caneta Tinteiro": "Tinteiro",
    "Borracha Dura": "Dura",
    "Borracha Mole": "Mole",
    "Borracha de Aerógrafo": "Soft Er.",
    "Marcador Copic": "Copic",
    "Caneta Feltro": "Feltro",
    "Marcador Permanente": "Perm.",
    "Desfoque Suave": "Blur Suave",
    "Desfoque Intenso": "Blur Forte",
    "Desfoque de Borda (Foco)": "Blur Foco",
    "Esfuminho Suave": "Esfuminho",
    "Arrasto de Óleo": "Arrasto",
    "Misturador de Cor (Pena)": "Misturador",
    "Aquarela Diluída (Wet-on-Wet)": "Wet-Wet",
    "Aquarela Concentrada (Wet-on-Dry)": "Wet-Dry",
    "Pincel Seco (Dry Brush)": "Dry Brush",
    "Veladura Transparente (Glaze)": "Glaze",
    "Espátula de Impasto (Palette Knife)": "Espátula",
    "Pincel de Cerda Pesada (Heavy Bristle)": "Cerda",
    "Óleo Glaze Viscoso (Viscous Glaze)": "Óleo Glaze",
    "Pincel de Carga Seca (Dry Scumble)": "Scumble",
}


def abbreviate_name(name: str) -> str:
    if name in ABBREVIATIONS:
        return ABBREVIATIONS[name]
    clean = name.replace("Pincel ", "").replace("Lápis ", "").replace("Brush ", "")
    if len(clean) > 12:
        return clean[:10] + ".."
    return clean


def get_default_preset_for_category(cat_id: str) -> Optional[Dict[str, Any]]:
    """Retorna o primeiro preset de uma categoria informada."""
    for cat in BRUSH_CATEGORIES:
        if cat["id"] == cat_id:
            presets = cat.get("presets", [])
            if presets:
                preset_info = dict(presets[0])
                preset_info["engine_type"] = cat["engine_type"]
                preset_info["category_id"] = cat_id
                return preset_info
    return None


class BrushSelectorPopup(QtWidgets.QDialog):
    """
    Popup flutuante de receitas do ALADYN ENGINE contendo 9 abas por mini-motor
    e um grid de 3 colunas de receitas curadas.
    """

    preset_selected = QtCore.Signal(str, dict)  # (label, preset_dict)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        flags = QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint
        super().__init__(parent, flags)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("QDialog { background: transparent; border: none; }")

        # 340px conteúdo + 24px margens de sombra externas
        self.setFixedSize(364, 310)

        self._active_preset: str = "Pincel Redondo"

        self.categories_keys = ["brush", "pencil", "inker", "eraser", "marker", "blur", "smudge", "watercolor", "oil"]

        self.cat_metadata = {
            "brush": {"label": get_category_display_name("brush", "Pincel Básico"), "icon": "cat_pinceis"},
            "pencil": {"label": get_category_display_name("pencil", "Lápis & Carvão"), "icon": "cat_lapis"},
            "inker": {"label": get_category_display_name("inker", "Caneta & Nanquim"), "icon": "cat_canetas"},
            "eraser": {"label": get_category_display_name("eraser", "Borracha"), "icon": "cat_borrachas"},
            "marker": {"label": get_category_display_name("marker", "Marcador & Feltro"), "icon": "cat_canetas"},
            "blur": {"label": get_category_display_name("blur", "Blur"), "icon": "cat_efeitos"},
            "smudge": {"label": get_category_display_name("smudge", "Smudge"), "icon": "cat_smudges"},
            "watercolor": {"label": get_category_display_name("watercolor", "Aquarela"), "icon": "cat_pinceis"},
            "oil": {"label": get_category_display_name("oil", "Óleo 3D"), "icon": "cat_pinceis"},
        }

        self._build_ui()
        self.populate_recipes()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def retranslate_ui(self):
        for k, btn in self.tab_buttons.items():
            btn.setToolTip(get_category_display_name(k))
        for btn in getattr(self, "buttons_list", []):
            raw = getattr(btn, "recipe_name", "")
            disp = get_preset_display_name(raw)
            btn.setToolTip(disp)
            btn.setText(abbreviate_name(disp))

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(0)

        self.container = QtWidgets.QFrame(self)
        self.container.setObjectName("PopupContainer")

        shadow = QtWidgets.QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(10)
        shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        shadow.setOffset(0, 2)
        self.container.setGraphicsEffect(shadow)

        main_layout.addWidget(self.container)

        container_layout = QtWidgets.QVBoxLayout(self.container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(6)

        # ── 1. Barra de Abas (Mini-Motores) ──────────────────────────────────
        tab_bar_layout = QtWidgets.QHBoxLayout()
        tab_bar_layout.setContentsMargins(0, 0, 0, 0)
        tab_bar_layout.setSpacing(2)

        self.tab_buttons: Dict[str, QtWidgets.QToolButton] = {}
        self.tab_group = QtWidgets.QButtonGroup(self)
        self.tab_group.setExclusive(True)

        for cat_key in self.categories_keys:
            meta = self.cat_metadata[cat_key]
            btn = QtWidgets.QToolButton(self.container)
            btn.setCheckable(True)
            btn.setFixedSize(30, 26)
            btn.setIconSize(QtCore.QSize(16, 16))
            btn.setIcon(get_icon(meta["icon"]))
            btn.setToolTip(get_category_display_name(cat_key, meta["label"]))
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setObjectName("TabButton")
            btn.clicked.connect(lambda _, k=cat_key: self._on_tab_clicked(k))

            self.tab_group.addButton(btn)
            self.tab_buttons[cat_key] = btn
            tab_bar_layout.addWidget(btn)

        container_layout.addLayout(tab_bar_layout)

        # Divisor sutil
        divider = QtWidgets.QFrame(self.container)
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setFrameShadow(QtWidgets.QFrame.Plain)
        divider.setObjectName("PopupDivider")
        container_layout.addWidget(divider)

        # ── 2. QStackedWidget com Grids de 3 Colunas ─────────────────────────
        self.stacked_widget = QtWidgets.QStackedWidget(self.container)
        self.stacked_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.grids: Dict[str, QtWidgets.QGridLayout] = {}

        for cat_key in self.categories_keys:
            page = QtWidgets.QWidget()
            page_layout = QtWidgets.QVBoxLayout(page)
            page_layout.setContentsMargins(0, 2, 0, 0)
            page_layout.setSpacing(0)

            grid_widget = QtWidgets.QWidget()
            grid_layout = QtWidgets.QGridLayout(grid_widget)
            grid_layout.setContentsMargins(0, 0, 0, 0)
            grid_layout.setSpacing(4)
            grid_layout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)

            self.grids[cat_key] = grid_layout
            page_layout.addWidget(grid_widget)
            page_layout.addStretch()

            self.stacked_widget.addWidget(page)

        container_layout.addWidget(self.stacked_widget, 1)

    def _on_tab_clicked(self, cat_key: str) -> None:
        if cat_key in self.categories_keys:
            idx = self.categories_keys.index(cat_key)
            self.stacked_widget.setCurrentIndex(idx)
            if cat_key in self.tab_buttons:
                self.tab_buttons[cat_key].setChecked(True)

    def set_active_recipe(self, name: str) -> None:
        self._active_preset = name
        self._update_button_selection_states()

    def populate_recipes(self) -> None:
        """Popula os grids com as 9 categorias e receitas nativas do ALADYN ENGINE."""
        for grid in self.grids.values():
            while grid.count():
                item = grid.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()

        self.buttons_list: List[QtWidgets.QToolButton] = []

        for cat_data in BRUSH_CATEGORIES:
            cat_key = cat_data["id"]
            if cat_key not in self.grids:
                continue

            grid = self.grids[cat_key]
            row, col = 0, 0

            for preset in cat_data.get("presets", []):
                recipe_name = preset["label"]
                display_name = get_preset_display_name(recipe_name)
                preset_info = dict(preset)
                preset_info["engine_type"] = cat_data["engine_type"]
                preset_info["category_id"] = cat_key

                btn = QtWidgets.QToolButton(self.stacked_widget)
                btn.setFixedSize(98, 56)
                btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
                btn.setIconSize(QtCore.QSize(18, 18))
                btn.setCursor(QtCore.Qt.PointingHandCursor)
                btn.setObjectName("GridPresetButton")
                btn.setToolTip(display_name)
                btn.setText(abbreviate_name(display_name))
                btn.setIcon(get_icon(self.cat_metadata[cat_key]["icon"]))
                btn.recipe_name = recipe_name
                btn.preset_data = preset_info

                btn.clicked.connect(lambda _, n=recipe_name, d=preset_info: self._on_recipe_clicked(n, d))

                grid.addWidget(btn, row, col)
                self.buttons_list.append(btn)

                col += 1
                if col >= 3:
                    col = 0
                    row += 1

        self._update_button_selection_states()
        self._on_tab_clicked("brush")

    def _update_button_selection_states(self) -> None:
        for btn in getattr(self, "buttons_list", []):
            is_active = (getattr(btn, "recipe_name", "") == self._active_preset)
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_recipe_clicked(self, name: str, data: dict) -> None:
        self.set_active_recipe(name)
        self.preset_selected.emit(name, data)
        self.close()

    def _apply_theme(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel")
        border = theme.get_color("border")
        text_main = theme.get_color("text_main")
        accent = theme.get_color("accent")
        bg_hover = theme.get_color("accent_muted")

        self.container.setStyleSheet(f"""
            QFrame#PopupContainer {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QFrame#PopupDivider {{
                background-color: {border};
            }}
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                color: {text_main};
                font-size: 10px;
                font-weight: bold;
            }}
            QToolButton:hover {{
                background-color: {bg_hover};
                border: 1px solid {border};
            }}
            QToolButton[active="true"], QToolButton:checked {{
                background-color: {accent};
                color: #ffffff;
            }}
        """)


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

        if hasattr(backend, "apply_brush_preset_dict"):
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
