"""
WindowMenu — Menu Janela
========================
Gerencia visibilidade de painéis e configurações de docas:
  - Alternar painéis individuais (Pincel, Cores, Camadas, Navegador…)
  - Recolher / Expandir todas as sidebars
  - Configurações da Barra de Gavetas e Barra Flutuante
"""
from __future__ import annotations

from PySide6 import QtGui, QtWidgets, QtCore
from ui.core.icons import get_icon


class WindowMenu(QtWidgets.QMenu):

    # Sinais de gerência de painel (panel_id, side)
    toggle_panel_requested = QtCore.Signal(str, str)  # panel_id, side

    # Controle de sidebar
    collapse_all_sidebars_requested = QtCore.Signal()
    expand_all_sidebars_requested   = QtCore.Signal()

    # Diálogo de configurações
    dock_settings_requested             = QtCore.Signal()
    floating_toolbar_settings_requested = QtCore.Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Janela", parent)
        self._panel_actions: dict[str, QtGui.QAction] = {}
        self._setup_actions()

    def _setup_actions(self) -> None:
        # ── Painéis ────────────────────────────────────────────────────
        self.addSection("Painéis de Ferramentas")

        self._add_panel_action("brush_plugin",    "Pincel & Ferramentas", "left",  "Alt+B", icon="brush")
        self._add_panel_action("color_plugin",    "Cores & Harmonias",    "left",  "Alt+C", icon="palette")
        self._add_panel_action("layers_plugin",   "Camadas",              "right", "Alt+L", icon="layers")
        self._add_panel_action("navigator_plugin","Navegador do Canvas",  "right", "Alt+N", icon="navigator")

        # ── Sidebar ────────────────────────────────────────────────────
        self.addSeparator()
        self.addSection("Barras Laterais")

        act_collapse = QtGui.QAction(get_icon("chevron_down"), "Recolher Todas as Barras", self)
        act_collapse.setShortcut("Alt+[")
        act_collapse.triggered.connect(self.collapse_all_sidebars_requested.emit)
        self.addAction(act_collapse)

        act_expand = QtGui.QAction(get_icon("chevron_up"), "Expandir Todas as Barras", self)
        act_expand.setShortcut("Alt+]")
        act_expand.triggered.connect(self.expand_all_sidebars_requested.emit)
        self.addAction(act_expand)

        # ── Configurações ──────────────────────────────────────────────
        self.addSeparator()

        act_ft_settings = QtGui.QAction(get_icon("tools"), "Barra Flutuante de Ferramentas…", self)
        act_ft_settings.triggered.connect(self.floating_toolbar_settings_requested.emit)
        self.addAction(act_ft_settings)

        act_settings = QtGui.QAction(get_icon("settings"), "Configurações de Gavetas & Docking…", self)
        act_settings.triggered.connect(self.dock_settings_requested.emit)
        self.addAction(act_settings)

    def _add_panel_action(
        self,
        panel_id: str,
        label: str,
        default_side: str,
        shortcut: str | None = None,
        icon: str | None = None
    ) -> None:
        act_icon = get_icon(icon) if icon else QtGui.QIcon()
        act = QtGui.QAction(act_icon, label, self) if not act_icon.isNull() else QtGui.QAction(label, self)
        act.setCheckable(True)
        if shortcut:
            act.setShortcut(shortcut)
        act.triggered.connect(
            lambda checked, pid=panel_id, side=default_side:
            self.toggle_panel_requested.emit(pid, side)
        )
        self._panel_actions[panel_id] = act
        self.addAction(act)

    # ── API pública ────────────────────────────────────────────────────────

    def set_panel_checked(self, panel_id: str, checked: bool) -> None:
        """Sincroniza o estado visual (check) do item de menu com a gaveta."""
        act = self._panel_actions.get(panel_id)
        if act:
            act.blockSignals(True)
            act.setChecked(checked)
            act.blockSignals(False)

    def register_panel(
        self,
        panel_id: str,
        label: str,
        side: str,
        shortcut: str | None = None,
        icon: str | None = None
    ) -> None:
        """Permite que plugins registrem dinamicamente painéis no menu."""
        if panel_id not in self._panel_actions:
            self._add_panel_action(panel_id, label, side, shortcut, icon)
