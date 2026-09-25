"""
FloatingToolbarSettingsDialog — Central de Configurações da Barra Rápida Flutuante (Lumenia V2)
================================================================================================
Interface moderna de 2 colunas no padrão Lumenia V2:
  - Coluna da Esquerda: Catálogo de ferramentas com switches individuais, atalhos e busca.
  - Coluna da Direita: Preview interativo da toolbar em tempo real, velocidade de recolhimento e docking magnético.
"""

from __future__ import annotations

from typing import List
from PySide6 import QtCore, QtGui, QtWidgets

from ui.infrastructure.theme.manager import ThemeManager
from ui.infrastructure.icons import get_icon
from ui.core.tools import TOOL_META, DEFAULT_TOOLS
from ui.core.widgets.toggle.toggle_switch import ToggleSwitch
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.screens.floating_toolbar_components import ToolbarLivePreview, ToolToggleCard

# Re-exportações para retrocompatibilidade contratual ARCcC
__all__ = [
    "ToolbarLivePreview",
    "ToolToggleCard",
    "FloatingToolbarSettingsDialog",
    "load_floating_toolbar_settings",
    "save_floating_toolbar_settings",
]

_SETTINGS_ORG = "Lumenia"
_SETTINGS_APP = "LumeniaApp"


# ── CARREGAMENTO / PERSISTÊNCIA ──────────────────────────────────────────────

def load_floating_toolbar_settings() -> dict:
    from ui.infrastructure.config import ConfigManager
    cm = ConfigManager.instance()
    sec = cm.get_section("floating_toolbar")
    active = sec.get("active", True)
    speed  = sec.get("speed", "Normal")
    tools  = sec.get("tools", list(DEFAULT_TOOLS))
    if not tools:
        tools = list(DEFAULT_TOOLS)
    return {"active": active, "speed": speed, "tools": tools}


def save_floating_toolbar_settings(cfg: dict) -> None:
    from ui.infrastructure.config import ConfigManager
    ConfigManager.instance().set_section("floating_toolbar", cfg)


# ── DIÁLOGO PRINCIPAL (2 COLUNAS) ───────────────────────────────────────────

class FloatingToolbarSettingsDialog(BaseFramelessDialog):
    """Central de Configurações da Barra Rápida Flutuante em 2 colunas."""

    settings_applied = QtCore.Signal(dict)

    def __init__(self, parent=None):
        from ui.infrastructure.i18n import tr, I18nManager
        super().__init__(title=tr("dialogs.floating_toolbar_title", "Configurações da Barra Flutuante"), icon_name="tools", parent=parent, modal=True)
        self.setObjectName("FloatingToolbarSettingsDialog")
        self.resize(820, 550)

        self._cfg = load_floating_toolbar_settings()
        self._active_tools: List[str] = list(self._cfg.get("tools", DEFAULT_TOOLS))
        self._cards: List[ToolToggleCard] = []

        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _setup_ui(self):
        from ui.infrastructure.i18n import tr
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
        self.search_box.setPlaceholderText(tr("dialogs.floating_toolbar_search", "Buscar ferramenta..."))
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
        self.lbl_insp_title = QtWidgets.QLabel(tr("dialogs.floating_toolbar_heading", "Barra Rápida Flutuante"))
        _title_font = QtGui.QFont("Segoe UI", 13)
        _title_font.setBold(True)
        self.lbl_insp_title.setFont(_title_font)

        self.lbl_insp_meta = QtWidgets.QLabel(tr("dialogs.floating_toolbar_meta", "HUD CONTEXTUAL DE CRIAÇÃO"))
        self.lbl_insp_meta.setProperty("accent", "true")

        title_box.addWidget(self.lbl_insp_title)
        title_box.addWidget(self.lbl_insp_meta)
        header_box.addLayout(title_box)
        header_box.addStretch()
        right_layout.addLayout(header_box)

        # Live Preview
        self.lbl_prev = QtWidgets.QLabel(tr("dialogs.floating_toolbar_preview", "Pré-Visualização em Tempo Real da Barra:"))
        self.lbl_prev.setStyleSheet("font-size: 11px; font-weight: bold; margin-top: 4px;")
        right_layout.addWidget(self.lbl_prev)

        self.live_preview = ToolbarLivePreview()
        self.live_preview.set_tools(self._active_tools)
        right_layout.addWidget(self.live_preview)

        # Grupo de Comportamento & Física
        self.behavior_group = QtWidgets.QGroupBox(tr("dialogs.floating_toolbar_behavior", "Comportamento & Física Magnética"))
        behavior_layout = QtWidgets.QVBoxLayout(self.behavior_group)
        behavior_layout.setContentsMargins(14, 14, 14, 14)
        behavior_layout.setSpacing(10)

        # Master Switch (Ativa/Desativa)
        row_master = QtWidgets.QHBoxLayout()
        self.lbl_master = QtWidgets.QLabel(tr("dialogs.floating_toolbar_show", "Exibir Barra Flutuante no Workspace"))
        self.switch_master = ToggleSwitch()
        self.switch_master.setChecked(self._cfg.get("active", True))
        row_master.addWidget(self.lbl_master)
        row_master.addStretch()
        row_master.addWidget(self.switch_master)
        behavior_layout.addLayout(row_master)

        # Velocidade de Auto-Recolhimento
        row_speed = QtWidgets.QHBoxLayout()
        self.lbl_speed = QtWidgets.QLabel(tr("dialogs.floating_toolbar_collapse", "Auto-Recolhimento por Inatividade:"))
        self.lbl_speed.setStyleSheet("font-size: 12px;")
        self.combo_speed = QtWidgets.QComboBox()
        current_speed = self._cfg.get("speed", "Normal")
        items = [
            ("Desativado", tr("dialogs.floating_toolbar_speed_off", "Desativado (Sempre Visível)")),
            ("Rápido", tr("dialogs.floating_toolbar_speed_fast", "Rápido (2 segundos)")),
            ("Normal", tr("dialogs.floating_toolbar_speed_normal", "Normal (4 segundos)")),
            ("Lento", tr("dialogs.floating_toolbar_speed_slow", "Lento (8 segundos)")),
        ]
        for canonical, label in items:
            self.combo_speed.addItem(label, canonical)
            if canonical == current_speed or current_speed in label:
                self.combo_speed.setCurrentIndex(self.combo_speed.count() - 1)
        row_speed.addWidget(self.lbl_speed)
        row_speed.addStretch()
        row_speed.addWidget(self.combo_speed)
        behavior_layout.addLayout(row_speed)

        right_layout.addWidget(self.behavior_group)
        right_layout.addStretch()

        # Botões de Ação na Base
        btn_box = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton(tr("dialogs.save_apply", "Salvar e Aplicar"))
        self.btn_apply.setIcon(get_icon("check"))
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.clicked.connect(self._on_apply)
        btn_box.addWidget(self.btn_apply)

        btn_box.addSpacing(8)

        self.btn_close = QtWidgets.QPushButton(tr("dialogs.close", "Fechar"))
        self.btn_close.setFixedHeight(34)
        self.btn_close.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_close)

        right_layout.addLayout(btn_box)
        cols_layout.addWidget(right_col, 1)

    def retranslate_ui(self) -> None:
        """Atualiza dinamicamente todos os textos deste diálogo quando o idioma muda."""
        from ui.infrastructure.i18n import tr
        if hasattr(self, "title_bar") and self.title_bar:
            self.title_bar.set_title(tr("dialogs.floating_toolbar_title", "Configurações da Barra Flutuante"))
        self.search_box.setPlaceholderText(tr("dialogs.floating_toolbar_search", "Buscar ferramenta..."))
        self.lbl_insp_title.setText(tr("dialogs.floating_toolbar_heading", "Barra Rápida Flutuante"))
        self.lbl_insp_meta.setText(tr("dialogs.floating_toolbar_meta", "HUD CONTEXTUAL DE CRIAÇÃO"))
        self.lbl_prev.setText(tr("dialogs.floating_toolbar_preview", "Pré-Visualização em Tempo Real da Barra:"))
        self.behavior_group.setTitle(tr("dialogs.floating_toolbar_behavior", "Comportamento & Física Magnética"))
        self.lbl_master.setText(tr("dialogs.floating_toolbar_show", "Exibir Barra Flutuante no Workspace"))
        self.lbl_speed.setText(tr("dialogs.floating_toolbar_collapse", "Auto-Recolhimento por Inatividade:"))
        self.btn_apply.setText(tr("dialogs.save_apply", "Salvar e Aplicar"))
        self.btn_close.setText(tr("dialogs.close", "Fechar"))

        cur_idx = max(0, self.combo_speed.currentIndex())
        self.combo_speed.blockSignals(True)
        self.combo_speed.clear()
        items = [
            ("Desativado", tr("dialogs.floating_toolbar_speed_off", "Desativado (Sempre Visível)")),
            ("Rápido", tr("dialogs.floating_toolbar_speed_fast", "Rápido (2 segundos)")),
            ("Normal", tr("dialogs.floating_toolbar_speed_normal", "Normal (4 segundos)")),
            ("Lento", tr("dialogs.floating_toolbar_speed_slow", "Lento (8 segundos)")),
        ]
        for canonical, label in items:
            self.combo_speed.addItem(label, canonical)
        self.combo_speed.setCurrentIndex(cur_idx)
        self.combo_speed.blockSignals(False)

        for card in self._cards:
            card.retranslate_ui()

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
                selection-color: {text_main};
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
                color: {text_main};
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
                color: {text_main};
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
