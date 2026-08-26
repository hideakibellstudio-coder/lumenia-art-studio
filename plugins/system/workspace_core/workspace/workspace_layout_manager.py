"""Layout and Dock management mixin for WorkspaceContainer."""

from PySide6 import QtCore, QtGui, QtWidgets
from .dock_system import SPEED_MAP, DELAY_MAP


class WorkspaceLayoutMixin:
    """Mixin para gerenciamento de docas laterais, PillHandles e barra flutuante."""

    def _on_dock_state_changed(self, *args) -> None:
        """Chamado quando gavetas abrem/fecham/animam."""
        if hasattr(self, "left_dock"):
            self.left_dock.update_unpinned_position()
        if hasattr(self, "right_dock"):
            self.right_dock.update_unpinned_position()
        self._update_pill_positions()
        self.update_toolbar_position()

    def _update_pill_positions(self) -> None:
        """Atualiza a posição das PillHandles estritamente nas faixas das sidebars (54px nas extremidades)."""
        if not hasattr(self, "_pill_left"):
            return

        wa_w = self.workspace_area.width()

        if hasattr(self, "left_dock"):
            self._pill_left.update_position(sidebar_slot_x=0, sidebar_slot_w=54)

        if hasattr(self, "right_dock"):
            right_slot_x = max(0, wa_w - 54)
            self._pill_right.update_position(sidebar_slot_x=right_slot_x, sidebar_slot_w=54)

    def _get_left_dock_visual_width(self) -> int:
        if not hasattr(self, "left_dock"):
            return 0
        if self.left_dock.is_pinned:
            return self.left_dock.width()
        else:
            w = self.left_dock.sidebar.width() if self.left_dock.sidebar.isVisible() else 0
            if self.left_dock.is_open and self.left_dock.drawer_container.isVisible():
                w += self.left_dock.drawer_container.width()
            return w

    def _get_right_dock_visual_width(self) -> int:
        if not hasattr(self, "right_dock"):
            return 0
        if self.right_dock.is_pinned:
            return self.right_dock.width()
        else:
            w = self.right_dock.sidebar.width() if self.right_dock.sidebar.isVisible() else 0
            if self.right_dock.is_open and self.right_dock.drawer_container.isVisible():
                w += self.right_dock.drawer_container.width()
            return w

    def update_toolbar_position(self) -> None:
        """Atualiza a posição da FloatingToolbar nativa de topo de acordo com o estado magnético."""
        if not hasattr(self, "floating_toolbar") or not self.floating_toolbar.isVisible():
            return

        state = self.floating_toolbar.dock_state
        if not state:
            return

        if state in ("snapped_left", "snapped_right"):
            self.floating_toolbar.set_orientation(QtCore.Qt.Vertical)
            if hasattr(self, "secondary_toolbar") and self.secondary_toolbar:
                self.secondary_toolbar.set_orientation(QtCore.Qt.Vertical)
        else:
            self.floating_toolbar.set_orientation(QtCore.Qt.Horizontal)
            if hasattr(self, "secondary_toolbar") and self.secondary_toolbar:
                self.secondary_toolbar.set_orientation(QtCore.Qt.Horizontal)

        wa_global = self.workspace_area.mapToGlobal(QtCore.QPoint(0, 0))
        wa_w = self.workspace_area.width()
        wa_h = self.workspace_area.height()

        tb_w = self.floating_toolbar.width()
        tb_h = self.floating_toolbar.height()

        margin_x, margin_y = 16, 12

        if state == "snapped_bottom":
            gx = wa_global.x() + (wa_w - tb_w) // 2
            gy = wa_global.y() + wa_h - tb_h - margin_y
        elif state == "snapped_top":
            gx = wa_global.x() + (wa_w - tb_w) // 2
            gy = wa_global.y() + margin_y
        elif state == "snapped_left":
            left_w = self._get_left_dock_visual_width()
            gx = wa_global.x() + left_w + margin_x
            gy = wa_global.y() + (wa_h - tb_h) // 2
        elif state == "snapped_right":
            right_w = self._get_right_dock_visual_width()
            gx = wa_global.x() + wa_w - right_w - tb_w - margin_x
            gy = wa_global.y() + (wa_h - tb_h) // 2
        else:
            return

        self.floating_toolbar.move(gx, gy)
        self.floating_toolbar.raise_()

        if hasattr(self, "secondary_toolbar") and self.secondary_toolbar.isVisible():
            self.secondary_toolbar.adjustSize()
            sec_w = self.secondary_toolbar.width()
            sec_h = self.secondary_toolbar.height()
            gap = 6

            if state in ("snapped_bottom", "free"):
                sec_gx = gx + (tb_w - sec_w) // 2
                sec_gy = gy - sec_h - gap
            elif state == "snapped_top":
                sec_gx = gx + (tb_w - sec_w) // 2
                sec_gy = gy + tb_h + gap
            elif state == "snapped_left":
                sec_gx = gx + tb_w + gap
                sec_gy = min(wa_global.y() + wa_h - sec_h - 12, max(wa_global.y() + 12, gy + (tb_h - sec_h) // 2))
            elif state == "snapped_right":
                sec_gx = gx - sec_w - gap
                sec_gy = min(wa_global.y() + wa_h - sec_h - 12, max(wa_global.y() + 12, gy + (tb_h - sec_h) // 2))
            else:
                sec_gx = gx
                sec_gy = gy - sec_h - gap

            self.secondary_toolbar.move(sec_gx, sec_gy)
            self.secondary_toolbar.raise_()

    def _on_floating_toolbar_dropped(self, global_pos: QtCore.QPoint) -> None:
        """Calcula o encaixe magnético (threshold 50px) ao soltar a barra flutuante."""
        if not hasattr(self, "floating_toolbar"):
            return

        threshold = 50
        wa_local = self.workspace_area.mapFromGlobal(global_pos)
        wa_w = self.workspace_area.width()
        wa_h = self.workspace_area.height()
        tb_w = self.floating_toolbar.width()
        tb_h = self.floating_toolbar.height()

        left_x = self._get_left_dock_visual_width()
        if abs(wa_local.x() - left_x) < threshold:
            self.floating_toolbar.dock_state = "snapped_left"
            self.update_toolbar_position()
            return

        right_w = self._get_right_dock_visual_width()
        right_edge_x = wa_w - right_w
        tb_right_x = wa_local.x() + tb_w
        if abs(tb_right_x - right_edge_x) < threshold:
            self.floating_toolbar.dock_state = "snapped_right"
            self.update_toolbar_position()
            return

        if wa_local.y() < threshold:
            self.floating_toolbar.dock_state = "snapped_top"
            self.update_toolbar_position()
            return

        tb_bottom_y = wa_local.y() + tb_h
        if abs(wa_h - tb_bottom_y) < threshold:
            self.floating_toolbar.dock_state = "snapped_bottom"
            self.update_toolbar_position()
            return

        self.floating_toolbar.dock_state = None
        self.update_toolbar_position()

    def apply_floating_toolbar_settings(self, cfg: dict) -> None:
        """Aplica configurações salvas à FloatingToolbar."""
        if not hasattr(self, "floating_toolbar"):
            return

        self.floating_toolbar.auto_collapse_speed = cfg.get("speed", "Rápido")
        self.floating_toolbar.visible_tool_ids = cfg.get("tools", [])
        self.floating_toolbar.rebuild_tools()

        if cfg.get("active", True):
            self.floating_toolbar.show()
            self.floating_toolbar.raise_()
            QtCore.QTimer.singleShot(30, self.update_toolbar_position)
        else:
            self.floating_toolbar.hide()

    def _on_status_notification(self, message: str) -> None:
        win = self.window()
        if hasattr(win, "statusBar") and win.statusBar():
            win.statusBar().showMessage(message, 3500)

    def apply_dock_settings(self, cfg: dict) -> None:
        """Aplica configurações de auto-recolhimento a ambas as docas."""
        kw = dict(
            auto_collapse=cfg.get("auto_collapse", False),
            speed=cfg.get("speed", "Rápido"),
            delay=cfg.get("hover_delay", "Normal (350ms)"),
        )
        if hasattr(self, "left_dock"):
            self.left_dock.apply_settings(**kw)
        if hasattr(self, "right_dock"):
            self.right_dock.apply_settings(**kw)

    def toggle_panel_from_menu(self, panel_id: str, side: str) -> None:
        """Alterna um painel específico via Menu Janela."""
        dock = self.left_dock if side == "left" else self.right_dock
        dock.toggle_panel(panel_id)

    def collapse_all_sidebars(self) -> None:
        """Recolhe ambas as sidebars via animação."""
        if hasattr(self, "left_dock"):
            self.left_dock._do_collapse()
        if hasattr(self, "right_dock"):
            self.right_dock._do_collapse()

    def expand_all_sidebars(self) -> None:
        """Expande ambas as sidebars via animação."""
        if hasattr(self, "left_dock"):
            self.left_dock._do_expand()
        if hasattr(self, "right_dock"):
            self.right_dock._do_expand()
