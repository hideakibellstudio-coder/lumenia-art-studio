"""
WindowMenu — Menu Janela — ARCcC i18n.
=======================================
Gerencia visibilidade de painéis e configurações de docas:
  - Alternar painéis individuais (Pincel, Cores, Camadas, Navegador…)
  - Recolher / Expandir todas as sidebars
  - Configurações da Barra de Gavetas e Barra Flutuante
"""
from __future__ import annotations

from PySide6 import QtGui, QtWidgets, QtCore
from ui.core.icons import get_icon
from ui.core.i18n import tr


class WindowMenu(QtWidgets.QMenu):

    # Sinais de gerência de painel (panel_id, side)
    toggle_panel_requested = QtCore.Signal(str, str)  # panel_id, side

    # Controle de sidebar
    collapse_all_sidebars_requested = QtCore.Signal()
    expand_all_sidebars_requested   = QtCore.Signal()

    # Diálogo de configurações
    dock_settings_requested             = QtCore.Signal()
    floating_toolbar_settings_requested = QtCore.Signal()
    telemetry_grid_requested            = QtCore.Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Janela", parent)
        self._panel_actions: dict[str, QtGui.QAction] = {}
        self._setup_actions()
        self.retranslate_ui()

    def _setup_actions(self) -> None:
        # ── Painéis ────────────────────────────────────────────────────
        self._section_panels = self.addSection("Painéis de Ferramentas")

        self._add_panel_action("brush_plugin",    "Pincel & Ferramentas", "left",  "Alt+B", icon="brush")
        self._add_panel_action("color_plugin",    "Cores & Harmonias",    "left",  "Alt+C", icon="palette")
        self._add_panel_action("layers_plugin",   "Camadas",              "right", "Alt+L", icon="layers")
        self._add_panel_action("navigator_plugin","Navegador do Canvas",  "right", "Alt+N", icon="navigator")
        self._add_panel_action("telemetry",       "Painel de Telemetria", "right", icon="chart")

        self.act_telemetry_grid = QtGui.QAction(get_icon("chart"), "Cockpit de Telemetria em Grid...", self)
        self.act_telemetry_grid.setShortcut("F12")
        self.act_telemetry_grid.triggered.connect(self.telemetry_grid_requested.emit)
        self.addAction(self.act_telemetry_grid)

        # ── Sidebar ────────────────────────────────────────────────────
        self.addSeparator()
        self._section_sidebars = self.addSection("Barras Laterais")

        self.act_collapse = QtGui.QAction(get_icon("chevron_down"), "", self)
        self.act_collapse.setShortcut("Alt+[")
        self.act_collapse.triggered.connect(self.collapse_all_sidebars_requested.emit)
        self.addAction(self.act_collapse)

        self.act_expand = QtGui.QAction(get_icon("chevron_up"), "", self)
        self.act_expand.setShortcut("Alt+]")
        self.act_expand.triggered.connect(self.expand_all_sidebars_requested.emit)
        self.addAction(self.act_expand)

        # ── Configurações ──────────────────────────────────────────────
        self.addSeparator()

        self.act_ft_settings = QtGui.QAction(get_icon("tools"), "", self)
        self.act_ft_settings.triggered.connect(self.floating_toolbar_settings_requested.emit)
        self.addAction(self.act_ft_settings)

        self.act_settings = QtGui.QAction(get_icon("settings"), "", self)
        self.act_settings.triggered.connect(self.dock_settings_requested.emit)
        self.addAction(self.act_settings)

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

    def retranslate_ui(self) -> None:
        self.setTitle(tr("menu.window.title", "Janela"))
        if hasattr(self, "_section_panels") and self._section_panels:
            self._section_panels.setText(tr("menu.window.tool_panels", "Painéis de Ferramentas"))
        if hasattr(self, "_section_sidebars") and self._section_sidebars:
            self._section_sidebars.setText(tr("menu.window.sidebars", "Barras Laterais"))

        if "brush_plugin" in self._panel_actions:
            self._panel_actions["brush_plugin"].setText(tr("menu.window.brush_panel", "Pincel & Ferramentas"))
        if "color_plugin" in self._panel_actions:
            self._panel_actions["color_plugin"].setText(tr("menu.window.color_wheel", "Cores & Harmonias"))
        if "layers_plugin" in self._panel_actions:
            self._panel_actions["layers_plugin"].setText(tr("menu.window.layers_panel", "Camadas"))
        if "navigator_plugin" in self._panel_actions:
            self._panel_actions["navigator_plugin"].setText(tr("menu.window.navigator", "Navegador do Canvas"))
        if "telemetry" in self._panel_actions:
            self._panel_actions["telemetry"].setText(tr("menu.window.telemetry_panel", "Painel de Telemetria"))
        if hasattr(self, "act_telemetry_grid"):
            self.act_telemetry_grid.setText(tr("menu.view.telemetry_grid", "Cockpit de Telemetria em Grid..."))

        if hasattr(self, "act_collapse"):
            self.act_collapse.setText(tr("menu.window.collapse_all", "Recolher Todas as Barras"))
        if hasattr(self, "act_expand"):
            self.act_expand.setText(tr("menu.window.expand_all", "Expandir Todas as Barras"))
        if hasattr(self, "act_ft_settings"):
            self.act_ft_settings.setText(tr("menu.window.floating_toolbar", "Barra Flutuante de Ferramentas…"))
        if hasattr(self, "act_settings"):
            self.act_settings.setText(tr("menu.window.dock_settings", "Configurações de Gavetas & Docking…"))

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
