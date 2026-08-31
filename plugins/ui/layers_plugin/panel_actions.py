"""Auxiliary action handlers for LayersPanel (Filters, Popups, Renaming, Moves, Duplicates)."""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect
from .panel_rename_popup import LayerRenamePopup
from .panel_sync import refresh_layer_thumbnail


def add_filter_layer(panel, filter_type=None):
    """Abre o diálogo de ajuste de filtros e gerencia o preview em tempo real."""
    from ui.core.screens.filters import FilterAdjustmentDialog
    dialog = FilterAdjustmentDialog(panel)
    panel._preview_filter_idx = -1

    def _repaint():
        for top_w in QApplication.topLevelWidgets():
            if hasattr(top_w, "workspace") and hasattr(top_w.workspace, "canvas_widget"):
                top_w.workspace.canvas_widget.update()
            elif hasattr(top_w, "canvas_widget"):
                top_w.canvas_widget.update()

    def on_preview_changed(name, type_id, params):
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if not backend or not hasattr(backend, "add_filter_layer"):
            return

        if panel._preview_filter_idx < 0:
            panel._preview_filter_idx = backend.add_filter_layer(f"Preview {name}", type_id)
        else:
            curr_type = backend.get_filter_type(panel._preview_filter_idx)
            if curr_type != type_id:
                backend.remove_layer(panel._preview_filter_idx)
                panel._preview_filter_idx = backend.add_filter_layer(f"Preview {name}", type_id)

        if panel._preview_filter_idx >= 0:
            backend.set_filter_params(panel._preview_filter_idx, params)
        _repaint()

    def on_preview_cancelled():
        if panel._preview_filter_idx >= 0:
            from ui.core.engine.registry import EngineRegistry
            backend = EngineRegistry.instance().get_backend()
            if backend:
                backend.remove_layer(panel._preview_filter_idx)
            panel._preview_filter_idx = -1
            _repaint()

    def on_filter_created(name, type_id, params):
        if panel._preview_filter_idx >= 0:
            from ui.core.engine.registry import EngineRegistry
            backend = EngineRegistry.instance().get_backend()
            if backend:
                backend.remove_layer(panel._preview_filter_idx)
            panel._preview_filter_idx = -1
        create_filter_layer(panel, name, type_id, params)

    dialog.preview_changed.connect(on_preview_changed)
    dialog.preview_cancelled.connect(on_preview_cancelled)
    dialog.filter_created.connect(on_filter_created)
    dialog.exec()


def create_filter_layer(panel, name: str, type_id: int, params: list):
    """Instancia a camada de ajuste no backend nativo e no LayerManager."""
    panel._updating_selection = True
    try:
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend:
            new_idx = backend.add_filter_layer(name, type_id)
            if new_idx >= 0:
                backend.set_filter_params(new_idx, params)

        panel.layer_manager.add_layer(name)
        active = panel.layer_manager.get_active_layer()
        if active:
            active.is_filter = True
            panel._select_uid_in_view(active.uid)
            panel._sync_to_native_engine("select")
        panel._show_status(f"Camada de Ajuste '{name}' criada com sucesso.")
    finally:
        panel._updating_selection = False


def open_edit_filter_popup(panel, uid: int = None):
    """Abre o popup de edição de parâmetros para uma camada de ajuste existente."""
    if uid is None:
        active = panel.layer_manager.get_active_layer()
        if not active:
            return
        uid = active.uid

    layer = panel.layer_manager.get_layer_by_uid(uid)
    if not layer:
        return

    from ui.core.engine.registry import EngineRegistry
    backend = EngineRegistry.instance().get_backend()
    if not backend:
        return

    layer_list = panel.layer_manager.layers
    try:
        c_idx = layer_list.index(layer)
    except ValueError:
        return

    if not backend.is_filter_layer(c_idx):
        panel._show_status(f"A camada '{layer.name}' não é uma camada de ajuste.")
        return

    type_id = backend.get_filter_type(c_idx)
    params = backend.get_filter_params(c_idx)

    from ui.core.screens.filters import FilterEditPopup
    popup = FilterEditPopup(c_idx, layer.name, type_id, params, panel)

    def on_params_changed(target_c_idx, new_params):
        if hasattr(backend, "set_filter_params"):
            backend.set_filter_params(target_c_idx, new_params)
        for top_w in QApplication.topLevelWidgets():
            if hasattr(top_w, "workspace") and hasattr(top_w.workspace, "canvas_widget"):
                top_w.workspace.canvas_widget.update()
            elif hasattr(top_w, "canvas_widget"):
                top_w.canvas_widget.update()

    popup.params_changed.connect(on_params_changed)
    popup.exec()


def open_rename_popup(panel, uid: int, rect: QRect):
    """Abre o popup de renomeação de camada ancorado ao item na view."""
    layer = panel.layer_manager.get_layer_by_uid(uid)
    if not layer:
        return

    global_pos = panel.view.viewport().mapToGlobal(rect.topLeft())
    target_rect = QRect(
        global_pos.x() + 85,
        global_pos.y() + 4,
        max(150, rect.width() - 95),
        28
    )

    popup = LayerRenamePopup(layer.name, target_rect, panel)

    def on_name_changed(new_name):
        if panel.layer_manager.rename_layer(uid, new_name):
            c_idx = panel.layer_manager.get_c_index_for_layer(uid)
            if c_idx >= 0:
                from ui.core.engine.registry import EngineRegistry
                backend = EngineRegistry.instance().get_backend()
                if backend and hasattr(backend, "set_layer_name"):
                    backend.set_layer_name(c_idx, new_name)
            panel.model.layoutChanged.emit()

    popup.name_changed.connect(on_name_changed)
    popup.show()
    popup.input_edit.setFocus()


def move_layer_up(panel):
    layer = panel.layer_manager.get_active_layer()
    if layer:
        panel._updating_selection = True
        try:
            panel._sync_to_native_engine("move_up")
            if panel.layer_manager.move_layer_up(layer.uid):
                panel._select_uid_in_view(layer.uid)
                panel._show_status(f"Camada '{layer.name}' movida para cima.")
        finally:
            panel._updating_selection = False


def move_layer_down(panel):
    layer = panel.layer_manager.get_active_layer()
    if layer:
        panel._updating_selection = True
        try:
            panel._sync_to_native_engine("move_down")
            if panel.layer_manager.move_layer_down(layer.uid):
                panel._select_uid_in_view(layer.uid)
                panel._show_status(f"Camada '{layer.name}' movida para baixo.")
        finally:
            panel._updating_selection = False


def merge_layer_down(panel):
    layer = panel.layer_manager.get_active_layer()
    if layer:
        layer_list = panel.layer_manager.layers
        if layer in layer_list:
            c_idx = layer_list.index(layer)
            if c_idx > 0:
                panel._updating_selection = True
                try:
                    panel._sync_to_native_engine("merge_down", c_idx)
                    if panel.layer_manager.merge_down(layer.uid):
                        active = panel.layer_manager.get_active_layer()
                        if active:
                            panel._select_uid_in_view(active.uid)
                            panel._sync_to_native_engine("select")
                        panel._show_status(f"Camada '{layer.name}' fundida para baixo.")
                finally:
                    panel._updating_selection = False


def duplicate_layer(panel):
    layer = panel.layer_manager.get_active_layer()
    if layer:
        panel._updating_selection = True
        try:
            panel._sync_to_native_engine("duplicate")
            new_uid = panel.layer_manager.duplicate_layer(layer.uid)
            panel._synced_uids = [l.uid for l in panel.layer_manager.layers]
            if new_uid:
                refresh_layer_thumbnail(panel, new_uid)
                panel._select_uid_in_view(new_uid)
                panel._sync_to_native_engine("select")
                panel._show_status(f"Camada '{layer.name}' duplicada com sucesso.")
        finally:
            panel._updating_selection = False
