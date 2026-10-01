from PySide6 import QtCore
import logging
from typing import Optional

from ui.infrastructure.i18n import tr

logger = logging.getLogger(__name__)

from .local_layer import LocalLayer, default_layer_name
from . import layer_properties
from .layer_backend_sync import (
    sync_backend_add,
    sync_backend_add_filter,
    sync_backend_remove,
    sync_backend_duplicate,
    sync_backend_reorder,
    sync_backend_merge_down,
    sync_backend_property,
    sync_backend_select,
    validate_layer_tree,
)
from .layer_manager_tree_ops import LayerTreeOpsMixin

__all__ = ["LocalLayer", "LocalLayerManager"]


class LocalLayerManager(QtCore.QObject, LayerTreeOpsMixin):
    active_layer_changed = QtCore.Signal(int)
    layer_added = QtCore.Signal(object)
    order_about_to_change = QtCore.Signal()
    order_changed = QtCore.Signal()
    layer_property_changed = QtCore.Signal(int)
    thumbnail_updated = QtCore.Signal(int)
    content_changed = QtCore.Signal(str)

    def __init__(self, backend=None):
        super().__init__()
        self.layers = []
        self._active_uid = None
        self._next_uid = 1
        self._history_guard = False
        self.backend_projection_restoring = False
        self._backend = backend
        self.document = None

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, value):
        self._backend = value

    def _snapshot(self):
        keys = ("uid", "name", "parent_uid", "is_group", "is_filter") + tuple(
            prop.name for prop in layer_properties.TABLE.all if not prop.in_constructor)
        return {
            "layers": [{k: getattr(layer, k) for k in keys} for layer in self.layers],
            "active_uid": self._active_uid,
            "next_uid": self._next_uid,
        }

    def _restore_snapshot(self, snapshot) -> None:
        self._history_guard = True
        try:
            self.replace_layers(snapshot["layers"])
            # O que o arquivo não guarda (a pasta aberta) só o instantâneo do histórico carrega.
            for layer, record in zip(self.layers, snapshot["layers"]):
                for prop in layer_properties.TABLE.all:
                    if not prop.saved:
                        setattr(layer, prop.name, prop.from_record(record, layer.is_group))
            self._next_uid = max(self._next_uid, int(snapshot["next_uid"]))
            self.set_active_layer(snapshot["active_uid"])
            self._last_structural_snapshot = snapshot
        finally:
            self._history_guard = False

    def get_active_layer(self):
        if self._active_uid is None and self.layers:
            return self.layers[0]
        for l in self.layers:
            if l.uid == self._active_uid:
                return l
        return self.layers[0] if self.layers else None

    def set_active_layer(self, uid):
        if uid is not None and self.get_layer_by_uid(uid) is None:
            raise ValueError("camada ativa inexistente")
        if uid != self._active_uid:
            self._active_uid = uid
            sync_backend_select(self, self.active_index)
            self.active_layer_changed.emit(uid)

    def get_layer_by_uid(self, uid):
        if type(uid) is not int or uid <= 0:
            return None
        for l in self.layers:
            if l.uid == uid:
                return l
        return None

    def get_layer_at_index(self, index: int):
        """Retorna uma camada por posição, sem misturar posição e identidade."""
        if not isinstance(index, int) or index < 0 or index >= len(self.layers):
            return None
        return self.layers[index]

    def _resolve_uid(self, target):
        """Resolve somente por UID ou objeto; índices usam get_layer_at_index."""
        if isinstance(target, LocalLayer):
            return target if target in self.layers else None
        return self.get_layer_by_uid(target) if type(target) is int else None

    def validate_integrity(self) -> None:
        """Valida UIDs estáveis e o grafo hierárquico antes da projeção nativa."""
        self._validate_clipping_masks()
        validate_layer_tree(self.layers, self._active_uid)

    def _new_uid(self) -> int:
        uid = self._next_uid
        self._next_uid += 1
        return uid

    def _insert_above_active(self, layer: LocalLayer) -> int:
        """Insere logo acima da camada ativa (dentro dela, se for grupo); devolve o índice."""
        active = self.get_active_layer()
        if active:
            idx = self.layers.index(active) + 1
            layer.parent_uid = active.uid if active.is_group else active.parent_uid
            self.layers.insert(idx, layer)
        else:
            idx = len(self.layers)
            self.layers.append(layer)
        return idx

    def _announce_added(self, layer: LocalLayer, reason: str) -> None:
        self.layer_added.emit(layer)
        self.order_changed.emit()
        self.content_changed.emit(reason)

    def add_layer(self, name=None) -> int:
        uid = self._new_uid()
        layer = LocalLayer(uid, name or default_layer_name(uid))
        idx = self._insert_above_active(layer)
        self.set_active_layer(uid)
        sync_backend_add(self, layer, idx, is_group=False)
        self._announce_added(layer, "add_layer")
        return uid

    def add_group(self, name=None) -> int:
        uid = self._new_uid()
        group = LocalLayer(uid, name or tr("layers.new_group", "Novo Grupo"), is_group=True)
        idx = self._insert_above_active(group)
        self.set_active_layer(uid)
        sync_backend_add(self, group, idx, is_group=True)
        self._announce_added(group, "add_group")
        return uid

    def add_filter_layer(self, name: str, filter_type_id: int, params: list) -> int:
        """Camada de ajuste: entra no modelo e no motor (com filtro e parâmetros) de uma vez.

        Antes de 2026-09-24 o painel de camadas criava a camada no motor e
        depois pedia ao modelo uma camada comum, marcando `is_filter` à mão.
        """
        uid = self._new_uid()
        layer = LocalLayer(uid, name or f"Ajuste {uid}", is_filter=True)
        idx = self._insert_above_active(layer)
        self.set_active_layer(uid)
        sync_backend_add_filter(self, layer, idx, filter_type_id, params)
        self._announce_added(layer, "add_filter_layer")
        return uid

    def request_thumbnails(self, uids=None) -> None:
        """Pede às views que releiam as miniaturas (os pixels mudaram no motor)."""
        for uid in (uids if uids is not None else [layer.uid for layer in self.layers]):
            self.thumbnail_updated.emit(uid)

    @property
    def active_index(self) -> int:
        active = self.get_active_layer()
        if active and active in self.layers:
            return self.layers.index(active)
        return -1

    def remove_layer(self, target) -> bool:
        layer = self._resolve_uid(target)
        if not layer:
            return False

        if len(self.layers) <= 1:
            return False

        removed = {layer.uid}
        while True:
            descendants = {item.uid for item in self.layers if item.parent_uid in removed}
            if descendants <= removed:
                break
            removed |= descendants
        if len(removed) == len(self.layers):
            return False
        self.order_about_to_change.emit()
        idx = self.layers.index(layer)
        self.layers = [item for item in self.layers if item.uid not in removed]
        sync_backend_remove(self, idx)
        if self._active_uid in removed:
            self.set_active_layer(self.layers[min(idx, len(self.layers) - 1)].uid)

        self.order_changed.emit()
        self._validate_clipping_masks()
        self.content_changed.emit("remove_layer")
        return True

    def duplicate_layer(self, target) -> int:
        layer: Optional[LocalLayer] = self._resolve_uid(target)
        if not layer or layer.is_group:
            return 0

        new_uid = self._next_uid
        self._next_uid += 1

        new_layer: LocalLayer = LocalLayer(new_uid, f"{layer.name} Copiar", is_filter=layer.is_filter)
        new_layer.parent_uid = layer.parent_uid
        for prop in layer_properties.TABLE.all:
            if prop.duplicated:
                setattr(new_layer, prop.name, getattr(layer, prop.name))

        idx = self.layers.index(layer) + 1
        self.layers.insert(idx, new_layer)

        self.set_active_layer(new_uid)
        sync_backend_duplicate(self, idx - 1)
        self.layer_added.emit(new_layer)
        self.content_changed.emit("duplicate_layer")
        return new_uid

    def move_layer_up(self, uid) -> bool:
        layer = self.get_layer_by_uid(uid)
        if not layer:
            return False

        idx = self.layers.index(layer)
        if idx >= len(self.layers) - 1:
            return False

        self.order_about_to_change.emit()
        self.layers[idx], self.layers[idx + 1] = self.layers[idx + 1], self.layers[idx]
        sync_backend_reorder(self, idx, idx + 1)
        self.order_changed.emit()
        self._validate_clipping_masks()
        self.set_active_layer(uid)
        self.content_changed.emit("move_layer")
        return True

    def move_layer_down(self, uid) -> bool:
        layer = self.get_layer_by_uid(uid)
        if not layer:
            return False

        idx = self.layers.index(layer)
        if idx <= 0:
            return False

        self.order_about_to_change.emit()
        self.layers[idx], self.layers[idx - 1] = self.layers[idx - 1], self.layers[idx]
        sync_backend_reorder(self, idx, idx - 1)
        self.order_changed.emit()
        self._validate_clipping_masks()
        self.set_active_layer(uid)
        self.content_changed.emit("move_layer")
        return True

    def merge_down(self, target) -> bool:
        layer = self._resolve_uid(target)
        if not layer or layer.is_group:
            return False

        idx = self.layers.index(layer)
        if idx <= 0:
            return False

        target_layer = self.layers[idx - 1]
        if target_layer.is_group:
            return False

        self.order_about_to_change.emit()
        self.layers.remove(layer)
        sync_backend_merge_down(self, idx)
        self.set_active_layer(target_layer.uid)
        self.order_changed.emit()
        self._validate_clipping_masks()
        self.content_changed.emit("merge_down")
        return True

    def _validate_clipping_masks(self) -> None:
        """Garante que a primeira camada (índice 0) nunca permaneça como máscara de recorte."""
        if self.layers and self.layers[0].clipping_mask:
            self.layers[0].clipping_mask = False
            if not self._history_guard:
                sync_backend_property(self, 0, "clipping_mask", False)
            self.layer_property_changed.emit(self.layers[0].uid)

    def set_property(self, idx: int, name: str, value) -> bool:
        """Muda uma propriedade da tabela `LAYER_PROPERTIES` e avisa o motor e quem escuta.

        Os setters abaixo (`set_alpha_lock`, `set_layer_opacity`...) existem pelos nomes que os
        chamadores já usam; uma propriedade nova entra na tabela e é mudada por aqui.
        """
        layer = self.get_layer_at_index(idx)
        if not layer:
            return False
        prop = layer_properties.TABLE.by_name[name]
        setattr(layer, name, prop.coerce(value))
        sync_backend_property(self, idx, prop.sync, getattr(layer, name))
        self.layer_property_changed.emit(layer.uid)
        self.content_changed.emit(prop.change_reason)
        return True

    def set_clipping_mask(self, idx: int, enabled: bool) -> None:
        # A primeira camada não tem base para recortar.
        self.set_property(idx, "clipping_mask", bool(enabled) and idx != 0)

    def set_alpha_lock(self, idx: int, enabled: bool) -> None:
        self.set_property(idx, "alpha_locked", enabled)

    def set_layer_lock(self, idx: int, locked: bool) -> None:
        self.set_property(idx, "locked", locked)

    def set_layer_visibility(self, idx: int, visible: bool) -> None:
        self.set_property(idx, "visible", visible)

    def rename_layer(self, uid: int, name: str) -> bool:
        layer = self.get_layer_by_uid(uid)
        name = str(name).strip()
        if not layer or not name:
            return False
        if layer.name == name:
            return True
        layer.name = name
        idx = self.layers.index(layer)
        sync_backend_property(self, idx, "name", name)
        self.layer_property_changed.emit(layer.uid)
        self.content_changed.emit("rename_layer")
        return True

    def set_layer_name(self, idx: int, name: str) -> bool:
        layer = self.get_layer_at_index(idx)
        return self.rename_layer(layer.uid, name) if layer else False

    def set_layer_opacity(self, idx: int, opacity: float) -> bool:
        return self.set_property(idx, "opacity", opacity)

    def set_layer_blend_mode(self, idx: int, blend_mode) -> bool:
        return self.set_property(idx, "blend_mode", blend_mode)
