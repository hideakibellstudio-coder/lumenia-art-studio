"""
panel_sync — Sincronizador Nativo C++ do LayersPanel
=====================================================
Submódulo atômico do LayersPanel para comunicação com o EngineBackend.
"""

from __future__ import annotations

import logging
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


def sync_to_native_engine(panel, action: str, *args):
    """Sincroniza as ações de camada executadas na UI com o motor ALADYN ENGINE via contrato."""
    from ui.core.engine.registry import EngineRegistry
    backend = EngineRegistry.instance().get_backend()
    if not backend:
        return

    active_layer = panel.layer_manager.get_active_layer()
    layer_list = panel.layer_manager.layers

    try:
        c_idx = layer_list.index(active_layer) if active_layer else backend.get_active_layer_index()
    except ValueError:
        c_idx = backend.get_active_layer_index()

    if action == "clear":
        backend.clear_canvas()
    elif action == "clear_layer":
        backend.clear_layer(c_idx)
    elif action == "opacity":
        val = args[0]
        backend.set_layer_opacity(c_idx, float(val))
    elif action == "blend":
        mode_idx = args[0]
        backend.set_layer_blend_mode(c_idx, mode_idx)
    elif action == "visibility":
        uid, vis = args[0], args[1]
        target_layer = panel.layer_manager.get_layer_by_uid(uid)
        if target_layer and target_layer in layer_list:
            idx = layer_list.index(target_layer)
            backend.set_layer_visibility(idx, bool(vis))
    elif action == "lock":
        uid, locked = args[0], args[1]
        target_layer = panel.layer_manager.get_layer_by_uid(uid)
        if target_layer and target_layer in layer_list:
            idx = layer_list.index(target_layer)
            backend.set_layer_lock(idx, bool(locked))
    elif action == "alpha_lock":
        uid, val = args[0], args[1]
        target_layer = panel.layer_manager.get_layer_by_uid(uid)
        if target_layer and target_layer in layer_list:
            idx = layer_list.index(target_layer)
            backend.set_layer_alpha_lock(idx, bool(val))
    elif action == "clipping_mask":
        uid, val = args[0], args[1]
        target_layer = panel.layer_manager.get_layer_by_uid(uid)
        if target_layer and target_layer in layer_list:
            idx = layer_list.index(target_layer)
            backend.set_layer_clipping_mask(idx, bool(val))
    elif action == "add":
        name = args[0] if args else ""
        backend.add_layer(name)
        panel._synced_uids = [l.uid for l in layer_list]
    elif action == "add_group":
        name = args[0] if args else "Novo Grupo"
        backend.add_group(name)
        panel._synced_uids = [l.uid for l in layer_list]
    elif action == "delete":
        backend.remove_layer(c_idx)
        panel._synced_uids = [l.uid for l in layer_list]
    elif action == "move_up":
        if c_idx < backend.get_drawing_layer_count() - 1:
            backend.reorder_layer(c_idx, c_idx + 1)
            panel._synced_uids = [l.uid for l in layer_list]
    elif action == "move_down":
        if c_idx > 0:
            backend.reorder_layer(c_idx, c_idx - 1)
            panel._synced_uids = [l.uid for l in layer_list]
    elif action == "reorder_all":
        if not hasattr(panel, "_synced_uids") or len(panel._synced_uids) != len(layer_list):
            old_uids = [l.uid for l in layer_list]
        else:
            old_uids = panel._synced_uids

        if len(layer_list) == len(old_uids):
            new_indices = []
            for l in layer_list:
                if l.uid in old_uids:
                    new_indices.append(old_uids.index(l.uid))
                else:
                    break
            if len(new_indices) == len(layer_list) and new_indices != list(range(len(layer_list))):
                backend.reorder_layers(new_indices)

        panel._synced_uids = [l.uid for l in layer_list]
    elif action == "merge_down":
        idx = args[0]
        backend.merge_layer_down(idx)
        panel._synced_uids = [l.uid for l in layer_list]
    elif action == "duplicate":
        backend.duplicate_layer(c_idx)
        panel._synced_uids = [l.uid for l in layer_list]
    elif action == "select":
        backend.select_layer(c_idx)

    # Sincroniza vínculos hierárquicos de pais no C++ sempre
    parent_indices = []
    for l in layer_list:
        if l.parent_uid is not None:
            p_layer = panel.layer_manager.get_layer_by_uid(l.parent_uid)
            if p_layer and p_layer in layer_list:
                parent_indices.append(layer_list.index(p_layer))
            else:
                parent_indices.append(-1)
        else:
            parent_indices.append(-1)
    backend.set_layer_parents(parent_indices)

    # Repinta o CanvasWidget
    for top_w in QApplication.topLevelWidgets():
        if hasattr(top_w, "workspace") and hasattr(top_w.workspace, "canvas_widget"):
            top_w.workspace.canvas_widget.update()
        elif hasattr(top_w, "canvas_widget"):
            top_w.canvas_widget.update()


def refresh_layer_thumbnail(panel, uid: int):
    """Gera a miniatura real de uma camada lendo o pixel buffer do motor C++ para aquele índice."""
    from ui.core.engine.registry import EngineRegistry
    backend = EngineRegistry.instance().get_backend()
    if not backend:
        return

    layer = panel.layer_manager.get_layer_by_uid(uid)
    if not layer:
        return

    layer_list = panel.layer_manager.layers
    try:
        c_idx = layer_list.index(layer)
    except ValueError:
        return

    try:
        raw = backend.get_layer_thumbnail_buffer(c_idx, 38, 28)
        if raw:
            from PySide6.QtGui import QImage, QPixmap
            img = QImage(raw, 38, 28, 38 * 4, QImage.Format_RGBA8888)
            if not img.isNull():
                layer.thumb = QPixmap.fromImage(img)
                idx = panel.model._find_index_by_uid(uid)
                if idx.isValid():
                    panel.model.dataChanged.emit(idx, idx)
    except Exception as e:
        logger.debug(f"[LayersPanel] Falha ao gerar thumbnail real: {e}")
