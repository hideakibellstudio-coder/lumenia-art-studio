"""
FloatingToolbarSettingsDialog — Central de Configurações da Barra Rápida Flutuante (Lumenia V2)
================================================================================================
Interface moderna de 2 colunas no padrão Lumenia V2:
  - Coluna da Esquerda: Catálogo de ferramentas com switches individuais, atalhos e busca.
  - Coluna da Direita: Preview interativo da toolbar em tempo real, velocidade de recolhimento e docking magnético.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon
from ui.core.tools import TOOL_META, DEFAULT_TOOLS
from ui.core.widgets.toggle.toggle_switch import ToggleSwitch
from ui.core.dialogs.base_dialog import BaseFramelessDialog

_SETTINGS_ORG = "Lumenia"
_SETTINGS_APP = "LumeniaApp"


# ── PREVIEW VISUAL DA TOOLBAR ────────────────────────────────────────────────

class ToolbarLivePreview(QtWidgets.QFrame):
    """Miniatura gráfica da toolbar atualizando os botões ativos em tempo real."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(54)
        self._active_tools: List[str] = []
        self._build_ui()

    def _build_ui(self):
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(6)
        self.layout.setAlignment(QtCore.Qt.AlignCenter)

    def set_tools(self, tool_ids: List[str]):
        self._active_tools = list(tool_ids)
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Handle de arraste — usa tokens de tema
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

    def update_style(self):
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


# ── CARTÃO DA FERRAMENTA (COLUNA ESQUERDA) ───────────────────────────────────

class ToolToggleCard(QtWidgets.QFrame):
    """Cartão individual de ferramenta com switch liga/desliga."""

    toggled = QtCore.Signal(str, bool)

    def __init__(self, tool_id: str, is_active: bool = True, parent=None):
        super().__init__(parent)
        self.tool_id = tool_id
        self.is_active = is_active
        self.meta = TOOL_META.get(tool_id, {"name": tool_id.capitalize(), "icon": "brush"})

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self.update_style)
        self.update_style()

    def _build_ui(self):
        self.setFixedHeight(52)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # Ícone da Ferramenta — cor e fundo via ThemeManager
        self.icon_lbl = QtWidgets.QLabel()
        self.icon_lbl.setFixedSize(28, 28)
        self.icon_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.icon_lbl)

        # Nome e Atalho
        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setAlignment(QtCore.Qt.AlignVCenter)

        name = self.meta.get("name", self.tool_id)
        shortcut = self.meta.get("shortcut", "")
        self.name_lbl = QtWidgets.QLabel(name)
        self.name_lbl.setStyleSheet("font-size: 11px; font-weight: bold;")

        self.shortcut_lbl = QtWidgets.QLabel(f"Atalho: [{shortcut}]" if shortcut else "Sem atalho")
        self.shortcut_lbl.setStyleSheet("font-size: 9px;")

        text_layout.addWidget(self.name_lbl)
        text_layout.addWidget(self.shortcut_lbl)
        layout.addLayout(text_layout)
        layout.addStretch()

        # Switch canônico com animação e conexão ao tema
        self.switch = ToggleSwitch()
        self.switch.setChecked(self.is_active)
        self.switch.toggled.connect(self._on_toggled)
        layout.addWidget(self.switch)

    def _on_toggled(self, checked: bool):
        self.is_active = checked
        self.toggled.emit(self.tool_id, checked)
        self.update_style()

    def set_active_state(self, active: bool):
        self.is_active = active
        self.switch.blockSignals(True)
        self.switch.setChecked(active)
        self.switch.blockSignals(False)
        self.update_style()

    def update_style(self):
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


# ── CARREGAMENTO / PERSISTÊNCIA ──────────────────────────────────────────────

def load_floating_toolbar_settings() -> dict:
    s = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    s.beginGroup("FloatingToolbar")
    active = s.value("active", True, type=bool)
    speed  = s.value("speed",  "Normal", type=str)
    tools_str = s.value("tools", None)
    s.endGroup()

    if tools_str and isinstance(tools_str, str):
        tools = [t.strip() for t in tools_str.split(",") if t.strip() in TOOL_META]
    else:
        tools = list(DEFAULT_TOOLS)

    return {"active": active, "speed": speed, "tools": tools}


def save_floating_toolbar_settings(cfg: dict) -> None:
    s = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    s.beginGroup("FloatingToolbar")
    s.setValue("active", cfg.get("active", True))
    s.setValue("speed",  cfg.get("speed", "Normal"))
    s.setValue("tools",  ",".join(cfg.get("tools", DEFAULT_TOOLS)))
    s.endGroup()


# ── DIÁLOGO PRINCIPAL (2 COLUNAS) ───────────────────────────────────────────

class FloatingToolbarSettingsDialog(BaseFramelessDialog):
    """Central de Configurações da Barra Rápida Flutuante em 2 colunas."""

    settings_applied = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(title="Configurações da Barra Flutuante", icon_name="tools", parent=parent, modal=True)
        self.setObjectName("FloatingToolbarSettingsDialog")
        self.resize(820, 550)

        self._cfg = load_floating_toolbar_settings()
        self._active_tools: List[str] = list(self._cfg.get("tools", DEFAULT_TOOLS))
        self._cards: List[ToolToggleCard] = []

        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)

    def _setup_ui(self):
        cols_widget = QtWidgets.QWidget()
        cols_layout = QtWidgets.QHBoxLayout(cols_widget)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(16)
        self.content_layout.addWidget(cols_widget, 1)

        # ── COLUNA DA ESQUERDA (CATÁLOGO DE FERRAMENTAS) ────────────────────
        left_col = QtWidgets.QWidget()
        left_col.setFixedWidth(310)
        left_layout = QtWidgets.QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Campo de busca
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Buscar ferramenta...")
        self.search_box.addAction(get_icon("search"), QtWidgets.QLineEdit.LeadingPosition)
        self.search_box.textChanged.connect(self._filter_tools)
        left_layout.addWidget(self.search_box)

        # ScrollArea com lista de cards
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.cards_container = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.setSpacing(6)

        for tid in TOOL_META.keys():
            card = ToolToggleCard(tid, is_active=(tid in self._active_tools))
            card.toggled.connect(self._on_tool_toggled)
            self._cards.append(card)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()
        self.scroll_area.setWidget(self.cards_container)
        left_layout.addWidget(self.scroll_area)

        cols_layout.addWidget(left_col)

        # ── COLUNA DA DIREITA (PREVIEW & COMPORTAMENTO) ─────────────────────
        right_col = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_col)
        right_layout.setContentsMargins(12, 4, 4, 4)
        right_layout.setSpacing(14)

        # Header
        header_box = QtWidgets.QHBoxLayout()
        self.lbl_insp_icon = QtWidgets.QToolButton()
        self.lbl_insp_icon.setFixedSize(44, 44)
        self.lbl_insp_icon.setIconSize(QtCore.QSize(24, 24))
        self.lbl_insp_icon.setIcon(get_icon("tools"))
        self.lbl_insp_icon.setStyleSheet("border: none; background: rgba(255,255,255,0.08); border-radius: 8px;")
        header_box.addWidget(self.lbl_insp_icon)

        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        self.lbl_insp_title = QtWidgets.QLabel("Barra Rápida Flutuante")
        font = self.lbl_insp_title.font()
        font.setPointSize(13)
        font.setBold(True)
        self.lbl_insp_title.setFont(font)

        self.lbl_insp_meta = QtWidgets.QLabel("HUD CONTEXTUAL DE CRIAÇÃO")
        self.lbl_insp_meta.setStyleSheet("color: #ff5252; font-size: 11px; font-weight: bold;")

        title_box.addWidget(self.lbl_insp_title)
        title_box.addWidget(self.lbl_insp_meta)
        header_box.addLayout(title_box)
        header_box.addStretch()
        right_layout.addLayout(header_box)

        # Live Preview
        lbl_prev = QtWidgets.QLabel("Pré-Visualização em Tempo Real da Barra:")
        lbl_prev.setStyleSheet("font-size: 11px; font-weight: bold; margin-top: 4px;")
        right_layout.addWidget(lbl_prev)

        self.live_preview = ToolbarLivePreview()
        self.live_preview.set_tools(self._active_tools)
        right_layout.addWidget(self.live_preview)

        # Grupo de Comportamento & Física
        behavior_group = QtWidgets.QGroupBox("Comportamento & Física Magnética")
        behavior_layout = QtWidgets.QVBoxLayout(behavior_group)
        behavior_layout.setContentsMargins(14, 14, 14, 14)
        behavior_layout.setSpacing(10)

        # Master Switch (Ativa/Desativa)
        row_master = QtWidgets.QHBoxLayout()
        lbl_master = QtWidgets.QLabel("Exibir Barra Flutuante no Workspace")
        self.switch_master = ToggleSwitch()
        self.switch_master.setChecked(self._cfg.get("active", True))
        row_master.addWidget(lbl_master)
        row_master.addStretch()
        row_master.addWidget(self.switch_master)
        behavior_layout.addLayout(row_master)

        # Velocidade de Auto-Recolhimento
        row_speed = QtWidgets.QHBoxLayout()
        lbl_speed = QtWidgets.QLabel("Auto-Recolhimento por Inatividade:")
        lbl_speed.setStyleSheet("font-size: 12px;")
        self.combo_speed = QtWidgets.QComboBox()
        self.combo_speed.addItems([
            "Desativado (Sempre Visível)",
            "Rápido (150ms)",
            "Normal (300ms)",
            "Lento (500ms)"
        ])
        current_speed = self._cfg.get("speed", "Normal")
        for i in range(self.combo_speed.count()):
            if current_speed in self.combo_speed.itemText(i):
                self.combo_speed.setCurrentIndex(i)
                break
        row_speed.addWidget(lbl_speed)
        row_speed.addStretch()
        row_speed.addWidget(self.combo_speed)
        behavior_layout.addLayout(row_speed)

        right_layout.addWidget(behavior_group)
        right_layout.addStretch()

        # Botões de Ação na Base
        btn_box = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Aplicar & Salvar")
        self.btn_apply.setIcon(get_icon("check"))
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.clicked.connect(self._on_apply)
        btn_box.addWidget(self.btn_apply)

        btn_box.addSpacing(8)

        btn_close = QtWidgets.QPushButton("Fechar")
        btn_close.setFixedHeight(34)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)

        right_layout.addLayout(btn_box)
        cols_layout.addWidget(right_col, 1)

    def _filter_tools(self):
        query = self.search_box.text().strip().lower()
        for card in self._cards:
            name = card.meta.get("name", "").lower()
            shortcut = card.meta.get("shortcut", "").lower()
            tid = card.tool_id.lower()
            match = not query or (query in name) or (query in shortcut) or (query in tid)
            card.setVisible(match)

    def _on_tool_toggled(self, tool_id: str, is_active: bool):
        if is_active and tool_id not in self._active_tools:
            self._active_tools.append(tool_id)
        elif not is_active and tool_id in self._active_tools:
            self._active_tools.remove(tool_id)

        self.live_preview.set_tools(self._active_tools)

    def _on_apply(self):
        speed_raw = self.combo_speed.currentText().split()[0]
        if "Desativado" in speed_raw:
            speed_raw = "Desativado"

        cfg = {
            "active": self.switch_master.isChecked(),
            "speed": speed_raw,
            "tools": list(self._active_tools),
        }
        save_floating_toolbar_settings(cfg)
        self.settings_applied.emit(cfg)

    def _apply_theme(self, *args):
        tm = ThemeManager.instance()
        bg_app = tm.get_color("bg_main")
        bg_panel = tm.get_color("bg_panel")
        bg_card = tm.get_color("bg_card")
        border = tm.get_color("border")
        border_muted = tm.get_color("border_muted")
        text_main = tm.get_color("text_main")
        text_sec = tm.get_color("text_sec")
        accent = tm.get_color("accent")
        accent_hover = tm.get_color("accent_hover")

        self.setStyleSheet(f"""
            QDialog#FloatingToolbarSettingsDialog {{
                background-color: {bg_app};
                color: {text_main};
            }}
            QGroupBox {{
                font-size: 11px;
                font-weight: bold;
                color: {text_sec};
                border: 1px solid {border};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 14px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }}
            QLineEdit, QComboBox {{
                background-color: {bg_card};
                color: {text_main};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg_card};
                color: {text_main};
                selection-background-color: {accent};
                selection-color: #ffffff;
                border: 1px solid {border};
            }}
            QPushButton {{
                background-color: {bg_card};
                color: {text_main};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {accent};
                color: #ffffff;
            }}
            QPushButton:disabled {{
                background-color: {bg_panel};
                color: {text_sec};
                border-color: {border_muted};
            }}
        """)
        self.btn_apply.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {accent_hover};
            }}
            QPushButton:disabled {{
                background-color: {bg_panel};
                color: {text_sec};
                border: 1px solid {border_muted};
            }}
        """)
