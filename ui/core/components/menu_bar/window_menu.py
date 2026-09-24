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
from ui.core.plugins.panel_ids import PANEL_TITLES, PanelId

# Painéis com item fixo no menu: (id canônico, lado da doca, atalho, ícone).
_PANEL_ITEMS = (
    (PanelId.BRUSH, "left", "Alt+B", "brush"),
    (PanelId.COLOR, "left", "Alt+C", "palette"),
    (PanelId.LAYERS, "right", "Alt+L", "layers"),
    (PanelId.NAVIGATOR, "right", "Alt+N", "navigator"),
    (PanelId.GEOMETRY, "right", None, "shapes"),
    (PanelId.TELEMETRY, "right", None, "chart"),
)


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
    scale_requested                     = QtCore.Signal(float)
    toggle_fullscreen_requested         = QtCore.Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Janela", parent)
        self._panel_actions: dict[str, QtGui.QAction] = {}
        self._scale_actions: dict[float, QtGui.QAction] = {}
        self._setup_actions()
        self.retranslate_ui()
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().scaleChanged.connect(self.sync_scale_checked)

    def _setup_actions(self) -> None:
        # ── Painéis ────────────────────────────────────────────────────
        self._section_panels = self.addSection("Painéis de Ferramentas")

        for panel_id, side, shortcut, icon in _PANEL_ITEMS:
            self._add_panel_action(panel_id, PANEL_TITLES[panel_id][1], side, shortcut, icon=icon)

        # NOTA: sem QKeySequence("F12") aqui de proposito -- o atalho F12
        # já vive em ViewMenu.action_telemetry_grid (era um conflito de
        # atalho ambiguo do Qt ter os dois definidos; o handler de teclado
        # em MainWindow.keyPressEvent cobre o F12 fisico independentemente
        # de qual QAction anuncia o atalho). Ver
        # claude/panorama-menu-bar-fluxo-navigator.md.
        self.act_telemetry_grid = QtGui.QAction(get_icon("chart"), "Cockpit de Telemetria em Grid...", self)
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

        # ── Modo de Janela ─────────────────────────────────────────────
        self.addSeparator()
        self.act_fullscreen = QtGui.QAction(get_icon("fullscreen"), "", self)
        self.act_fullscreen.triggered.connect(self.toggle_fullscreen_requested.emit)
        self.addAction(self.act_fullscreen)

        # ── Escala de Interface ─────────────────────────────────────────
        self.addSeparator()
        self.menu_scale = self.addMenu("Escala da Interface")
        self.menu_scale.setIcon(get_icon("display"))
        self._scale_group = QtGui.QActionGroup(self)
        self._scale_group.setExclusive(True)

        from ui.core.theme.manager import ThemeManager
        current_scale = ThemeManager.instance().ui_scale
        scale_options = [
            ("80%", 0.8),
            ("100% (Padrão)", 1.0),
            ("125%", 1.25),
            ("150%", 1.5),
            ("175%", 1.75),
            ("200%", 2.0),
        ]
        for label, factor in scale_options:
            act = QtGui.QAction(label, self)
            act.setCheckable(True)
            if abs(factor - current_scale) < 0.05:
                act.setChecked(True)
            act.triggered.connect(lambda checked=False, val=factor: self.scale_requested.emit(val))
            self._scale_group.addAction(act)
            self.menu_scale.addAction(act)
            self._scale_actions[factor] = act

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
            lambda checked, pid=str(panel_id), side=default_side:
            self.toggle_panel_requested.emit(pid, side)
        )
        self._panel_actions[str(panel_id)] = act
        self.addAction(act)

    def retranslate_ui(self) -> None:
        self.setTitle(tr("menu.window.title", "Janela"))
        self._section_panels.setText(tr("menu.window.tool_panels", "Painéis de Ferramentas"))
        self._section_sidebars.setText(tr("menu.window.sidebars", "Barras Laterais"))
        for panel_id, act in self._panel_actions.items():
            if panel_id in PANEL_TITLES:
                act.setText(tr(*PANEL_TITLES[panel_id]))
        self.act_telemetry_grid.setText(tr("menu.view.telemetry_grid", "Cockpit de Telemetria em Grid..."))
        self.act_collapse.setText(tr("menu.window.collapse_all", "Recolher Todas as Barras"))
        self.act_expand.setText(tr("menu.window.expand_all", "Expandir Todas as Barras"))
        self.act_ft_settings.setText(tr("menu.window.floating_toolbar", "Barra Flutuante de Ferramentas…"))
        self.act_settings.setText(tr("menu.window.dock_settings", "Configurações de Gavetas & Docking…"))
        self.act_fullscreen.setText(tr("menu.window.fullscreen", "Alternar Tela Cheia (F11)"))
        self.menu_scale.setTitle(tr("menu.window.scale", "Escala da Interface"))

    # ── API pública ────────────────────────────────────────────────────────

    def sync_scale_checked(self, current_scale: float) -> None:
        """Marca o item de escala ativo no submenu."""
        for factor, act in self._scale_actions.items():
            act.blockSignals(True)
            act.setChecked(abs(factor - current_scale) < 0.05)
            act.blockSignals(False)

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
