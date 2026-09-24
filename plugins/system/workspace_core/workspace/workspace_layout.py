"""WorkspaceLayout — onde ficam as peças que flutuam sobre o workspace.

Gavetas despinadas, pílulas de reativação das sidebars, barra de ferramentas
flutuante (com encaixe magnético nas bordas) e barra secundária. Também
aplica as configurações das docas e da barra flutuante.

Colaborador com estado próprio do `WorkspaceContainer`: recebe pelo
construtor as peças que posiciona e escuta os sinais delas. Antes era o mixin
`WorkspaceLayoutMixin`, que descobria as peças no dono com 20 `hasattr` e era
chamado pelas docas por um método privado do workspace.
"""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ui.core.tools import DEFAULT_TOOLS

from .dock_system import AdvancedDockSystem
from .floating_toolbar import FloatingToolbar
from .pill_handle import PillHandle
from .secondary_tool_bar import SecondaryToolBar

_SIDEBAR_SLOT = 54
_SNAP_THRESHOLD = 50
_MARGIN_X, _MARGIN_Y = 16, 12
_SECONDARY_GAP = 6


class WorkspaceLayout(QtCore.QObject):
    def __init__(
        self,
        area: QtWidgets.QWidget,
        left_dock: AdvancedDockSystem,
        right_dock: AdvancedDockSystem,
        left_pill: PillHandle,
        right_pill: PillHandle,
        floating_toolbar: FloatingToolbar,
        secondary_toolbar: SecondaryToolBar,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._area = area
        self._left, self._right = left_dock, right_dock
        self._left_pill, self._right_pill = left_pill, right_pill
        self._toolbar = floating_toolbar
        self._secondary = secondary_toolbar
        for dock in (left_dock, right_dock):
            dock.drawer_opened.connect(self.refresh)
            dock.drawer_closed.connect(self.refresh)
            dock.pin_toggled.connect(self.refresh)
            dock.sidebar_resized.connect(self.update_pills)
        floating_toolbar.drag_finished.connect(self.on_toolbar_dropped)
        floating_toolbar.sizeChanged.connect(self.update_toolbar_position)
        secondary_toolbar.sizeChanged.connect(self.update_toolbar_position)

    # ── Gavetas e pílulas ─────────────────────────────────────────────────

    def refresh(self, *_args) -> None:
        """Depois de gaveta abrir/fechar/pinar ou do workspace mudar de tamanho."""
        self._left.update_unpinned_position()
        self._right.update_unpinned_position()
        self.update_pills()
        self.update_toolbar_position()

    def update_pills(self) -> None:
        """Pílulas ficam na faixa das sidebars (54 px em cada extremidade)."""
        self._left_pill.update_position(sidebar_slot_x=0, sidebar_slot_w=_SIDEBAR_SLOT)
        right_x = max(0, self._area.width() - _SIDEBAR_SLOT)
        self._right_pill.update_position(sidebar_slot_x=right_x, sidebar_slot_w=_SIDEBAR_SLOT)

    @property
    def has_unpinned_open(self) -> bool:
        return any(dock.is_open and not dock.is_pinned for dock in (self._left, self._right))

    def close_unpinned_drawers(self) -> None:
        for dock in (self._left, self._right):
            if dock.is_open and not dock.is_pinned:
                dock.close_drawer()

    def set_painting(self, painting: bool) -> None:
        """Durante o traço as gavetas não abrem nem animam."""
        self._left.set_painting_state(painting)
        self._right.set_painting_state(painting)

    def toggle_panel(self, panel_id: str, side: str) -> None:
        (self._left if side == "left" else self._right).toggle_panel(panel_id)

    def collapse_all(self) -> None:
        self._left.collapse_sidebar()
        self._right.collapse_sidebar()

    def expand_all(self) -> None:
        self._left.expand_sidebar()
        self._right.expand_sidebar()

    def retranslate(self) -> None:
        self._left.retranslate_ui()
        self._right.retranslate_ui()
        self._toolbar.retranslate_ui()

    def apply_dock_settings(self, cfg: dict) -> None:
        """Auto-recolhimento e, se vier do diálogo, a ordem dos painéis."""
        kw = dict(
            auto_collapse=cfg.get("auto_collapse", False),
            speed=cfg.get("speed", "Rápido"),
            delay=cfg.get("hover_delay", "Normal (350ms)"),
        )
        order = cfg.get("panel_order", {})
        for side, dock in (("left", self._left), ("right", self._right)):
            dock.apply_settings(**kw)
            if order.get(side):
                dock.set_panel_order(order[side])

    def dock_panels(self) -> dict:
        """{"left"/"right": [(id, título)]} na ordem atual das gavetas."""
        return {"left": self._left.panel_titles(), "right": self._right.panel_titles()}

    # ── Barra flutuante e barra secundária ────────────────────────────────

    def apply_floating_toolbar_settings(self, cfg: dict) -> None:
        self._toolbar.set_auto_collapse_speed(cfg.get("speed", "Rápido"))
        self._toolbar.visible_tool_ids = cfg.get("tools") or list(DEFAULT_TOOLS)
        self._toolbar.rebuild_tools()
        if cfg.get("active", True):
            self._toolbar.show()
            self._toolbar.raise_()
            QtCore.QTimer.singleShot(30, self, self.update_toolbar_position)
        else:
            self._toolbar.hide()

    def on_toolbar_dropped(self, global_pos: QtCore.QPoint) -> None:
        """Encaixe magnético (50 px) ao soltar a barra flutuante perto de uma borda."""
        local = self._area.mapFromGlobal(global_pos)
        area_w, area_h = self._area.width(), self._area.height()
        tb_w, tb_h = self._toolbar.width(), self._toolbar.height()
        if abs(local.x() - self._left.visual_width) < _SNAP_THRESHOLD:
            state = "snapped_left"
        elif abs(local.x() + tb_w - (area_w - self._right.visual_width)) < _SNAP_THRESHOLD:
            state = "snapped_right"
        elif local.y() < _SNAP_THRESHOLD:
            state = "snapped_top"
        elif abs(area_h - (local.y() + tb_h)) < _SNAP_THRESHOLD:
            state = "snapped_bottom"
        else:
            state = "free_floating"
        self._toolbar.dock_state = state
        self.update_toolbar_position()

    def update_toolbar_position(self) -> None:
        """Posiciona a barra flutuante pelo encaixe e a secundária ao lado dela."""
        state = self._toolbar.dock_state or "snapped_bottom"
        vertical = state in ("snapped_left", "snapped_right")
        orientation = QtCore.Qt.Vertical if vertical else QtCore.Qt.Horizontal
        self._toolbar.set_orientation(orientation)
        self._secondary.set_orientation(orientation)

        origin = self._area.mapToGlobal(QtCore.QPoint(0, 0))
        area_w, area_h = self._area.width(), self._area.height()
        if area_w < 50 or area_h < 50:
            QtCore.QTimer.singleShot(100, self, self.update_toolbar_position)
            return

        self._toolbar.adjustSize()
        tb_w = max(60, self._toolbar.width())
        tb_h = max(36, self._toolbar.height())
        if state == "snapped_bottom":
            gx, gy = origin.x() + (area_w - tb_w) // 2, origin.y() + area_h - tb_h - _MARGIN_Y
        elif state == "snapped_top":
            gx, gy = origin.x() + (area_w - tb_w) // 2, origin.y() + _MARGIN_Y
        elif state == "snapped_left":
            gx, gy = origin.x() + self._left.visual_width + _MARGIN_X, origin.y() + (area_h - tb_h) // 2
        elif state == "snapped_right":
            gx = origin.x() + area_w - self._right.visual_width - tb_w - _MARGIN_X
            gy = origin.y() + (area_h - tb_h) // 2
        else:
            return  # "free_floating": fica onde o usuário soltou

        # Nunca fora da área do workspace.
        gx = max(origin.x() + _MARGIN_X, min(origin.x() + area_w - tb_w - _MARGIN_X, gx))
        gy = max(origin.y() + _MARGIN_Y, min(origin.y() + area_h - tb_h - _MARGIN_Y, gy))
        self._toolbar.move(gx, gy)
        if not self._toolbar.isVisible():
            self._toolbar.show()
        self._toolbar.raise_()
        if self._secondary.isVisible():
            self._place_secondary(state, gx, gy, tb_w, tb_h, origin, area_h)

    def _place_secondary(self, state, gx, gy, tb_w, tb_h, origin, area_h) -> None:
        self._secondary.adjustSize()
        sec_w, sec_h = self._secondary.width(), self._secondary.height()
        top_limit, bottom_limit = origin.y() + 12, origin.y() + area_h - sec_h - 12
        if state == "snapped_top":
            x, y = gx + (tb_w - sec_w) // 2, gy + tb_h + _SECONDARY_GAP
        elif state == "snapped_left":
            x, y = gx + tb_w + _SECONDARY_GAP, min(bottom_limit, max(top_limit, gy + (tb_h - sec_h) // 2))
        elif state == "snapped_right":
            x, y = gx - sec_w - _SECONDARY_GAP, min(bottom_limit, max(top_limit, gy + (tb_h - sec_h) // 2))
        else:
            x, y = gx + (tb_w - sec_w) // 2, gy - sec_h - _SECONDARY_GAP
        self._secondary.move(x, y)
        self._secondary.raise_()
