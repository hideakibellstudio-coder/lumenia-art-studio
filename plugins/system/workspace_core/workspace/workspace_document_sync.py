"""Document and Camera synchronization mixin for WorkspaceContainer."""

import math
from typing import Any, TYPE_CHECKING
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.document.document import Document

if TYPE_CHECKING:
    from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget


class WorkspaceDocSyncMixin:
    """Mixin para sincronização de câmera, viewport, documentos ativos e navigator."""

    def _on_document_geometry_changed(self, width, height):
        self.canvas_w, self.canvas_h = width, height
        self.canvas_widget.canvas_w, self.canvas_widget.canvas_h = width, height
        if self._properties_dock:
            self._properties_dock.navigator.set_canvas_size(width, height)
        if getattr(self, "_navigator_panel", None):
            self._navigator_panel.set_canvas_size(width, height)
        self._sync_navigator_to_canvas()
        self.canvas_widget.update()

    def connect_properties_dock(self, dock: Any, panel_id: str = "properties") -> None:
        """
        Conecta os sinais do navigator (PropertiesDock) à câmera do canvas.
        Deve ser chamado pelo plugin de UI após add_panel().
        """
        self._properties_dock = dock
        self._bind_panel_signal(panel_id, dock.navigator.camera_changed_by_user, self._set_camera_from_navigator)
        if hasattr(dock.navigator, "flip_changed_by_user"):
            self._bind_panel_signal(panel_id, dock.navigator.flip_changed_by_user, self._set_flip_from_navigator)
        self._bind_panel_signal(panel_id, dock.navigator.request_global_fit_view, self.reset_view)
        self._bind_panel_signal(panel_id, self.canvas_widget.cameraChanged, self._on_canvas_camera_changed)

    def disconnect_properties_dock(self, dock: Any, panel_id: str = "properties") -> None:
        """Desfaz a sincronização de câmera antes de destruir o PropertiesDock."""
        self._disconnect_panel_signals(panel_id)
        if self._properties_dock is dock:
            self._properties_dock = None

    def _sync_navigator_to_canvas(self) -> None:
        """Lê o estado atual da câmera do canvas e empurra para o navigator."""
        cw = self.canvas_widget
        self._on_canvas_camera_changed(
            cw.zoom, cw.pan_x, cw.pan_y, cw.rotation,
            float(max(1, cw.width())), float(max(1, cw.height()))
        )

    def _set_camera_from_navigator(
        self, zoom: float, norm_x: float, norm_y: float, rotation: float
    ) -> None:
        """Recebe coordenadas normalizadas do navigator e aplica ao canvas."""
        cw: "RenderWidget" = self.canvas_widget
        cw_w = float(getattr(cw, "canvas_w", self.canvas_w))
        cw_h = float(getattr(cw, "canvas_h", self.canvas_h))
        cw.zoom     = zoom
        cw.pan_x    = (0.5 - norm_x) * zoom * cw_w
        cw.pan_y    = (0.5 - norm_y) * zoom * cw_h
        cw.rotation = rotation

        if cw.input_adapter:
            rot_rad = math.radians(rotation)
            cw.input_adapter.update_view(cw.zoom, cw.pan_x, cw.pan_y, rot_rad)

        self.zoomChanged.emit(cw.zoom)
        cw.update()

    def _set_flip_from_navigator(self, flip_x: bool, flip_y: bool) -> None:
        """Recebe estado de espelhamento do navigator e aplica ao canvas."""
        cw: "RenderWidget" = self.canvas_widget
        cw.flip_x = bool(flip_x)
        cw.flip_y = bool(flip_y)
        cw.update()

    def _on_canvas_camera_changed(
        self,
        zoom: float, pan_x: float, pan_y: float, rotation: float,
        view_w: float, view_h: float,
    ) -> None:
        """Mapeia parâmetros de câmera para coordenadas normalizadas do navigator."""
        document: Document = self._dm.active_document()
        if document is not None:
            document.zoom, document.pan_x, document.pan_y, document.rotation = zoom, pan_x, pan_y, rotation
        cw_w = float(getattr(self.canvas_widget, "canvas_w", self.canvas_w))
        cw_h = float(getattr(self.canvas_widget, "canvas_h", self.canvas_h))
        norm_x  = 0.5 - pan_x / (zoom * cw_w)
        norm_y  = 0.5 - pan_y / (zoom * cw_h)
        ratio_w = view_w / (zoom * cw_w)
        ratio_h = view_h / (zoom * cw_h)
        flip_h = bool(getattr(self.canvas_widget, "flip_x", False))
        flip_v = bool(getattr(self.canvas_widget, "flip_y", False))

        if self._properties_dock:
            self._properties_dock.navigator.update_viewport(
                zoom, norm_x, norm_y, rotation, flip_h, flip_v, ratio_w, ratio_h
            )
        if hasattr(self, "_navigator_panel") and self._navigator_panel:
            self._navigator_panel.update_viewport(
                zoom, norm_x, norm_y, rotation, flip_h, flip_v, ratio_w, ratio_h
            )

    def refresh_document_state(self, doc):

        self._on_active_document_changed(doc, capture_previous=False)

    def _on_active_document_changed(self, doc: Document, *, capture_previous=True) -> None:
        """
        Chamado pelo DocumentManager quando o documento ativo muda.
        Salva o estado do doc anterior e restaura o contexto C++, câmera, papel e guias do novo doc.
        """
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()

        previous = getattr(self, "_geometry_document", None)
        if previous is not None:
            previous.geometry_changed.disconnect(self._on_document_geometry_changed)
        self._geometry_document = doc
        if doc is not None:
            doc.geometry_changed.connect(self._on_document_geometry_changed)

        # Cancela qualquer transformação ativa em andamento antes de trocar
        if hasattr(self.canvas_widget, "transform_ctrl") and self.canvas_widget.transform_ctrl.active:
            self.canvas_widget.transform_ctrl.cancel()

        if capture_previous and self._last_active_doc_uid:
            last_doc: Document = self._dm.get_document(self._last_active_doc_uid)
            if last_doc:
                last_doc.zoom        = self.canvas_widget.zoom
                last_doc.pan_x       = self.canvas_widget.pan_x
                last_doc.pan_y       = self.canvas_widget.pan_y
                last_doc.rotation    = self.canvas_widget.rotation
                last_doc.saved_color = self._saved_color
                last_doc.paper_color = getattr(self.canvas_widget, "paper_color", QtGui.QColor(255, 255, 255))
                last_doc.paper_visible = getattr(self.canvas_widget, "paper_visible", True)
                if hasattr(self.canvas_widget, "geometry_ctrl"):
                    last_doc.guide_state = dict(self.canvas_widget.geometry_ctrl.guide_state)
                    last_doc.sym_state = dict(self.canvas_widget.geometry_ctrl.sym_state)

        self._last_active_doc_uid = doc.uid if doc else None

        if not doc:
            self.canvas_widget.setEnabled(False)
            if self._properties_dock:
                self._properties_dock.layers.set_layer_manager(None)
                self._properties_dock.navigator.set_has_document(False)
            if hasattr(self, "_layers_panel") and self._layers_panel:
                self._layers_panel.set_layer_manager(None)
            if hasattr(self, "_navigator_panel") and self._navigator_panel:
                self._navigator_panel.set_has_document(False)
            if self.canvas_widget.renderer:
                self.canvas_widget.renderer.clear_canvas()
            self.canvas_widget.update()
            return

        # Sincroniza o contexto C++ do motor nativo para a facade deste documento
        if backend and hasattr(backend, "set_active_document_context"):
            backend.set_active_document_context(doc.uid, doc.width, doc.height)
            backend.set_canvas_paper_state(doc.paper_color, doc.paper_visible,
                                           doc.paper_texture_id, doc.paper_texture_enabled,
                                           reset_texture=False)

        self.canvas_w = doc.width
        self.canvas_h = doc.height
        self.canvas_widget.setEnabled(True)
        self.canvas_widget.canvas_w = doc.width
        self.canvas_widget.canvas_h = doc.height

        # Restaura papel e preenchimentos deste documento
        self.canvas_widget.paper_color = getattr(doc, "paper_color", QtGui.QColor(255, 255, 255))
        self.canvas_widget.paper_visible = getattr(doc, "paper_visible", True)

        if hasattr(self.canvas_widget, "geometry_ctrl"):
            self.canvas_widget.geometry_ctrl.load_document_state(doc)

        self.viewport_container.sync_active_tab(doc.uid)

        if doc.zoom == 1.0 and doc.pan_x == 0.0 and doc.pan_y == 0.0:
            self.canvas_widget.center_canvas()
        else:
            self.canvas_widget.zoom     = doc.zoom
            self.canvas_widget.pan_x    = doc.pan_x
            self.canvas_widget.pan_y    = doc.pan_y
            self.canvas_widget.rotation = doc.rotation

        color = doc.saved_color if doc.saved_color else self._saved_color
        self._saved_color = color
        self._apply_brush_color(color)
        if hasattr(self, "_color_panel") and self._color_panel and hasattr(self._color_panel, "set_color"):
            self._color_panel.set_color(color)
        elif self._brush_dock and hasattr(self._brush_dock, "set_color"):
            self._brush_dock.set_color(color)
        elif self._brush_dock and hasattr(self._brush_dock, "color_wheel"):
            self._brush_dock.color_wheel.set_color(color)

        if self.canvas_widget.input_adapter:
            rot_rad = math.radians(doc.rotation)
            self.canvas_widget.input_adapter.update_view(
                doc.zoom, doc.pan_x, doc.pan_y, rot_rad
            )
        self.canvas_widget.update()

        self.zoomChanged.emit(doc.zoom)
        self._sync_navigator_to_canvas()

        if self._properties_dock:
            self._properties_dock.layers.set_layer_manager(doc.layer_manager)
            self._properties_dock.navigator.set_canvas_size(doc.width, doc.height)
            self._properties_dock.navigator.set_has_document(True)
        if hasattr(self, "_layers_panel") and self._layers_panel:
            self._layers_panel.set_layer_manager(doc.layer_manager)
            if hasattr(self._layers_panel, "paper_widget"):
                pw = self._layers_panel.paper_widget
                p_col = getattr(doc, "paper_color", QtGui.QColor(255, 255, 255, 255))
                p_vis = getattr(doc, "paper_visible", True)
                p_tex = getattr(doc, "paper_texture_id", 0)
                p_ena = getattr(doc, "paper_texture_enabled", False)
                pw.set_paper_state(color=p_col, visible=p_vis, preset_id=p_tex, enabled=p_ena,
                                   scale=doc.paper_scale, contrast=doc.paper_contrast,
                                   invert=doc.paper_invert, sync=False)
        if hasattr(self, "_navigator_panel") and self._navigator_panel:
            self._navigator_panel.set_canvas_size(doc.width, doc.height)
            self._navigator_panel.set_has_document(True)

        if doc and hasattr(doc, "layer_manager"):
            act_layer = doc.layer_manager.get_active_layer()
            if act_layer and act_layer in doc.layer_manager.layers:
                act_idx = doc.layer_manager.layers.index(act_layer)
                from ui.core.engine.registry import EngineRegistry
                b = EngineRegistry.instance().get_backend()
                if b and hasattr(b, "select_layer"):
                    b.select_layer(act_idx)

        active_color = getattr(self, "_saved_color", QtGui.QColor(0, 0, 0))
        self._apply_brush_color(active_color)
        if hasattr(self, "_brush_dock") and self._brush_dock and hasattr(self._brush_dock, "preset_combo"):
            combo = self._brush_dock.preset_combo
            active_tool = getattr(self.canvas_widget, "active_tool", "brush")
            current_preset = getattr(combo, "_active_preset", "Pincel Redondo")
            current_data = combo._tool_preset_state.get(active_tool) or combo._tool_preset_state.get("brush")
            if current_data:
                combo._apply_preset_backend(current_preset, current_data)

    def _on_document_closed_cleanup(self, uid: str) -> None:
        """Chamado quando um documento é fechado para liberar memória C++ imediatamente."""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "close_document_context"):
            backend.close_document_context(uid)
