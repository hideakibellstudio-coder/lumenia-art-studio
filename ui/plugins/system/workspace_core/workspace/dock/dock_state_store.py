"""DockStateStore — State Serialization, Layout Persistence, and i18n for Docks.

Handles serialization and restoration of panel order, pinned status,
active panel lists, and dynamic internationalization translation.

Nota (2026-09-24): serialize/restore têm teste, mas o app ainda não salva
nem restaura o estado das gavetas entre sessões (decisão pendente).
"""

from typing import TYPE_CHECKING
from ui.infrastructure.i18n import tr
from ui.core.plugins.panel_ids import PANEL_TITLES

if TYPE_CHECKING:
    from .dock_system import AdvancedDockSystem



class DockStateStore:
    """Serializes, restores, and updates localization of dock panels."""

    @staticmethod
    def serialize_state(
        is_open: bool,
        is_pinned: bool,
        active_panel_ids: set,
        drawer_width: int,
        panel_order: list
    ) -> dict:
        """Serializes current dock state into a JSON/Settings-compatible dictionary."""
        return {
            "is_open": is_open,
            "is_pinned": is_pinned,
            "active_panel_ids": list(active_panel_ids),
            "width": drawer_width,
            "panel_order": panel_order,
        }

    @staticmethod
    def restore_state(dock: 'AdvancedDockSystem', state: dict) -> None:
        """Restores dock state from saved dictionary."""
        if not state:
            return

        # 1. Panel order
        order = state.get("panel_order", [])
        if order:
            dock.set_panel_order(order)

        # 2. Pin status
        is_pinned = state.get("is_pinned", False)
        dock.set_pinned(is_pinned)

        # 3. Active panels and open drawer
        active_ids = state.get("active_panel_ids", [])
        is_open = state.get("is_open", False)
        if is_open and active_ids:
            for pid in active_ids:
                if dock.has_panel(pid) and pid not in dock.active_panel_ids:
                    dock.toggle_panel(pid)

    @staticmethod
    def retranslate_panels(sidebar, panels_info: dict) -> None:
        """Updates tooltips and titles using current locale translations."""
        for panel_id, btn in sidebar.buttons().items():
            if panel_id in PANEL_TITLES:
                key, def_val = PANEL_TITLES[panel_id]
                trans = tr(key, def_val)
                btn.setToolTip(trans)
                if panel_id in panels_info:
                    panels_info[panel_id]["title"] = trans
