"""plan_layer_drop — onde ficam as camadas arrastadas e soltas na árvore.

Função pura sobre a lista de camadas: devolve a nova ordem (uids) e o mapa de
pais que o `LocalLayerManager.reorder_and_reparent` aplica. Extraída de
`LayerModel.dropMimeData` em 2026-09-24 (o modelo estava em 400 linhas).

Convenção da lista: índice 0 é a camada de baixo; na árvore, a linha 0 de um
grupo é o filho de cima (por isso a linha é invertida).
"""
from __future__ import annotations

from typing import Optional


def _sibling_at_row(layers: list, parent_uid: Optional[int], row: int):
    children = [layer for layer in layers if layer.parent_uid == parent_uid]
    inverted = len(children) - 1 - row
    return children[inverted] if 0 <= inverted < len(children) else None


def plan_layer_drop(manager, uids: list[int], parent_uid: Optional[int], row: int):
    """(nova ordem de uids em texto, {uid: pai}) ou None se o destino é inválido."""
    if parent_uid in uids:
        return None
    remaining = [layer for layer in manager.layers if layer.uid not in uids]

    insert_idx = None
    if parent_uid is not None:
        target = manager.get_layer_by_uid(parent_uid)
        if target and not target.is_group:
            # Soltar sobre uma camada comum = logo acima dela, no mesmo pai.
            if target in remaining:
                insert_idx = remaining.index(target) + 1
            parent_uid = target.parent_uid

    if insert_idx is None:
        siblings = [layer for layer in remaining if layer.parent_uid == parent_uid]
        if row == -1 or row >= len(siblings):
            insert_idx = 0 if parent_uid is None else remaining.index(manager.get_layer_by_uid(parent_uid)) + 1
        else:
            sibling = _sibling_at_row(remaining, parent_uid, row)
            insert_idx = remaining.index(sibling) + 1 if sibling else 0

    moved = [layer for layer in (manager.get_layer_by_uid(uid) for uid in uids) if layer]
    ordered = remaining[:insert_idx] + moved + remaining[insert_idx:]
    parent_map = {}
    for layer in ordered:
        parent = parent_uid if layer in moved else layer.parent_uid
        parent_map[str(layer.uid)] = str(parent) if parent is not None else None
    return [str(layer.uid) for layer in ordered], parent_map
