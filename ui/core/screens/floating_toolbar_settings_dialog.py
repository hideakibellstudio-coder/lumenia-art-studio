from __future__ import annotations

from typing import Dict, List, Optional
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from plugins.system.workspace_core.workspace.floating_toolbar import TOOL_META, DEFAULT_TOOLS

_SETTINGS_ORG = "Lumenia"
_SETTINGS_APP = "LumeniaApp"


def load_floating_toolbar_settings() -> dict:
    """Carrega as configurações da Barra Flutuante do QSettings."""
    s = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    tools = s.value("floating_toolbar/tools", DEFAULT_TOOLS)
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",") if t.strip()]
    elif not isinstance(tools, list):
        tools = list(DEFAULT_TOOLS)

    return {
        "active": s.value("floating_toolbar/active", True, type=bool),
        "speed": s.value("floating_toolbar/speed", "Rápido", type=str),
        "tools": list(tools),
    }


def save_floating_toolbar_settings(cfg: dict) -> None:
    """Persiste as configurações da Barra Flutuante no QSettings."""
    s = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    s.setValue("floating_toolbar/active", cfg["active"])
    s.setValue("floating_toolbar/speed", cfg["speed"])
    s.setValue("floating_toolbar/tools", cfg["tools"])


class FloatingToolbarSettingsDialog(QtWidgets.QDialog):
    """Diálogo de configurações específicas para a Barra Flutuante."""

    settings_applied = QtCore.Signal(dict)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configurações: Barra Flutuante")
        self.setModal(True)
        self.setFixedSize(420, 520)

        self._build_ui()
        self._load_settings()

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        title = QtWidgets.QLabel("Configurações da Barra Flutuante")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        main_layout.addWidget(title)

        desc = QtWidgets.QLabel(
            "Personalize a exibição, velocidade de auto-recolhimento e ferramentas da barra rápida flutuante."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8b949e; font-size: 11px;")
        main_layout.addWidget(desc)

        # Ativar/Desativar
        master_layout = QtWidgets.QHBoxLayout()
        master_layout.addWidget(QtWidgets.QLabel("Ativar Barra Flutuante:"))
        self.chk_master = QtWidgets.QCheckBox()
        self.chk_master.stateChanged.connect(self._on_master_changed)
        master_layout.addWidget(self.chk_master)
        master_layout.addStretch()
        main_layout.addLayout(master_layout)

        # Velocidade
        speed_layout = QtWidgets.QHBoxLayout()
        speed_layout.addWidget(QtWidgets.QLabel("Velocidade de Recolhimento:"))
        self.cbo_speed = QtWidgets.QComboBox()
        self.cbo_speed.addItems(["Desativado", "Lento", "Rápido", "Ultra Rápido"])
        speed_layout.addWidget(self.cbo_speed)
        main_layout.addLayout(speed_layout)

        # Lista de Ferramentas
        main_layout.addWidget(QtWidgets.QLabel("Ferramentas Visíveis na Barra:"))
        self.list_tools = QtWidgets.QListWidget()
        main_layout.addWidget(self.list_tools)

        for tid, meta in TOOL_META.items():
            item = QtWidgets.QListWidgetItem(self.list_tools)
            widget = QtWidgets.QCheckBox(meta["name"])
            widget.setStyleSheet("QCheckBox { margin-left: 8px; margin-right: 8px; spacing: 8px; }")
            widget.setProperty("tool_id", tid)
            self.list_tools.setItemWidget(item, widget)
            item.setSizeHint(widget.sizeHint())

        # Divisor
        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        main_layout.addWidget(divider)

        # Botões de Ação
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()

        self.btn_apply = QtWidgets.QPushButton("Aplicar")
        self.btn_apply.setFixedHeight(30)
        self.btn_apply.clicked.connect(self._apply_settings)

        self.btn_ok = QtWidgets.QPushButton("OK")
        self.btn_ok.setFixedHeight(30)
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self._accept_settings)

        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_ok)
        main_layout.addLayout(btn_layout)

    def _on_master_changed(self) -> None:
        active = self.chk_master.isChecked()
        self.cbo_speed.setEnabled(active)
        self.list_tools.setEnabled(active)

    def _load_settings(self) -> None:
        cfg = load_floating_toolbar_settings()
        self.chk_master.setChecked(cfg["active"])
        self.cbo_speed.setCurrentText(cfg["speed"])

        visible_tools = set(cfg["tools"])
        for i in range(self.list_tools.count()):
            item = self.list_tools.item(i)
            widget = self.list_tools.itemWidget(item)
            if widget:
                tid = widget.property("tool_id")
                widget.setChecked(tid in visible_tools)

        self._on_master_changed()

    def _get_current_cfg(self) -> dict:
        tools = []
        for i in range(self.list_tools.count()):
            item = self.list_tools.item(i)
            widget = self.list_tools.itemWidget(item)
            if widget and widget.isChecked():
                tools.append(widget.property("tool_id"))

        return {
            "active": self.chk_master.isChecked(),
            "speed": self.cbo_speed.currentText(),
            "tools": tools,
        }

    def _apply_settings(self) -> None:
        cfg = self._get_current_cfg()
        save_floating_toolbar_settings(cfg)
        self.settings_applied.emit(cfg)

    def _accept_settings(self) -> None:
        self._apply_settings()
        self.accept()

    def _apply_theme(self) -> None:
        theme = ThemeManager.instance()
        bg_card = theme.get_color("bg_card") or "#25252e"
        border_color = theme.get_color("border_color") or "#383848"
        text_main = theme.get_color("text_main") or "#e1e1e6"
        accent = theme.get_color("accent") or "#8b5cf6"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_card};
                color: {text_main};
            }}
            QLabel {{
                color: {text_main};
            }}
            QComboBox, QListWidget {{
                background-color: #1e1e24;
                border: 1px solid {border_color};
                border-radius: 6px;
                color: {text_main};
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 4px;
            }}
            QPushButton {{
                background-color: #383848;
                border: none;
                border-radius: 6px;
                color: {text_main};
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: #4a4a5e;
            }}
            QPushButton:default {{
                background-color: {accent};
                color: #ffffff;
            }}
        """)
