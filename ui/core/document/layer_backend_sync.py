"""
layer_backend_sync — Sincronizador de Estado e Projeção C++ para LocalLayerManager
===================================================================================
Implementa a sincronização Single Source of Truth (SSOT) entre o LocalLayerManager
(Python) e o motor C++ ALADYN ENGINE via contrato EngineBackend.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, List

from . import layer_properties

logger = logging.getLogger(__name__)


def get_active_backend(manager) -> Optional[Any]:
    """Obtém o backend ativo aplicável ao LocalLayerManager."""
    if getattr(manager, "backend_projection_restoring", False) or getattr(manager, "_history_guard", False):
        return None

    backend = getattr(manager, "_backend", None)
    if backend is None:
        try:
            from ui.core.engine.registry import EngineRegistry
            backend = EngineRegistry.instance().get_backend()
        except Exception:
            return None

    if backend is None or not getattr(backend, "available", True):
        return None

    doc = getattr(manager, "document", None)
    if doc is not None and hasattr(backend, "get_active_document_context"):
        ctx = backend.get_active_document_context()
        if ctx and ctx != doc.uid:
            return None

    return backend


def notify_canvas_repaint(action_name: str = "") -> None:
    """Dispara repaint do CanvasWidget quando há alteração visual de camadas."""
    if action_name in ("select", "lock", "alpha_lock"):
        return
    from ui.core.plugins.canvas_access import request_canvas_repaint
    request_canvas_repaint()


def sync_backend_parents(manager) -> None:
    """Sincroniza a árvore hierárquica de pais no motor C++."""
    backend = get_active_backend(manager)
    if not backend:
        return
    layer_list = manager.layers
    parent_indices: List[int] = []
    for l in layer_list:
        if l.parent_uid is not None:
            p_layer = manager.get_layer_by_uid(l.parent_uid)
            if p_layer and p_layer in layer_list:
                parent_indices.append(layer_list.index(p_layer))
            else:
                parent_indices.append(-1)
        else:
            parent_indices.append(-1)
    backend.set_layer_parents(parent_indices)


def sync_backend_add(manager, layer, target_idx: int, is_group: bool = False) -> None:
    """Sincroniza adição de nova camada/grupo com o motor C++."""
    backend = get_active_backend(manager)
    if not backend:
        return
    if backend.get_drawing_layer_count() < len(manager.layers):
        if is_group:
            backend.add_group(layer.name, target_idx)
        else:
            backend.add_layer(layer.name, target_idx)
    sync_backend_parents(manager)
    backend.select_layer(manager.active_index)
    notify_canvas_repaint("add")


def sync_backend_add_filter(manager, layer, target_idx: int, filter_type_id: int, params) -> None:
    """Sincroniza a criação de uma camada de ajuste (filtro + parâmetros) com o motor C++."""
    backend = get_active_backend(manager)
    if not backend:
        return
    if backend.get_drawing_layer_count() < len(manager.layers):
        native_idx = backend.add_filter_layer(layer.name, filter_type_id, target_idx)
        if native_idx >= 0:
            backend.set_filter_params(native_idx, params)
    sync_backend_parents(manager)
    backend.select_layer(manager.active_index)
    notify_canvas_repaint("add")


def sync_backend_remove(manager, c_idx: int) -> None:
    """Sincroniza remoção de camada com o motor C++."""
    backend = get_active_backend(manager)
    if not backend:
        return
    if backend.get_drawing_layer_count() > len(manager.layers):
        backend.remove_layer(c_idx)
    sync_backend_parents(manager)
    backend.select_layer(manager.active_index)
    notify_canvas_repaint("remove")


def sync_backend_duplicate(manager, c_idx: int) -> None:
    """Sincroniza duplicação de camada com o motor C++."""
    backend = get_active_backend(manager)
    if not backend:
        return
    if backend.get_drawing_layer_count() < len(manager.layers):
        backend.duplicate_layer(c_idx)
    sync_backend_parents(manager)
    backend.select_layer(manager.active_index)
    notify_canvas_repaint("duplicate")


def sync_backend_reorder(manager, from_idx: int, to_idx: int) -> None:
    """Sincroniza reordenação de camada adjacente com o motor C++."""
    backend = get_active_backend(manager)
    if not backend:
        return
    backend.reorder_layer(from_idx, to_idx)
    sync_backend_parents(manager)
    backend.select_layer(manager.active_index)
    notify_canvas_repaint("reorder")


def sync_backend_reorder_all(manager, new_indices: List[int]) -> None:
    """Sincroniza permutação completa da pilha de camadas com o motor C++."""
    backend = get_active_backend(manager)
    if not backend:
        return
    backend.reorder_layers(new_indices)
    sync_backend_parents(manager)
    backend.select_layer(manager.active_index)
    notify_canvas_repaint("reorder_all")


def sync_backend_merge_down(manager, c_idx: int) -> None:
    """Sincroniza merge down de camada com o motor C++."""
    backend = get_active_backend(manager)
    if not backend:
        return
    if backend.get_drawing_layer_count() > len(manager.layers):
        backend.merge_layer_down(c_idx)
    sync_backend_parents(manager)
    backend.select_layer(manager.active_index)
    notify_canvas_repaint("merge_down")


def sync_backend_flatten_group(manager, group_idx: int) -> None:
    """Sincroniza "achatar grupo" com o motor C++.

    `group_idx` é a posição do grupo ANTES de o modelo remover os filhos (a
    mesma que o motor ainda tem). Até 2026-09-24 o modelo só reenviava os pais
    e quem achatava no motor era o menu, por um segundo caminho.
    """
    backend = get_active_backend(manager)
    if not backend:
        return
    if backend.get_drawing_layer_count() > len(manager.layers):
        backend.flatten_group(group_idx)
    sync_backend_parents(manager)
    backend.select_layer(manager.active_index)
    notify_canvas_repaint("flatten_group")


def sync_backend_property(manager, idx: int, prop_name: str, value: Any) -> None:
    """Sincroniza propriedades individuais de camada com o motor C++."""
    backend = get_active_backend(manager)
    if not backend or idx < 0 or idx >= backend.get_drawing_layer_count():
        return
    prop = layer_properties.TABLE.by_sync_name.get(prop_name)
    if prop and prop.engine_setter:
        layer_properties.apply_to_engine(backend, idx, prop, value)
    notify_canvas_repaint(prop_name)


def sync_backend_select(manager, c_idx: int) -> None:
    """Sincroniza seleção de camada ativa com o motor C++."""
    backend = get_active_backend(manager)
    if not backend or c_idx < 0:
        return
    backend.select_layer(c_idx)


def validate_layer_tree(layers, active_uid) -> None:
    """Valida integridade estrutural e grafo de pais da lista de camadas."""
    uids = [layer.uid for layer in layers]
    if any(type(uid) is not int or uid <= 0 for uid in uids) or len(uids) != len(set(uids)):
        raise ValueError("UIDs de camadas devem ser inteiros positivos e únicos")
    nodes = {layer.uid: layer for layer in layers}
    for layer in layers:
        seen = {layer.uid}
        parent = layer.parent_uid
        while parent is not None:
            if type(parent) is not int or parent in seen or parent not in nodes or not nodes[parent].is_group:
                raise ValueError("hierarquia de camadas inválida")
            seen.add(parent)
            parent = nodes[parent].parent_uid
    if active_uid is not None and active_uid not in nodes:
        raise ValueError("camada ativa inexistente")


def perform_reorder_and_reparent(layers, new_order_uids, parent_map) -> List[Any]:
    """Executa a reordenação e reparenting validando integridade antes da mutação."""
    order = [str(uid) for uid in new_order_uids]
    nodes = {str(layer.uid): layer for layer in layers}
    if len(order) != len(nodes) or set(order) != set(nodes):
        raise ValueError("A ordem deve conter cada camada exatamente uma vez.")
    parents = {uid: str(parent_map[uid]) if parent_map.get(uid) is not None else None for uid in order}
    for uid in order:
        seen = {uid}
        parent = parents[uid]
        while parent is not None:
            if parent in seen or parent not in nodes or not nodes[parent].is_group:
                raise ValueError("Hierarquia de camadas inválida.")
            seen.add(parent)
            parent = parents[parent]

    id_to_layer = {str(l.uid): l for l in layers}
    new_list = []
    for uid_str in order:
        if uid_str in id_to_layer:
            l = id_to_layer[uid_str]
            p_uid = parent_map.get(uid_str)
            l.parent_uid = int(p_uid) if p_uid is not None else None
            new_list.append(l)
    return new_list
