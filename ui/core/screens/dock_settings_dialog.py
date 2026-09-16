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


def load_dock_settings() -> dict:
    """Carrega as configurações de gavetas do ConfigManager (JSON)."""
    from ui.core.config import ConfigManager
    sec = ConfigManager.instance().get_section("dock")
    return {
        "auto_collapse": sec.get("auto_collapse", False),
        "speed":         sec.get("speed", "Rápido"),
        "hover_delay":   sec.get("hover_delay", "Normal (350ms)"),
    }


def save_dock_settings(settings_dict: dict) -> None:
    """Persiste as configurações de gavetas no ConfigManager (JSON)."""
    from ui.core.config import ConfigManager
    ConfigManager.instance().set_section("dock", settings_dict)


class DockBarsSettingsDialog(BaseFramelessDialog):
    """Diálogo de configurações das Barras de Gavetas laterais."""

    settings_applied = QtCore.Signal(dict)  # emite cfg dict quando o usuário aplica

    def __init__(self, workspace=None, parent: QtWidgets.QWidget | None = None) -> None:
        from ui.core.i18n import tr, I18nManager
        super().__init__(title=tr("dialogs.dock_title", "Configurações: Barra de Gavetas"), icon_name="settings", parent=parent, modal=True)
        self._workspace = workspace
        self.resize(660, 540)

        self._build_ui()
        self._load_settings()

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()

    # ── Construção da UI ──────────────────────────────────────────────────

    def _build_ui(self) -> None:
        from ui.core.i18n import tr
        main = self.content_layout

        # ── Seção: Comportamento ───────────────────────────────────────
        self.lbl_behavior = QtWidgets.QLabel(tr("dialogs.dock_behavior", "Comportamento"))
        self.lbl_behavior.setStyleSheet("font-size: 13px; font-weight: bold;")
        main.addWidget(self.lbl_behavior)

        behavior_grid = QtWidgets.QGridLayout()
        behavior_grid.setSpacing(10)

        # Auto-recolhimento
        self.lbl_collapse = QtWidgets.QLabel(tr("dialogs.dock_collapse_label", "Auto-Recolhimento:"))
        behavior_grid.addWidget(self.lbl_collapse, 0, 0)
        self.chk_collapse = QtWidgets.QCheckBox(tr("dialogs.dock_collapse_check", "Recolher barra ao mover o mouse para fora"))
        behavior_grid.addWidget(self.chk_collapse, 0, 1)
        self.chk_collapse.stateChanged.connect(self._update_controls_state)

        # Velocidade
        self.lbl_speed = QtWidgets.QLabel(tr("dialogs.dock_speed_label", "Velocidade:"))
        behavior_grid.addWidget(self.lbl_speed, 1, 0)
        self.cbo_speed = QtWidgets.QComboBox()
        self.cbo_speed.setFixedWidth(180)
        behavior_grid.addWidget(self.cbo_speed, 1, 1)

        # Delay
        self.lbl_delay = QtWidgets.QLabel(tr("dialogs.dock_delay_label", "Delay (Pílula Hover):"))
        behavior_grid.addWidget(self.lbl_delay, 2, 0)
        self.cbo_delay = QtWidgets.QComboBox()
        self.cbo_delay.setFixedWidth(180)
        behavior_grid.addWidget(self.cbo_delay, 2, 1)

        main.addLayout(behavior_grid)

        # ── Separador ─────────────────────────────────────────────────
        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.HLine)
        main.addWidget(sep2)

        # ── Seção: Organização dos Painéis ────────────────────────────
        self.lbl_org = QtWidgets.QLabel(tr("dialogs.dock_panels_org", "Organização dos Painéis"))
        self.lbl_org.setProperty("heading", "true")
        main.addWidget(self.lbl_org)

        self.lbl_org_desc = QtWidgets.QLabel(
            tr("dialogs.dock_panels_org_desc",
               "Clique nas setas para alterar a ordem dos painéis em cada gaveta. "
               "Ou arraste diretamente os botões na sidebar.")
        )
        self.lbl_org_desc.setWordWrap(True)
        self.lbl_org_desc.setProperty("muted", "true")
        main.addWidget(self.lbl_org_desc)

        lists_layout = QtWidgets.QHBoxLayout()
        lists_layout.setSpacing(10)

        # Gaveta Esquerda
        left_col = QtWidgets.QVBoxLayout()
        self.lbl_left = QtWidgets.QLabel(tr("dialogs.dock_left_drawer", "Gaveta Esquerda"))
        self.lbl_left.setStyleSheet("font-weight: bold; font-size: 11px;")
        left_col.addWidget(self.lbl_left)
        self.list_left = self._make_panel_list()
        left_col.addWidget(self.list_left)
        arrow_left, self.btn_up_left, self.btn_dn_left = self._make_arrow_btns(self.list_left)
        left_col.addLayout(arrow_left)
        lists_layout.addLayout(left_col)

        # Gaveta Direita
        right_col = QtWidgets.QVBoxLayout()
        self.lbl_right = QtWidgets.QLabel(tr("dialogs.dock_right_drawer", "Gaveta Direita"))
        self.lbl_right.setStyleSheet("font-weight: bold; font-size: 11px;")
        right_col.addWidget(self.lbl_right)
        self.list_right = self._make_panel_list()
        right_col.addWidget(self.list_right)
        arrow_right, self.btn_up_right, self.btn_dn_right = self._make_arrow_btns(self.list_right)
        right_col.addLayout(arrow_right)
        lists_layout.addLayout(right_col)

        main.addLayout(lists_layout)

        # ── Botões de Ação ─────────────────────────────────────────────
        sep3 = QtWidgets.QFrame()
        sep3.setFrameShape(QtWidgets.QFrame.HLine)
        main.addWidget(sep3)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()

        self.btn_apply = QtWidgets.QPushButton(tr("dialogs.apply", "Aplicar"))
        self.btn_apply.setFixedHeight(30)
        self.btn_apply.clicked.connect(self._on_apply)
        btn_row.addWidget(self.btn_apply)

        self.btn_ok = QtWidgets.QPushButton(tr("dialogs.ok", "OK"))
        self.btn_ok.setFixedHeight(30)
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_ok)

        self.btn_cancel = QtWidgets.QPushButton(tr("dialogs.cancel", "Cancelar"))
        self.btn_cancel.setFixedHeight(30)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        main.addLayout(btn_row)

    def retranslate_ui(self) -> None:
        """Atualiza dinamicamente todos os textos deste diálogo quando o idioma é alterado."""
        from ui.core.i18n import tr
        if hasattr(self, "title_bar") and self.title_bar:
            self.title_bar.set_title(tr("dialogs.dock_title", "Configurações: Barra de Gavetas"))

        if hasattr(self, "lbl_behavior"):
            self.lbl_behavior.setText(tr("dialogs.dock_behavior", "Comportamento"))
            self.lbl_collapse.setText(tr("dialogs.dock_collapse_label", "Auto-Recolhimento:"))
            self.chk_collapse.setText(tr("dialogs.dock_collapse_check", "Recolher barra ao mover o mouse para fora"))
            self.lbl_speed.setText(tr("dialogs.dock_speed_label", "Velocidade:"))
            self.lbl_delay.setText(tr("dialogs.dock_delay_label", "Delay (Pílula Hover):"))
            self.lbl_org.setText(tr("dialogs.dock_panels_org", "Organização dos Painéis"))
            self.lbl_org_desc.setText(tr("dialogs.dock_panels_org_desc",
                                         "Clique nas setas para alterar a ordem dos painéis em cada gaveta. "
                                         "Ou arraste diretamente os botões na sidebar."))
            self.lbl_left.setText(tr("dialogs.dock_left_drawer", "Gaveta Esquerda"))
            self.lbl_right.setText(tr("dialogs.dock_right_drawer", "Gaveta Direita"))
            self.btn_apply.setText(tr("dialogs.apply", "Aplicar"))
            self.btn_ok.setText(tr("dialogs.ok", "OK"))
            self.btn_cancel.setText(tr("dialogs.cancel", "Cancelar"))
            self.btn_up_left.setText("▲ " + tr("layers.move_up", "Mover Cima"))
            self.btn_dn_left.setText("▼ " + tr("layers.move_down", "Mover Baixo"))
            self.btn_up_right.setText("▲ " + tr("layers.move_up", "Mover Cima"))
            self.btn_dn_right.setText("▼ " + tr("layers.move_down", "Mover Baixo"))

        # Atualiza itens de velocidade preservando seleção
        cur_speed_idx = max(0, self.cbo_speed.currentIndex())
        self.cbo_speed.blockSignals(True)
        self.cbo_speed.clear()
        speed_items = [
            ("Ultra Rápido", tr("dialogs.dock_speed_ultrafast", "Ultra Rápido")),
            ("Rápido", tr("dialogs.dock_speed_fast", "Rápido")),
            ("Normal", tr("dialogs.dock_speed_normal", "Normal")),
            ("Lento", tr("dialogs.dock_speed_slow", "Lento")),
        ]
        for canonical, label in speed_items:
            self.cbo_speed.addItem(label, canonical)
        self.cbo_speed.setCurrentIndex(cur_speed_idx)
        self.cbo_speed.blockSignals(False)

        # Atualiza itens de delay preservando seleção
        cur_delay_idx = max(0, self.cbo_delay.currentIndex())
        self.cbo_delay.blockSignals(True)
        self.cbo_delay.clear()
        delay_items = [
            ("Sem Atraso", tr("dialogs.dock_delay_none", "Sem Atraso")),
            ("Curto (100ms)", tr("dialogs.dock_delay_short", "Curto (100ms)")),
            ("Normal (350ms)", tr("dialogs.dock_delay_normal", "Normal (350ms)")),
            ("Longo (800ms)", tr("dialogs.dock_delay_long", "Longo (800ms)")),
        ]
        for canonical, label in delay_items:
            self.cbo_delay.addItem(label, canonical)
        self.cbo_delay.setCurrentIndex(cur_delay_idx)
        self.cbo_delay.blockSignals(False)

    def _make_panel_list(self) -> QtWidgets.QListWidget:
        lw = QtWidgets.QListWidget()
        lw.setDragDropMode(QtWidgets.QListWidget.InternalMove)
        lw.setDefaultDropAction(QtCore.Qt.MoveAction)
        lw.setAlternatingRowColors(True)
        lw.setFixedHeight(130)
        return lw

    def _make_arrow_btns(self, list_widget: QtWidgets.QListWidget) -> tuple[QtWidgets.QHBoxLayout, QtWidgets.QPushButton, QtWidgets.QPushButton]:
        from ui.core.i18n import tr
        row = QtWidgets.QHBoxLayout()
        btn_up = QtWidgets.QPushButton("▲ " + tr("layers.move_up", "Mover Cima"))
        btn_up.setFixedHeight(26)
        btn_up.clicked.connect(lambda: self._move_item(list_widget, -1))
        btn_dn = QtWidgets.QPushButton("▼ " + tr("layers.move_down", "Mover Baixo"))
        btn_dn.setFixedHeight(26)
        btn_dn.clicked.connect(lambda: self._move_item(list_widget, +1))
        row.addWidget(btn_up)
        row.addWidget(btn_dn)
        return row, btn_up, btn_dn

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
        speed_index = self.cbo_speed.findData(cfg["speed"])
        self.cbo_speed.setCurrentIndex(speed_index if speed_index >= 0 else 1)
        delay_index = self.cbo_delay.findData(cfg["hover_delay"])
        self.cbo_delay.setCurrentIndex(delay_index if delay_index >= 0 else 2)
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
            "speed":         self.cbo_speed.currentData() or self.cbo_speed.currentText(),
            "hover_delay":   self.cbo_delay.currentData() or self.cbo_delay.currentText(),
        }

    def _collect_order(self) -> dict:
        left_order  = [self.list_left.item(i).data(QtCore.Qt.UserRole)  for i in range(self.list_left.count())]
        right_order = [self.list_right.item(i).data(QtCore.Qt.UserRole) for i in range(self.list_right.count())]
        return {"left": left_order, "right": right_order}

    def _on_apply(self) -> None:
        cfg = self._collect_config()
        save_dock_settings(cfg)
        self.settings_applied.emit(cfg)

    def accept(self) -> None:
        self._on_apply()
        super().accept()

    # ── Tema ──────────────────────────────────────────────────────────────

    def _apply_theme(self, *args) -> None:
        self.setStyleSheet(ThemeManager.instance().get_stylesheet())
