"""Brush and Tool synchronization mixin for WorkspaceContainer."""

import logging
from typing import Any
from PySide6 import QtCore, QtGui, QtWidgets

logger = logging.getLogger("Workspace.BrushAdapter")


class WorkspaceBrushMixin:
    """Mixin para controle de ferramentas, cores e parâmetros de traço/brush."""

    def connect_brush_dock(self, dock: Any) -> None:
        """
        Conecta os sinais do BrushSettingsPanel ao renderer do canvas.
        Deve ser chamado pelo plugin de UI após add_panel().
        """
        self._brush_dock = dock

        if hasattr(dock, "colorChanged"):
            dock.colorChanged.connect(self._on_brush_color)
        if hasattr(dock, "sizeChanged"):
            dock.sizeChanged.connect(self._on_brush_size)
        if hasattr(dock, "opacityChanged"):
            dock.opacityChanged.connect(self._on_brush_opacity)
        if hasattr(dock, "pressureChanged"):
            dock.pressureChanged.connect(self._on_brush_pressure)
        if hasattr(dock, "pressureCurvePowerChanged"):
            dock.pressureCurvePowerChanged.connect(self._on_brush_pressure_curve)
        if hasattr(dock, "stabilizerWeightChanged"):
            dock.stabilizerWeightChanged.connect(self._on_brush_stabilizer)
        if hasattr(dock, "spacingChanged"):
            dock.spacingChanged.connect(self._on_brush_spacing)
        if hasattr(dock, "minDensityActiveChanged"):
            dock.minDensityActiveChanged.connect(self._on_min_density_active)
        if hasattr(dock, "minDensityValueChanged"):
            dock.minDensityValueChanged.connect(self._on_min_density_value)
        if hasattr(dock, "contrastChanged"):
            dock.contrastChanged.connect(self._on_brush_contrast)
        if hasattr(dock, "invertHeightChanged"):
            dock.invertHeightChanged.connect(self._on_brush_invert)
        if hasattr(dock, "loadShapeRequested"):
            dock.loadShapeRequested.connect(lambda: self._load_custom_texture(is_shape=True))
        if hasattr(dock, "loadHeightmapRequested"):
            dock.loadHeightmapRequested.connect(lambda: self._load_custom_texture(is_shape=False))

        if hasattr(dock, "toolActivated"):
            dock.toolActivated.connect(self.select_tool, QtCore.Qt.UniqueConnection)
        if hasattr(dock, "toolOptionsChanged"):
            dock.toolOptionsChanged.connect(self._on_tool_settings_changed)

    def _apply_brush_color(self, color: QtGui.QColor) -> None:
        self.canvas_widget._active_draw_color = color
        if hasattr(self.canvas_widget, "set_shape_color"):
            self.canvas_widget.set_shape_color(color)
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend:
            backend.set_brush_color(color.redF(), color.greenF(), color.blueF())
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_brush_color(
                color.redF(), color.greenF(), color.blueF()
            )
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
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend:
            backend.set_brush_size(val)
        if cw.renderer:
            cw.renderer.set_brush_size(val)
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
        if cw.renderer:
            cw.renderer.set_brush_pressure(val)
            cw.update()
        if self._brush_dock:
            self._brush_dock.stroke_preview.update_brush_state(pressure=val)

    def _on_brush_pressure_curve(self, val: float) -> None:
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_pressure_curve_power"):
            backend.set_pressure_curve_power(val)
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_pressure_curve_power(val)
            self.canvas_widget.update()

    def _on_brush_stabilizer(self, weight: float) -> None:
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_stabilizer_weight"):
            backend.set_stabilizer_weight(weight)
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_stabilizer_weight(weight)
            self.canvas_widget.update()

    def _on_brush_spacing(self, factor: float) -> None:
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_brush_spacing"):
            backend.set_brush_spacing(factor)
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_brush_spacing(factor)
            self.canvas_widget.update()
        if self._brush_dock:
            self._brush_dock.stroke_preview.update_brush_state(spacing=factor)

    def _on_brush_opacity(self, factor: float) -> None:
        cw = self.canvas_widget
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_brush_opacity"):
            backend.set_brush_opacity(factor)
        if cw.renderer:
            cw.renderer.set_brush_opacity(factor)
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
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_min_density_active"):
            backend.set_min_density_active(active)
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_min_density_active(active)
            self.canvas_widget.update()

    def _on_min_density_value(self, weight: float) -> None:
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_min_density_value"):
            backend.set_min_density_value(weight)
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_min_density_value(weight)
            self.canvas_widget.update()

    def _on_brush_contrast(self, val: float) -> None:
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_brush_contrast"):
            backend.set_brush_contrast(val)
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_brush_contrast(val)
            self.canvas_widget.update()
        if self._brush_dock:
            hardness = min(0.99, max(0.01, val / 3.0))
            self._brush_dock.stroke_preview.update_brush_state(hardness=hardness)

    def _on_brush_invert(self, invert: bool) -> None:
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_brush_invert_height"):
            backend.set_brush_invert_height(invert)
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_brush_invert_height(invert)
            self.canvas_widget.update()

    def _load_custom_texture(self, is_shape: bool) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Selecionar Imagem de Textura",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.tga)",
        )
        if not file_path:
            return

        image = QtGui.QImage(file_path)
        if image.isNull():
            QtWidgets.QMessageBox.warning(
                self, "Erro", "Não foi possível carregar a imagem selecionada."
            )
            return

        image    = image.convertToFormat(QtGui.QImage.Format_RGBA8888)
        width    = image.width()
        height   = image.height()
        ptr      = image.constBits()
        px_bytes = ptr.tobytes()

        renderer = self.canvas_widget.renderer
        if renderer:
            if is_shape:
                renderer.set_shape_texture(px_bytes, width, height)
            else:
                renderer.set_heightmap_texture(px_bytes, width, height)

        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend:
            if is_shape and hasattr(backend, "set_shape_texture"):
                backend.set_shape_texture(px_bytes, width, height)
            elif not is_shape and hasattr(backend, "set_heightmap_texture"):
                backend.set_heightmap_texture(px_bytes, width, height)
                if hasattr(backend, "set_brush_grain_enabled"):
                    backend.set_brush_grain_enabled(True)

        if self._brush_dock:
            self._brush_dock.update_thumbnail(is_shape, file_path)

        self.canvas_widget.update()

    def _on_stroke_finished_sync_previews(self) -> None:
        try:
            from ui.core.engine.registry import EngineRegistry
            backend = EngineRegistry.instance().get_backend()
            facade = getattr(backend, "_facade", None)

            if hasattr(self, "_layers_panel") and self._layers_panel and hasattr(self._layers_panel, "layer_manager"):
                lm = self._layers_panel.layer_manager
                if lm and lm.get_active_layer() and facade:
                    lm.update_thumbnail(lm.get_active_layer().uid, facade)

            if hasattr(self, "_navigator_panel") and self._navigator_panel:
                if hasattr(self.canvas_widget, "get_canvas_image"):
                    canvas_img = self.canvas_widget.get_canvas_image()
                    if canvas_img and not canvas_img.isNull():
                        self._navigator_panel.set_artwork(canvas_img)
                elif backend and hasattr(backend, "get_qimage"):
                    qimg = backend.get_qimage()
                    if qimg and not qimg.isNull():
                        self._navigator_panel.set_artwork(qimg)
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
            self.canvas_widget._eyedrop_settings.update(settings)
        elif tool_id == "bucket":
            self.canvas_widget._bucket_settings.update(settings)
        elif tool_id == "wand":
            self.canvas_widget._wand_settings.update(settings)
        elif tool_id in ("rect_select", "ellipse_select"):
            if not hasattr(self.canvas_widget, "_geom_select_settings"):
                self.canvas_widget._geom_select_settings = {}
            self.canvas_widget._geom_select_settings.update(settings)
        elif tool_id == "lasso":
            if not hasattr(self.canvas_widget, "_lasso_settings"):
                self.canvas_widget._lasso_settings = {}
            self.canvas_widget._lasso_settings.update(settings)
        elif tool_id.startswith("shape") or tool_id == "shapes":
            self.canvas_widget.set_shape_settings(settings)
            if hasattr(self, "left_dock") and hasattr(self.left_dock, "brush_panel"):
                bp = self.left_dock.brush_panel
                if hasattr(bp, "shapes_options_widget") and "shape_type" in settings:
                    bp.shapes_options_widget.shape_dropdown.set_shape(settings["shape_type"])
            if hasattr(self, "secondary_toolbar") and self.secondary_toolbar:
                if "shape_type" in settings:
                    self.secondary_toolbar.shape_dropdown_h.set_shape(settings["shape_type"])
                    self.secondary_toolbar.shape_dropdown_v.set_shape(settings["shape_type"])
        elif tool_id == "transform":
            self.canvas_widget._transform_interp_mode = settings.get("interp_mode", 2)
            self.canvas_widget._transform_lock_aspect = settings.get("lock_aspect", False)

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
