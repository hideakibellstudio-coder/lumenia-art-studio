"""Ferramenta ativa e opções de ferramenta do WorkspaceContainer.

Desde 2026-09-24 este mixin não trata mais de cor nem de parâmetros do
pincel: isso é do BrushState (ui/core/state), aplicado ao motor pelo
BrushEngineSync e ao canvas pelo CanvasBrushBinding. O que sobrou aqui é a
seleção de ferramenta e o roteamento das opções de ferramenta para o canvas.
"""

import logging
from typing import Any
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.tool_settings import normalize_tool_settings

logger = logging.getLogger("Workspace.BrushAdapter")


class WorkspaceBrushMixin:
    """Seleção de ferramenta e roteamento das opções de ferramenta."""

    def connect_brush_dock(self, dock: Any, panel_id: str = "brush_settings") -> None:
        """Liga os sinais de ferramenta do painel de pincel ao workspace."""
        self._brush_dock = dock
        self._bind_panel_signal(panel_id, dock.toolActivated, self.select_tool, unique=True)
        self._bind_panel_signal(panel_id, dock.toolOptionsChanged, self._on_tool_settings_changed)

    def disconnect_brush_dock(self, dock: Any, panel_id: str = "brush_settings") -> None:
        """Desfaz as conexões criadas por connect_brush_dock."""
        self._disconnect_panel_signals(panel_id)
        if self._brush_dock is dock:
            self._brush_dock = None

    def _get_backend(self):
        from ui.core.engine.registry import EngineRegistry
        return EngineRegistry.instance().get_backend()

    def _on_stroke_finished_sync_previews(self) -> None:
        if not hasattr(self, "_preview_sync_timer"):
            self._preview_sync_timer = QtCore.QTimer(self)
            self._preview_sync_timer.setSingleShot(True)
            self._preview_sync_timer.timeout.connect(self._do_sync_previews)
        self._preview_sync_timer.start(100)

    def _do_sync_previews(self) -> None:
        try:
            backend = self._get_backend()
            if not backend:
                return
            if hasattr(self, "_navigator_panel") and self._navigator_panel:
                qimg = backend.get_qimage()
                if qimg and not qimg.isNull():
                    thumb = qimg.scaled(320, 240, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
                    self._navigator_panel.set_artwork(thumb)
            # Emit thumbnail_updated for all layers so the layers panel
            # can refresh real pixel thumbnails after strokes, undo/redo, etc.
            from ui.core.document.manager import DocumentManager
            doc = DocumentManager.instance().active_document()
            if doc:
                for layer in doc.layer_manager.layers:
                    doc.layer_manager.thumbnail_updated.emit(layer.uid)
        except Exception as e:
            logger.debug(f"[WorkspaceContainer] Erro ao sincronizar previews: {e}")

    def select_tool(self, tool: str) -> None:
        if getattr(self, "_is_selecting_tool", False):
            return

        self._is_selecting_tool = True
        try:
            from .floating_toolbar import TOOL_META

            self._current_tool = tool
            if hasattr(self, "canvas_widget"):
                if getattr(self.canvas_widget, "active_tool", None) == "text" and tool != "text":
                    self.canvas_widget.commit_text_overlay()
                self.canvas_widget.active_tool = tool
                if hasattr(self.canvas_widget, "_update_cursor_shape"):
                    self.canvas_widget._update_cursor_shape()

            if hasattr(self, "_brush_dock") and self._brush_dock:
                self._brush_dock.set_tool_active(tool)

            if hasattr(self, "floating_toolbar") and self.floating_toolbar:
                self.floating_toolbar.select_tool(tool, notify=False, animate=False)

            if hasattr(self, "secondary_toolbar") and self.secondary_toolbar:
                self.secondary_toolbar.set_tool(tool)
                self.update_toolbar_position()

            win = self.window()
            if hasattr(win, "tool_sidebar") and win.tool_sidebar:
                if tool == "brush":
                    win.tool_sidebar.action_brush.setChecked(True)
                    win.tool_sidebar.action_eraser.setChecked(False)
                    if hasattr(win.tool_sidebar, "action_shapes"):
                        win.tool_sidebar.action_shapes.setChecked(False)
                elif tool == "eraser":
                    win.tool_sidebar.action_brush.setChecked(False)
                    win.tool_sidebar.action_eraser.setChecked(True)
                    if hasattr(win.tool_sidebar, "action_shapes"):
                        win.tool_sidebar.action_shapes.setChecked(False)
                elif tool.startswith("shape") or tool == "shapes":
                    win.tool_sidebar.action_brush.setChecked(False)
                    win.tool_sidebar.action_eraser.setChecked(False)
                    if hasattr(win.tool_sidebar, "action_shapes"):
                        win.tool_sidebar.action_shapes.setChecked(True)

            if tool == "transform":
                self.canvas_widget.start_transform_mode()
            elif getattr(self.canvas_widget, "_transform_active", False):
                self.canvas_widget.commit_transform()

            meta = TOOL_META.get(tool, {"name": tool.capitalize(), "implemented": False})
            if not meta.get("implemented", False):
                self._on_status_notification(f"Ferramenta '{meta['name']}' em desenvolvimento.")
            else:
                self._on_status_notification(f"Ferramenta ativa: {meta['name']}")
        finally:
            self._is_selecting_tool = False

    def _on_tool_settings_changed(self, tool_id: str, settings: dict) -> None:
        if tool_id == "eyedrop":
            target = self.canvas_widget._eyedrop_settings
            target.update(normalize_tool_settings(tool_id, settings, target))
        elif tool_id == "bucket":
            target = self.canvas_widget._bucket_settings
            target.update(normalize_tool_settings(tool_id, settings, target))
        elif tool_id == "wand":
            target = self.canvas_widget._wand_settings
            target.update(normalize_tool_settings(tool_id, settings, target))
        elif tool_id in ("rect_select", "ellipse_select"):
            target = self.canvas_widget._geom_select_settings
            target.update(normalize_tool_settings(tool_id, settings, target))
        elif tool_id == "lasso":
            target = self.canvas_widget._lasso_settings
            target.update(normalize_tool_settings(tool_id, settings, target))
        elif tool_id.startswith("shape") or tool_id == "shapes":
            target = self.canvas_widget._shape_settings
            normalized = normalize_tool_settings("shapes", settings, target)
            self.canvas_widget.set_shape_settings(normalized)
            if hasattr(self, "left_dock") and hasattr(self.left_dock, "brush_panel"):
                bp = self.left_dock.brush_panel
                if hasattr(bp, "shapes_options_widget") and "shape_type" in normalized:
                    bp.shapes_options_widget.shape_dropdown.set_shape(normalized["shape_type"])
            if hasattr(self, "secondary_toolbar") and self.secondary_toolbar:
                if "shape_type" in normalized:
                    self.secondary_toolbar.shape_dropdown_h.set_shape(normalized["shape_type"])
                    self.secondary_toolbar.shape_dropdown_v.set_shape(normalized["shape_type"])
        elif tool_id == "text":
            target = self.canvas_widget._text_settings
            self.canvas_widget.set_text_settings(normalize_tool_settings("text", settings, target))
        elif tool_id == "transform":
            normalized = normalize_tool_settings(
                tool_id,
                settings,
                {
                    "interp_mode": self.canvas_widget.transform_ctrl.interp_mode,
                    "lock_aspect": self.canvas_widget.transform_ctrl.lock_aspect,
                    "distort": self.canvas_widget.transform_ctrl.distort,
                },
            )
            self.canvas_widget.transform_ctrl.interp_mode = normalized["interp_mode"]
            self.canvas_widget.transform_ctrl.lock_aspect = normalized["lock_aspect"]
            self.canvas_widget.transform_ctrl.distort = normalized["distort"]
