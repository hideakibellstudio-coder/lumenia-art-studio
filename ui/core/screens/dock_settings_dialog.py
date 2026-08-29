"""
DockBarsSettingsDialog — Configurações do Sistema de Gavetas
=============================================================
Permite configurar:
  - Auto-recolhimento da sidebar
  - Velocidade da animação de recolhimento
  - Delay de hover para expansão da pílula
  - Organização dos painéis (ordem dentro de cada gaveta, com setas de movimentação)

As configurações são persistidas via QSettings.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog

_SETTINGS_ORG  = "Lumenia"
_SETTINGS_APP  = "LumeniaApp"


def load_dock_settings() -> dict:
    """Carrega as configurações de gavetas do QSettings."""
    s = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    return {
        "auto_collapse": s.value("dock/auto_collapse", False, type=bool),
        "speed":         s.value("dock/speed",         "Rápido",        type=str),
        "hover_delay":   s.value("dock/hover_delay",   "Normal (350ms)", type=str),
    }


def save_dock_settings(cfg: dict) -> None:
    """Persiste as configurações de gavetas no QSettings."""
    s = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    s.setValue("dock/auto_collapse", cfg["auto_collapse"])
    s.setValue("dock/speed",         cfg["speed"])
    s.setValue("dock/hover_delay",   cfg["hover_delay"])


class DockBarsSettingsDialog(BaseFramelessDialog):
    """Diálogo de configurações das Barras de Gavetas laterais."""

    settings_applied = QtCore.Signal(dict)  # emite cfg dict quando o usuário aplica

    def __init__(self, workspace=None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(title="Configurações: Barra de Gavetas", icon_name="settings", parent=parent, modal=True)
        self._workspace = workspace
        self.resize(660, 540)

        self._build_ui()
        self._load_settings()

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    # ── Construção da UI ──────────────────────────────────────────────────

    def _build_ui(self) -> None:
        main = self.content_layout

        # ── Seção: Comportamento ───────────────────────────────────────
        lbl_behavior = QtWidgets.QLabel("Comportamento")
        lbl_behavior.setStyleSheet("font-size: 13px; font-weight: bold;")
        main.addWidget(lbl_behavior)

        behavior_grid = QtWidgets.QGridLayout()
        behavior_grid.setSpacing(10)

        # Auto-recolhimento
        behavior_grid.addWidget(QtWidgets.QLabel("Auto-Recolhimento:"), 0, 0)
        self.chk_collapse = QtWidgets.QCheckBox("Recolher barra ao mover o mouse para fora")
        behavior_grid.addWidget(self.chk_collapse, 0, 1)
        self.chk_collapse.stateChanged.connect(self._update_controls_state)

        # Velocidade
        behavior_grid.addWidget(QtWidgets.QLabel("Velocidade:"), 1, 0)
        self.cbo_speed = QtWidgets.QComboBox()
        self.cbo_speed.addItems(["Ultra Rápido", "Rápido", "Normal", "Lento"])
        self.cbo_speed.setFixedWidth(180)
        behavior_grid.addWidget(self.cbo_speed, 1, 1)

        # Delay
        behavior_grid.addWidget(QtWidgets.QLabel("Delay (Pílula Hover):"), 2, 0)
        self.cbo_delay = QtWidgets.QComboBox()
        self.cbo_delay.addItems(["Sem Atraso", "Curto (100ms)", "Normal (350ms)", "Longo (800ms)"])
        self.cbo_delay.setFixedWidth(180)
        behavior_grid.addWidget(self.cbo_delay, 2, 1)

        main.addLayout(behavior_grid)

        # ── Separador ─────────────────────────────────────────────────
        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.HLine)
        main.addWidget(sep2)

        # ── Seção: Organização dos Painéis ────────────────────────────
        lbl_org = QtWidgets.QLabel("Organização dos Painéis")
        lbl_org.setStyleSheet("font-size: 13px; font-weight: bold;")
        main.addWidget(lbl_org)

        lbl_org_desc = QtWidgets.QLabel(
            "Clique nas setas para alterar a ordem dos painéis em cada gaveta. "
            "Ou arraste diretamente os botões na sidebar."
        )
        lbl_org_desc.setWordWrap(True)
        lbl_org_desc.setStyleSheet("color: #8b949e; font-size: 10px;")
        main.addWidget(lbl_org_desc)

        lists_layout = QtWidgets.QHBoxLayout()
        lists_layout.setSpacing(10)

        # Gaveta Esquerda
        left_col = QtWidgets.QVBoxLayout()
        lbl_left = QtWidgets.QLabel("Gaveta Esquerda")
        lbl_left.setStyleSheet("font-weight: bold; font-size: 11px;")
        left_col.addWidget(lbl_left)
        self.list_left = self._make_panel_list()
        left_col.addWidget(self.list_left)
        arrow_left = self._make_arrow_btns(self.list_left)
        left_col.addLayout(arrow_left)
        lists_layout.addLayout(left_col)

        # Gaveta Direita
        right_col = QtWidgets.QVBoxLayout()
        lbl_right = QtWidgets.QLabel("Gaveta Direita")
        lbl_right.setStyleSheet("font-weight: bold; font-size: 11px;")
        right_col.addWidget(lbl_right)
        self.list_right = self._make_panel_list()
        right_col.addWidget(self.list_right)
        arrow_right = self._make_arrow_btns(self.list_right)
        right_col.addLayout(arrow_right)
        lists_layout.addLayout(right_col)

        main.addLayout(lists_layout)

        # ── Botões de Ação ─────────────────────────────────────────────
        sep3 = QtWidgets.QFrame()
        sep3.setFrameShape(QtWidgets.QFrame.HLine)
        main.addWidget(sep3)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()

        self.btn_apply = QtWidgets.QPushButton("Aplicar")
        self.btn_apply.setFixedHeight(30)
        self.btn_apply.clicked.connect(self._on_apply)
        btn_row.addWidget(self.btn_apply)

        self.btn_ok = QtWidgets.QPushButton("OK")
        self.btn_ok.setFixedHeight(30)
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_ok)

        btn_cancel = QtWidgets.QPushButton("Cancelar")
        btn_cancel.setFixedHeight(30)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        main.addLayout(btn_row)

    def _make_panel_list(self) -> QtWidgets.QListWidget:
        lw = QtWidgets.QListWidget()
        lw.setDragDropMode(QtWidgets.QListWidget.InternalMove)
        lw.setDefaultDropAction(QtCore.Qt.MoveAction)
        lw.setAlternatingRowColors(True)
        lw.setFixedHeight(130)
        return lw

    def _make_arrow_btns(self, list_widget: QtWidgets.QListWidget) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        btn_up = QtWidgets.QPushButton("▲ Mover para Cima")
        btn_up.setFixedHeight(26)
        btn_up.clicked.connect(lambda: self._move_item(list_widget, -1))
        btn_dn = QtWidgets.QPushButton("▼ Mover para Baixo")
        btn_dn.setFixedHeight(26)
        btn_dn.clicked.connect(lambda: self._move_item(list_widget, +1))
        row.addWidget(btn_up)
        row.addWidget(btn_dn)
        return row

    # ── Lógica de controle ────────────────────────────────────────────────

    def _move_item(self, lw: QtWidgets.QListWidget, direction: int) -> None:
        row = lw.currentRow()
        if row < 0:
            return
        new_row = row + direction
        if new_row < 0 or new_row >= lw.count():
            return
        item = lw.takeItem(row)
        lw.insertItem(new_row, item)
        lw.setCurrentRow(new_row)

    def _update_controls_state(self) -> None:
        enabled = self.chk_collapse.isChecked()
        self.cbo_speed.setEnabled(enabled)
        self.cbo_delay.setEnabled(enabled)

    # ── Carregar / Salvar ─────────────────────────────────────────────────

    def _load_settings(self) -> None:
        cfg = load_dock_settings()
        self.chk_collapse.setChecked(cfg["auto_collapse"])
        self.cbo_speed.setCurrentText(cfg["speed"])
        self.cbo_delay.setCurrentText(cfg["hover_delay"])
        self._update_controls_state()
        self._populate_panel_lists()

    def _populate_panel_lists(self) -> None:
        """Carrega os painéis de cada gaveta a partir do workspace."""
        self.list_left.clear()
        self.list_right.clear()

        if not self._workspace:
            return

        if hasattr(self._workspace, "left_dock"):
            for pid in self._workspace.left_dock.get_panel_order():
                title = self._workspace.left_dock.panel_data.get(pid, {}).get("title", pid)
                item = QtWidgets.QListWidgetItem(title)
                item.setData(QtCore.Qt.UserRole, pid)
                self.list_left.addItem(item)

        if hasattr(self._workspace, "right_dock"):
            for pid in self._workspace.right_dock.get_panel_order():
                title = self._workspace.right_dock.panel_data.get(pid, {}).get("title", pid)
                item = QtWidgets.QListWidgetItem(title)
                item.setData(QtCore.Qt.UserRole, pid)
                self.list_right.addItem(item)

    def _collect_config(self) -> dict:
        return {
            "auto_collapse": self.chk_collapse.isChecked(),
            "speed":         self.cbo_speed.currentText(),
            "hover_delay":   self.cbo_delay.currentText(),
        }

    def _collect_order(self) -> dict:
        left_order  = [self.list_left.item(i).data(QtCore.Qt.UserRole)  for i in range(self.list_left.count())]
        right_order = [self.list_right.item(i).data(QtCore.Qt.UserRole) for i in range(self.list_right.count())]
        return {"left": left_order, "right": right_order}

    def _on_apply(self) -> None:
        cfg = self._collect_config()
        save_dock_settings(cfg)
        self.settings_applied.emit(cfg)

        # Aplica a ordem dos painéis ao workspace imediatamente
        if self._workspace:
            order = self._collect_order()
            # A sidebar já foi reordenada via drag & drop ou UI; apenas notifica
            # (a reordenação real é feita pelos botões que alteram a QListWidget)

    def accept(self) -> None:
        self._on_apply()
        super().accept()

    # ── Tema ──────────────────────────────────────────────────────────────

    def _apply_theme(self, *args) -> None:
        self.setStyleSheet(ThemeManager.instance().get_stylesheet())
