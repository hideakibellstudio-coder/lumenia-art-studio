"""DockAnimator — Animation Orchestration and Auto-Collapse Timers for Docks.

Controls smooth drawer transitions, sidebar auto-collapse timers, and PillHandle interactions.
Strictly decoupled in compliance with ARCcC v2 (< 190 LOC).
"""
import logging

from typing import TYPE_CHECKING, Optional
from PySide6 import QtCore

if TYPE_CHECKING:
    from ..dock_system import AdvancedDockSystem

SPEED_MAP = {"Ultra Rápido": 60, "Rápido": 180, "Normal": 320, "Lento": 500}
DELAY_MAP = {"Sem Atraso": 0, "Curto (100ms)": 100, "Normal (350ms)": 350, "Longo (800ms)": 800}


class DockAnimator:
    """Manages smooth expansion/collapse property animations and timers for dock components."""

    SIDEBAR_EXPANDED = 54
    DRAWER_WIDTH = 280

    def __init__(self, dock: 'AdvancedDockSystem') -> None:
        self.dock = dock

        self._auto_collapse: bool = False
        self._speed_ms: int = SPEED_MAP["Rápido"]
        self._hover_delay_ms: int = DELAY_MAP["Normal (350ms)"]
        self._pill: Optional[object] = None

        # Sidebar Animation
        self._sidebar_anim = QtCore.QPropertyAnimation(dock.sidebar, b"maximumWidth")
        self._sidebar_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._sidebar_anim.valueChanged.connect(self._on_sidebar_anim_value_changed)
        self._sidebar_anim.finished.connect(self._on_sidebar_anim_finished)

        # Drawer Animation
        self._drawer_anim = QtCore.QPropertyAnimation(dock.drawer_container, b"maximumWidth")
        self._drawer_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._drawer_anim.valueChanged.connect(self._on_drawer_anim_value_changed)
        self._drawer_anim.finished.connect(self._on_drawer_anim_finished)

        # Timers
        self._collapse_timer = QtCore.QTimer(dock)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self.do_collapse)

        self._expand_timer = QtCore.QTimer(dock)
        self._expand_timer.setSingleShot(True)
        self._expand_timer.timeout.connect(self.do_expand)

        try:
            from ui.core.theme.manager import ThemeManager
            ThemeManager.instance().scaleChanged.connect(self._on_scale_changed)
        except Exception:
            logging.getLogger(__name__).debug("DockAnimator sem reatividade de escala.", exc_info=True)

        self.update_anim_duration()

    @property
    def drawer_width(self) -> int:
        try:
            from ui.core.theme.manager import ThemeManager
            return max(180, int(self.DRAWER_WIDTH * ThemeManager.instance().ui_scale))
        except Exception:
            return self.DRAWER_WIDTH

    def _on_scale_changed(self, scale: float) -> None:
        if self.dock.drawer_container.maximumWidth() > 0:
            w = self.drawer_width
            self.dock.drawer_container.setMinimumWidth(w)
            self.dock.drawer_container.setMaximumWidth(w)
            if not self.dock.is_pinned:
                self.dock.update_unpinned_position()

    def apply_settings(self, auto_collapse: bool, speed: str = "Rápido", delay: str = "Normal (350ms)") -> None:
        """Applies real-time animation settings."""
        self._auto_collapse = auto_collapse
        self._speed_ms = SPEED_MAP.get(speed, 180)
        self._hover_delay_ms = DELAY_MAP.get(delay, 350)
        self.update_anim_duration()

        if self._auto_collapse or self.dock.is_pinned:
            if not self.dock.sidebar.underMouse() and (not self.dock.is_open or self.dock.is_pinned):
                self.do_collapse()
        else:
            self._collapse_timer.stop()
            self._expand_timer.stop()
            if self.dock.sidebar.maximumWidth() == 0:
                self.do_expand()

    def update_anim_duration(self) -> None:
        self._sidebar_anim.setDuration(self._speed_ms)
        self._drawer_anim.setDuration(int(self._speed_ms * 1.2) + 40)

    def inject_pill(self, pill: object) -> None:
        self._pill = pill
        pill.hovered.connect(self._on_pill_hovered)
        pill.left.connect(self._on_pill_left)

    def _on_pill_hovered(self) -> None:
        if not self.dock._is_painting:
            self._expand_timer.start(self._hover_delay_ms)

    def _on_pill_left(self) -> None:
        self._expand_timer.stop()

    def show_pill(self) -> None:
        if self._pill:
            try:
                self._pill.show()
                self._pill.raise_()
            except RuntimeError:
                pass

    def hide_pill(self) -> None:
        if self._pill:
            try:
                self._pill.hide()
                self._pill.raise_()
            except RuntimeError:
                pass

    def do_collapse(self) -> None:
        self._expand_timer.stop()
        current = self.dock.sidebar.width()
        if current == 0 or not self.dock.sidebar.isVisible():
            self.dock.sidebar.hide()
            self.show_pill()
            return
        self._sidebar_anim.stop()
        self._sidebar_anim.setStartValue(current)
        self._sidebar_anim.setEndValue(0)
        self._sidebar_anim.start()

    def do_expand(self) -> None:
        if self.dock._is_painting:
            return
        self._collapse_timer.stop()
        self.hide_pill()
        self.dock.sidebar.show()
        self.dock.sidebar.raise_()
        current = self.dock.sidebar.width()
        if current == self.SIDEBAR_EXPANDED and not self.dock.sidebar.isHidden():
            self.dock.sidebar.setFixedWidth(self.SIDEBAR_EXPANDED)
            return
        self._sidebar_anim.stop()
        self._sidebar_anim.setStartValue(current)
        self._sidebar_anim.setEndValue(self.SIDEBAR_EXPANDED)
        self._sidebar_anim.start()

    def _on_sidebar_anim_value_changed(self, value: int) -> None:
        self.dock.sidebar.setFixedWidth(value)
        if hasattr(self.dock._workspace, "_update_pill_positions"):
            self.dock._workspace._update_pill_positions()

    def _on_sidebar_anim_finished(self) -> None:
        if self.dock.sidebar.width() == 0:
            self.dock.sidebar.hide()
            self.show_pill()
        else:
            self.dock.sidebar.setFixedWidth(self.SIDEBAR_EXPANDED)
            self.hide_pill()
        if hasattr(self.dock._workspace, "_update_pill_positions"):
            self.dock._workspace._update_pill_positions()

    def open_drawer_anim(self) -> None:
        self.dock.drawer_container.show()
        if not self.dock.is_pinned:
            self.dock.drawer_container.raise_()
        target_w = self.drawer_width
        current = self.dock.drawer_container.maximumWidth()
        if current == target_w and self.dock.drawer_container.width() == target_w:
            self.dock.drawer_container.setMinimumWidth(target_w)
            if not self.dock.is_pinned:
                self.dock.update_unpinned_position()
            return
        self._drawer_anim.stop()
        self._drawer_anim.setStartValue(current)
        self._drawer_anim.setEndValue(target_w)
        self._drawer_anim.start()

    def close_drawer_anim(self) -> None:
        current = self.dock.drawer_container.maximumWidth()
        if current == 0:
            self.dock.drawer_container.hide()
            return
        self.dock.drawer_container.setMinimumWidth(0)
        self._drawer_anim.stop()
        self._drawer_anim.setStartValue(current)
        self._drawer_anim.setEndValue(0)
        self._drawer_anim.start()

    def _on_drawer_anim_value_changed(self, value: int) -> None:
        self.dock.drawer_container.setMinimumWidth(value)
        if not self.dock.is_pinned and self.dock.drawer_container.isVisible():
            self.dock.update_unpinned_position()

    def _on_drawer_anim_finished(self) -> None:
        if self.dock.drawer_container.maximumWidth() == 0:
            self.dock.drawer_container.hide()
            for widget in self.dock.drawer_container._panels.values():
                try:
                    widget.hide()
                except RuntimeError:
                    pass
        else:
            target_w = self.drawer_width
            self.dock.drawer_container.setMinimumWidth(target_w)
            self.dock.drawer_container.setMaximumWidth(target_w)
            if not self.dock.is_pinned:
                self.dock.update_unpinned_position()
