"""AdvancedDockSystem — Sistema de Gavetas Dinâmicas com Auto-Recolhimento (ARCcC v2).

Gerencia a apresentação e o ciclo de vida dos painéis laterais (esquerda e direita).
Delega cálculos geométricos ao DockGeometryCalculator, persistência ao DockStateStore,
e interpolações visuais ao DockAnimator.

Recebe pelo construtor o widget onde a gaveta flutua quando despinada
(`drawer_host`, a área do workspace) e avisa por `sidebar_resized` quando a
largura da sidebar muda. Até 2026-09-24 guardava o workspace e lia
`workspace.workspace_area` com getattr, e o animador chamava um método privado
do workspace.
"""

from __future__ import annotations
from typing import Dict, List, Set
from PySide6 import QtCore, QtWidgets

from ui.core.logger import get_logger
from .dock.sidebar_widget import SidebarWidget
from .dock.drawer_content_container import DrawerContentContainer
from .dock.dock_geometry_calculator import DockGeometryCalculator
from .dock.dock_state_store import DockStateStore
from .dock.dock_animator import DockAnimator, SPEED_MAP, DELAY_MAP

logger = get_logger("Workspace.DockSystem")


class AdvancedDockSystem(QtWidgets.QWidget):
    """Gerenciador da Doca Lateral (Esquerda ou Direita) com auto-recolhimento e gavetas."""

    drawer_opened = QtCore.Signal(str)   # panel_id ou "stacked"
    drawer_closed = QtCore.Signal()
    pin_toggled = QtCore.Signal(bool)
    sidebar_resized = QtCore.Signal()
    # Painel mostrado/escondido na gaveta (menu Janela marca o item).
    panel_visibility_changed = QtCore.Signal(str, bool)

    SIDEBAR_EXPANDED = DockAnimator.SIDEBAR_EXPANDED
    DRAWER_WIDTH = DockAnimator.DRAWER_WIDTH

    def __init__(self, side: str, drawer_host: QtWidgets.QWidget, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.side = side
        self._drawer_host = drawer_host

        self._outer_layout = QtWidgets.QHBoxLayout(self)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        self._outer_layout.setSpacing(0)

        # Estado Interno
        self.is_pinned: bool = False
        self.is_open: bool = False
        self.active_panel_ids: Set[str] = set()
        self._is_painting: bool = False

        # Componentes
        self.sidebar = SidebarWidget(side, self)
        self.drawer_container = DrawerContentContainer(side=side, parent=self)
        self._panels_info: Dict[str, dict] = {}

        # Animator
        self.animator = DockAnimator(self, on_sidebar_resized=self.sidebar_resized.emit)

        # Hover da Sidebar
        self.sidebar.installEventFilter(self)

        # Conexões
        self.sidebar.button_clicked.connect(self.toggle_panel)
        self.sidebar.order_changed.connect(self.sync_panel_order_from_sidebar)
        self.drawer_container.header.pin_toggled.connect(self.set_pinned)
        self.drawer_container.header.pin_toggled.connect(self.pin_toggled.emit)

        # Inserção no layout
        self._outer_layout.addWidget(self.sidebar)
        self.drawer_container.hide()

        from ui.core.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    # ── Geometria e Dimensões Delegadas ──
    @property
    def effective_left_x(self) -> int:
        return DockGeometryCalculator.compute_effective_left_x(self, self.drawer_container)

    @property
    def effective_right_x(self) -> int:
        return DockGeometryCalculator.compute_effective_right_x(self, self.drawer_container)

    @property
    def visual_width(self) -> int:
        return DockGeometryCalculator.compute_visual_width(self, self.sidebar, self.drawer_container, self.is_pinned, self.is_open)

    def update_unpinned_position(self) -> None:
        if self.is_pinned or (not self.is_open and self.drawer_container.maximumWidth() == 0):
            return
        host = self._drawer_host
        drawer_w = max(1, self.drawer_container.maximumWidth())
        geo = DockGeometryCalculator.compute_unpinned_geometry(self.side, host.width(), host.height(), drawer_w)
        self.drawer_container.setGeometry(geo)
        self.drawer_container.raise_()

    # ── Configurações e Animações ──
    def apply_settings(self, auto_collapse: bool, speed: str = "Rápido", delay: str = "Normal (350ms)") -> None:
        self.animator.apply_settings(auto_collapse, speed, delay)

    def inject_pill(self, pill: object) -> None:
        self.animator.inject_pill(pill)

    @property
    def is_painting(self) -> bool:
        return self._is_painting

    def collapse_sidebar(self) -> None:
        self.animator.do_collapse()

    def expand_sidebar(self) -> None:
        self.animator.do_expand()

    def open_drawer_anim(self) -> None:
        self.animator.open_drawer_anim()

    def close_drawer_anim(self) -> None:
        self.animator.close_drawer_anim()

    # ── Event Filter — Hover da Sidebar ──
    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if watched is self.sidebar:
            if event.type() == QtCore.QEvent.Leave:
                if not (self.is_open and not self.is_pinned) and (self.animator.auto_collapse or self.is_pinned):
                    if not self.sidebar.underMouse():
                        self.animator.schedule_collapse()
            elif event.type() == QtCore.QEvent.Enter:
                self.animator.cancel_collapse()
        return super().eventFilter(watched, event)

    # ── Gestão de Painéis ──
    def add_panel(self, panel_id: str, title: str, widget: QtWidgets.QWidget, icon_path: str | None = None) -> None:
        self._panels_info[panel_id] = {"title": title, "widget": widget}
        self.sidebar.add_panel_button(panel_id, title, icon_path)
        self.drawer_container.add_panel_widget(panel_id, title, widget)

    def remove_panel(self, panel_id: str) -> None:
        if panel_id in self._panels_info:
            del self._panels_info[panel_id]
            self.active_panel_ids.discard(panel_id)
            self.sidebar.remove_panel_button(panel_id)
            self.drawer_container.remove_panel_widget(panel_id)
            if not self.active_panel_ids:
                self.close_drawer()

    def _cleanup_panels(self) -> None:
        for pid in self.drawer_container.forget_dead_panels():
            self._panels_info.pop(pid, None)
            self.active_panel_ids.discard(pid)
        self.sidebar.forget_dead_buttons()

    def has_panel(self, panel_id: str) -> bool:
        return panel_id in self._panels_info

    def toggle_panel(self, panel_id: str) -> None:
        self._cleanup_panels()
        if panel_id not in self._panels_info:
            return
        widget = self.drawer_container.panel_widget(panel_id)
        if not widget:
            return
        try:
            if panel_id in self.active_panel_ids:
                self.active_panel_ids.remove(panel_id)
                self.sidebar.set_button_active(panel_id, False)
                widget.hide()
            else:
                self.active_panel_ids.add(panel_id)
                self.sidebar.set_button_active(panel_id, True)
                widget.show()
        except RuntimeError:
            self.active_panel_ids.discard(panel_id)
            return
        self.panel_visibility_changed.emit(str(panel_id), panel_id in self.active_panel_ids)

        self.drawer_container.update_spacer(self.active_panel_ids)
        self._update_drawer_state()

    def retranslate_ui(self):
        DockStateStore.retranslate_panels(self.sidebar, self._panels_info)
        if self.is_open:
            self._update_drawer_state()

    def _update_drawer_state(self) -> None:
        count = len(self.active_panel_ids)
        if count == 0:
            self.close_drawer()
        elif count == 1:
            active_pid = next(iter(self.active_panel_ids))
            title = self._panels_info.get(active_pid, {}).get("title", "")
            self.drawer_container.header.set_title(title)
            if not self.is_open:
                self.is_open = True
                self.resolve_state()
                self.drawer_opened.emit(active_pid)
        else:
            from ui.core.i18n import tr
            self.drawer_container.header.set_title(tr("window.stacked_panels", "PAINÉIS EMPILHADOS"))
            if not self.is_open:
                self.is_open = True
                self.resolve_state()
                self.drawer_opened.emit("stacked")

    def close_drawer(self) -> None:
        self._cleanup_panels()
        self.is_open = False
        for pid in list(self.active_panel_ids):
            self.panel_visibility_changed.emit(str(pid), False)
            self.sidebar.set_button_active(pid, False)
            widget = self.drawer_container.panel_widget(pid)
            if widget:
                try: widget.hide()
                except RuntimeError: pass
        self.active_panel_ids.clear()
        self.drawer_container.update_spacer(self.active_panel_ids)
        self.resolve_state()
        self.drawer_closed.emit()
        if (self.animator.auto_collapse or self.is_pinned) and not self.sidebar.underMouse():
            self.animator.schedule_collapse()

    def set_pinned(self, pinned: bool) -> None:
        self.is_pinned = pinned
        self.drawer_container.header.set_pinned(pinned)
        if self.is_open:
            self.resolve_state()
        if pinned and not self.sidebar.underMouse():
            self.collapse_sidebar()
        elif not pinned:
            self.expand_sidebar()

    def resolve_state(self) -> None:
        if not self.is_open:
            self.close_drawer_anim()
            return
        if self.is_pinned:
            if self._outer_layout.indexOf(self.drawer_container) == -1:
                self.drawer_container.setParent(self)
                if self.side == "left":
                    self._outer_layout.insertWidget(1, self.drawer_container)
                else:
                    self._outer_layout.insertWidget(0, self.drawer_container)
        else:
            if self._outer_layout.indexOf(self.drawer_container) != -1:
                self._outer_layout.removeWidget(self.drawer_container)
            self.drawer_container.setParent(self._drawer_host)
            self.update_unpinned_position()

        self.open_drawer_anim()
        if not self.is_pinned:
            self.update_unpinned_position()

    def sync_panel_order_from_sidebar(self) -> None:
        order = self.sidebar.get_panel_order()
        for idx, pid in enumerate(order):
            self.drawer_container.reorder_panel(pid, idx)

    def set_painting_state(self, is_painting: bool) -> None:
        self._is_painting = is_painting
        if is_painting and not self.is_pinned and self.is_open:
            self.close_drawer()
        if is_painting:
            self.animator.cancel_expand()

    def get_panel_order(self) -> List[str]:
        return self.sidebar.get_panel_order()

    def set_panel_order(self, order: List[str]) -> None:
        """Reordena os botões e as gavetas (ids ausentes ficam onde estão)."""
        self.sidebar.reorder_panels([pid for pid in order if pid in self._panels_info])
        self.sync_panel_order_from_sidebar()

    def panel_titles(self) -> List[tuple]:
        """[(id, título)] na ordem visual; lido pelo diálogo de configuração das docas."""
        return [(pid, self._panels_info.get(pid, {}).get("title", pid)) for pid in self.get_panel_order()]

    def get_state(self) -> dict:
        return DockStateStore.serialize_state(
            self.is_open, self.is_pinned, self.active_panel_ids, self.DRAWER_WIDTH, self.get_panel_order()
        )

    def restore_state(self, state: dict) -> None:
        DockStateStore.restore_state(self, state)
