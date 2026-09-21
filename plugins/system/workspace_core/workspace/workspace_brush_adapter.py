"""Brush and Tool synchronization mixin for WorkspaceContainer."""

import logging
from typing import Any
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.tool_settings import normalize_tool_settings

logger = logging.getLogger("Workspace.BrushAdapter")


class WorkspaceBrushMixin:
    """Mixin para controle de ferramentas, cores e parâmetros de traço/brush."""

    def connect_brush_dock(self, dock: Any, panel_id: str = "brush_settings") -> None:
        """
        Conecta os sinais do BrushSettingsPanel ao renderer do canvas.
        Deve ser chamado pelo plugin de UI após add_panel().
        """
        self._brush_dock = dock
        if getattr(dock, "_lumenia_brush_connected", False):
            return
        dock._lumenia_brush_connected = True

        if hasattr(dock, "colorChanged"):
            self._bind_panel_signal(panel_id, dock.colorChanged, self._on_brush_color)
        if hasattr(dock, "sizeChanged"):
            self._bind_panel_signal(panel_id, dock.sizeChanged, self._on_brush_size)
        if hasattr(dock, "opacityChanged"):
            self._bind_panel_signal(panel_id, dock.opacityChanged, self._on_brush_opacity)
        if hasattr(dock, "pressureChanged"):
            self._bind_panel_signal(panel_id, dock.pressureChanged, self._on_brush_pressure)
        if hasattr(dock, "pressureCurvePowerChanged"):
            self._bind_panel_signal(panel_id, dock.pressureCurvePowerChanged, self._on_brush_pressure_curve)
        if hasattr(dock, "stabilizerWeightChanged"):
            self._bind_panel_signal(panel_id, dock.stabilizerWeightChanged, self._on_brush_stabilizer)
        if hasattr(dock, "spacingChanged"):
            self._bind_panel_signal(panel_id, dock.spacingChanged, self._on_brush_spacing)
        if hasattr(dock, "minDensityActiveChanged"):
            self._bind_panel_signal(panel_id, dock.minDensityActiveChanged, self._on_min_density_active)
        if hasattr(dock, "minDensityValueChanged"):
            self._bind_panel_signal(panel_id, dock.minDensityValueChanged, self._on_min_density_value)
        if hasattr(dock, "contrastChanged"):
            self._bind_panel_signal(panel_id, dock.contrastChanged, self._on_brush_contrast)
        if hasattr(dock, "invertHeightChanged"):
            self._bind_panel_signal(panel_id, dock.invertHeightChanged, self._on_brush_invert)
        if hasattr(dock, "loadShapeRequested"):
            self._bind_panel_signal(panel_id, dock.loadShapeRequested, lambda: self._load_custom_texture(is_shape=True))
        if hasattr(dock, "loadHeightmapRequested"):
            self._bind_panel_signal(panel_id, dock.loadHeightmapRequested, lambda: self._load_custom_texture(is_shape=False))

        if hasattr(dock, "toolActivated"):
            self._bind_panel_signal(panel_id, dock.toolActivated, self.select_tool, unique=True)
        if hasattr(dock, "toolOptionsChanged"):
            self._bind_panel_signal(panel_id, dock.toolOptionsChanged, self._on_tool_settings_changed)

    def disconnect_brush_dock(self, dock: Any, panel_id: str = "brush_settings") -> None:
        """Desfaz todas as conexões criadas para um BrushSettingsPanel."""
        self._disconnect_panel_signals(panel_id)
        try:
            dock._lumenia_brush_connected = False
        except RuntimeError:
            pass
        if self._brush_dock is dock:
            self._brush_dock = None

    def _get_backend(self):
        from ui.core.engine.registry import EngineRegistry
        return EngineRegistry.instance().get_backend()

    def _apply_brush_color(self, color: QtGui.QColor) -> None:
        if hasattr(self.canvas_widget, "active_color"):
            self.canvas_widget.active_color = color
        else:
            self.canvas_widget._active_draw_color = color
        if hasattr(self.canvas_widget, "set_shape_color"):
            self.canvas_widget.set_shape_color(color)
        backend = self._get_backend()
        if backend:
            backend.set_brush_color(color.redF(), color.greenF(), color.blueF())
        self.canvas_widget.update()

    def _on_brush_color(self, color: QtGui.QColor) -> None:
        self._saved_color = color
        self._apply_brush_color(color)
        if self._brush_dock and hasattr(self._brush_dock, "set_color"):
            self._brush_dock.set_color(color)
        if hasattr(self, "secondary_toolbar") and self.secondary_toolbar:
            self.secondary_toolbar.set_captured_color(color)
        if hasattr(self, "_color_panel") and self._color_panel and hasattr(self._color_panel, "set_color"):
            self._color_panel.set_color(color)

    def _on_brush_size(self, val: float) -> None:
        cw = self.canvas_widget
        cw.brush_size = val
        backend = self._get_backend()
        if backend:
            backend.set_brush_size(val)
        cw.update()
        if self._brush_dock:
            d = self._brush_dock
            if hasattr(d, "qs_size"):
                d.qs_size.blockSignals(True)
                d.qs_size.setValue(int(val))
                d.qs_size.blockSignals(False)
            if hasattr(d, "_adv_panel") and d._adv_panel and hasattr(d._adv_panel, "slider_size"):
                d._adv_panel.slider_size.blockSignals(True)
                d._adv_panel.slider_size.setValue(val)
                d._adv_panel.slider_size.blockSignals(False)
            c = self._saved_color
            if hasattr(d, "stroke_preview"):
                opac_val = (d.qs_opacity.value() / 100.0) if hasattr(d, "qs_opacity") else 1.0
                d.stroke_preview.update_brush_state(
                    size=val,
                    opacity=opac_val,
                    color=[c.redF(), c.greenF(), c.blueF()],
                )

    def _on_brush_pressure(self, val: float) -> None:
        cw = self.canvas_widget
        cw.manual_pressure = val
        backend = self._get_backend()
        if backend:
            backend.set_brush_pressure(val)
        cw.update()
        if self._brush_dock:
            self._brush_dock.stroke_preview.update_brush_state(pressure=val)

    def _on_brush_pressure_curve(self, val: float) -> None:
        backend = self._get_backend()
        if backend:
            backend.set_pressure_curve_power(val)
        self.canvas_widget.update()

    def _on_brush_stabilizer(self, weight: float) -> None:
        backend = self._get_backend()
        if backend:
            backend.set_stabilizer_weight(weight)
        self.canvas_widget.update()

    def _on_brush_spacing(self, factor: float) -> None:
        backend = self._get_backend()
        if backend:
            backend.set_brush_spacing(factor)
        self.canvas_widget.update()
        if self._brush_dock:
            self._brush_dock.stroke_preview.update_brush_state(spacing=factor)

    def _on_brush_opacity(self, factor: float) -> None:
        cw = self.canvas_widget
        backend = self._get_backend()
        if backend:
            backend.set_brush_opacity(factor)
        cw.update()
        if self._brush_dock:
            d = self._brush_dock
            val = int(factor * 100.0)
            d.qs_opacity.blockSignals(True)
            d.qs_opacity.setValue(val)
            d.qs_opacity.blockSignals(False)
            if d._adv_panel:
                d._adv_panel.slider_opacity.blockSignals(True)
                d._adv_panel.slider_opacity.setValue(val)
                d._adv_panel.slider_opacity.blockSignals(False)
            d.stroke_preview.update_brush_state(opacity=factor)

    def _on_min_density_active(self, active: bool) -> None:
        backend = self._get_backend()
        if backend:
            backend.set_min_density_active(active)
        self.canvas_widget.update()

    def _on_min_density_value(self, weight: float) -> None:
        backend = self._get_backend()
        if backend:
            backend.set_min_density_value(weight)
        self.canvas_widget.update()

    def _on_brush_contrast(self, val: float) -> None:
        backend = self._get_backend()
        if backend:
            backend.set_brush_contrast(val)
        self.canvas_widget.update()
        if self._brush_dock:
            hardness = min(0.99, max(0.01, val / 3.0))
            self._brush_dock.stroke_preview.update_brush_state(hardness=hardness)

    def _on_brush_invert(self, invert: bool) -> None:
        backend = self._get_backend()
        if backend:
            backend.set_brush_invert_height(invert)
        self.canvas_widget.update()

    def _load_custom_texture(self, is_shape: bool) -> None:
        from .brush_texture_io import BrushTextureIO
        BrushTextureIO.load_and_apply_to_workspace(self, is_shape)

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

            if tool in ("brush", "bucket"):
                self._apply_brush_color(self._saved_color)
            elif tool == "eraser":
                self._apply_brush_color(QtGui.QColor("#ffffff"))

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

    def _on_canvas_color_picked(self, color: QtGui.QColor) -> None:
        self._saved_color = color
        self._apply_brush_color(color)
        if hasattr(self, "_brush_dock") and self._brush_dock:
            self._brush_dock.set_color(color)
        if hasattr(self, "_color_panel") and self._color_panel and hasattr(self._color_panel, "set_color"):
            self._color_panel.set_color(color)
        if hasattr(self, "secondary_toolbar") and self.secondary_toolbar:
            self.secondary_toolbar.set_captured_color(color)

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
                },
            )
            self.canvas_widget.transform_ctrl.interp_mode = normalized["interp_mode"]
            self.canvas_widget.transform_ctrl.lock_aspect = normalized["lock_aspect"]

    def sync_all_properties(self) -> None:
        if not self._brush_dock:
            return
        d = self._brush_dock
        if hasattr(d, "qs_size"):
            self._on_brush_size(float(d.qs_size.value()))
        if hasattr(d, "qs_opacity"):
            self._on_brush_opacity(d.qs_opacity.value() / 100.0)
        if hasattr(d, "qs_hardness"):
            val = float(d.qs_hardness.value())
            contrast = (val / 100.0) * 3.0
            self._on_brush_contrast(contrast)
        if hasattr(d, "qs_spacing"):
            self._on_brush_spacing(d.qs_spacing.value() / 100.0)
        if hasattr(d, "qs_stabilizer"):
            self._on_brush_stabilizer(d.qs_stabilizer.value() / 100.0)
        self._apply_brush_color(self._saved_color)
