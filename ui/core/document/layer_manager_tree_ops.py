"""Operações estruturais da pilha de camadas: achatar grupo/imagem, reordenar com
reparentamento e substituir a lista inteira (restauração).

Separado de layer_manager.py em 2026-09-22 (448 linhas, na parede dos 450).
Continua sendo parte da SSOT: LocalLayerManager herda este mixin.
"""
import logging
from typing import Optional
from .local_layer import LocalLayer
from .layer_blend_mode import LayerBlendMode
from .layer_backend_sync import (
    perform_reorder_and_reparent,
    sync_backend_flatten_group,
    sync_backend_parents,
    sync_backend_reorder_all,
    sync_backend_select,
)

logger = logging.getLogger(__name__)


class LayerTreeOpsMixin:
    """Mixin extraído de layer_manager.py (métodos movidos sem alteração)."""

    def flatten_group(self, idx: int) -> bool:
        group: Optional[LocalLayer] = self.get_layer_at_index(idx)
        if not group or not group.is_group:
            return False
        descendants = {group.uid}
        while True:
            children = {layer.uid for layer in self.layers if layer.parent_uid in descendants}
            if children <= descendants:
                break
            descendants |= children
        self.order_about_to_change.emit()
        group.is_group = False
        if LayerBlendMode.coerce(group.blend_mode) == LayerBlendMode.PASS_THROUGH:
            group.blend_mode = LayerBlendMode.NORMAL
        self.layers = [layer for layer in self.layers if layer.uid == group.uid or layer.uid not in descendants]
        if self._active_uid in descendants:
            self.set_active_layer(group.uid)
        sync_backend_flatten_group(self, idx)
        self.order_changed.emit()
        self._validate_clipping_masks()
        self.content_changed.emit("flatten_group")
        self.validate_integrity()
        return True

    def flatten_image(self) -> bool:
        """Achata todos os grupos e mescla a pilha inteira numa camada só.

        Cada passo é uma operação do modelo, que sincroniza o motor. Até
        2026-09-24 este método descartava as camadas só no modelo (o motor
        continuava com todas) e o menu fazia a operação real por outro caminho.
        Quem chama envolve numa `layer_transaction`: um erro no meio desfaz tudo.
        """
        if len(self.layers) <= 1:
            return False
        while any(layer.is_group for layer in self.layers):
            idx = next(i for i, layer in enumerate(self.layers) if layer.is_group)
            self.flatten_group(idx)
        while len(self.layers) > 1:
            before = len(self.layers)
            if not self.merge_down(self.layers[-1].uid) or len(self.layers) >= before:
                raise RuntimeError("A operação de achatar não avançou.")
        return True

    def reorder_and_reparent(self, new_order_uids, parent_map):
        old_uids = [layer.uid for layer in self.layers]
        self.order_about_to_change.emit()
        self.layers = perform_reorder_and_reparent(self.layers, new_order_uids, parent_map)
        # A nova ordem vai ao motor aqui (fonte única). Até 2026-09-24 só o
        # painel de camadas fazia isso, ao ouvir order_changed; sem o painel
        # aberto a ordem de composição divergia do documento, e mesmo com ele
        # a camada ativa no motor ficava apontando para a posição antiga.
        permutation = [old_uids.index(layer.uid) for layer in self.layers]
        if permutation != list(range(len(permutation))):
            sync_backend_reorder_all(self, permutation)
        else:
            sync_backend_parents(self)
            sync_backend_select(self, self.active_index)
        self.order_changed.emit()
        self._validate_clipping_masks()
        self.validate_integrity()

    def replace_layers(self, records) -> None:
        """Reconstrói a projeção local a partir de registros persistidos."""
        new_layers = []
        max_uid = 0
        for record in records or []:
            uid = int(record.get("uid", max_uid + 1))
            max_uid = max(max_uid, uid)
            layer: LocalLayer = LocalLayer(
                uid,
                str(record.get("name", f"Camada {uid}")),
                parent_uid=record.get("parent_uid"),
                is_group=bool(record.get("is_group", False)),
                is_filter=bool(record.get("is_filter", False)),
            )
            layer.visible = bool(record.get("visible", True))
            layer.locked = bool(record.get("locked", False))
            layer.opacity = max(0.0, min(1.0, float(record.get("opacity", 1.0))))
            layer.blend_mode = LayerBlendMode.coerce(record.get("blend_mode", LayerBlendMode.PASS_THROUGH if layer.is_group else LayerBlendMode.NORMAL))
            layer.alpha_locked = bool(record.get("alpha_locked", False))
            layer.clipping_mask = bool(record.get("clipping_mask", False))
            new_layers.append(layer)
        self.order_about_to_change.emit()
        self.layers = new_layers
        self._next_uid = max_uid + 1
        active_uid = next((r.get("uid") for r in records or [] if r.get("uid") == self._active_uid), None)
        self._active_uid = active_uid if active_uid is not None else (new_layers[0].uid if new_layers else None)
        self.order_changed.emit()
        self._validate_clipping_masks()
        if not self._history_guard:
            self._last_structural_snapshot = self._snapshot()
