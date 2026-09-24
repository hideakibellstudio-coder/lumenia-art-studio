"""
AladynLayerMixin — Gerenciador Atômico de Camadas, Grupos e Filtros para o AladynBackend.
==========================================================================================
Isola todas as operações de pilha de camadas, modos de mesclagem, hierarquias de pais,
camadas de ajuste e histórico de desfazer/refazer (Undo/Redo) do motor ALADYN ENGINE.
"""

from __future__ import annotations
import logging
from typing import Any, Optional

from ui.core.document.layer_blend_mode import LayerBlendMode
from .aladyn_base import AladynBackendBase

logger = logging.getLogger(__name__)


class AladynLayerMixin(AladynBackendBase):
    """Mixin responsável pelo gerenciamento de camadas, grupos e filtros no AladynBackend."""

    def clear_canvas(self) -> None:
        if self._facade:
            self._facade.clear_canvas()
            self._mark_document_dirty("clear_canvas")

    def clear_layer(self, index: int) -> None:
        if self._facade:
            self._facade.clear_layer(index)
            self._mark_document_dirty("clear_layer")

    def set_layer_alpha_lock(self, index: int, locked: bool) -> None:
        if self._facade:
            self._facade.set_layer_alpha_lock(index, locked)
            self._mark_document_dirty("alpha_lock")

    def set_layer_clipping_mask(self, index: int, clipped: bool) -> None:
        if self._facade:
            self._facade.set_layer_clipping_mask(index, clipped)
            self._mark_document_dirty("clipping_mask")

    def set_layer_blend_mode(self, index: int, mode_val: Any) -> None:
        if self._facade:
            # Passa int puro (contrato de `.pyi`: `blend_mode_id: int`), nunca
            # constrói o enum nativo -- mais simples, e imune a um binding
            # pybind11 parcial (bind_math_brush.cpp expõe os 13 valores hoje,
            # mas já expôs só 7 antes da Fase C5). Ver
            # ui.core.document.layer_blend_mode para o histórico completo.
            self._facade.set_layer_blend_mode(index, int(LayerBlendMode.coerce(mode_val)))
            self._mark_document_dirty("blend_mode")

    def reorder_layer(self, from_index: int, to_index: int) -> bool:
        if self._facade:
            res = self._facade.reorder_layer(from_index, to_index)
            if res:
                self._mark_document_dirty("reorder_layer")
            return res
        return False

    def reorder_layers(self, new_order: list[int]) -> bool:
        if self._facade:
            res = self._facade.reorder_layers(new_order)
            if res:
                self._mark_document_dirty("reorder_layers")
            return res
        return False

    def set_layer_parents(self, parent_indices: list[int]) -> bool:
        if self._facade:
            res = self._facade.set_layer_parents(parent_indices)
            if res:
                self._mark_document_dirty("set_layer_parents")
            return res
        return False

    def set_layer_document_uid(self, index: int, uid: int) -> bool:
        if self._facade:
            return bool(self._facade.set_layer_document_uid(int(index), int(uid)))
        return False

    def add_group(self, name: str = "Novo Grupo", insert_index: int = -1) -> int:
        if self._facade:
            idx = self._facade.add_group(name, int(insert_index))
            if idx >= 0:
                self._mark_document_dirty("add_group")
            return idx
        return -1

    def add_filter_layer(self, name: str, filter_type_id: int, insert_index: int = -1) -> int:
        if self._facade:
            idx = self._facade.add_filter_layer(name, filter_type_id, int(insert_index))
            if idx >= 0:
                self._mark_document_dirty("add_filter_layer")
            return idx
        return -1

    def set_filter_params(self, index: int, params: list[float]) -> None:
        if self._facade:
            self._facade.set_filter_params(index, [float(x) for x in params])
            self._mark_document_dirty("filter_params")

    def get_filter_params(self, index: int) -> list[float]:
        if self._facade:
            return list(self._facade.get_filter_params(index))
        return []

    def get_filter_type(self, index: int) -> int:
        if self._facade:
            return self._facade.get_filter_type(index)
        return -1

    def is_filter_layer(self, index: int) -> bool:
        if self._facade:
            return self._facade.is_filter_layer(index)
        return False

    def set_layer_name(self, index: int, name: str) -> None:
        if self._facade:
            self._facade.set_layer_name(index, name)
            self._mark_document_dirty("layer_name")

    def get_layer_info(self, index: int) -> dict:
        if self._facade:
            return dict(self._facade.get_layer_info(int(index)))
        return {}

    def is_group(self, index: int) -> bool:
        if self._facade:
            return self._facade.is_group(index)
        return False

    def duplicate_layer(self, index: int) -> int:
        if self._facade:
            idx = self._facade.duplicate_layer(index)
            if idx >= 0:
                self._mark_document_dirty("duplicate_layer")
            return idx
        return -1

    def flatten_group(self, index: int) -> bool:
        if self._facade:
            res = self._facade.flatten_group(index)
            if res:
                self._mark_document_dirty("flatten_group")
            return res
        return False

    def merge_layer_down(self, index: int) -> bool:
        if self._facade:
            res = self._facade.merge_layer_down(index)
            if res:
                self._mark_document_dirty("merge_layer_down")
            return res
        return False

    def add_layer(self, name: str = "", insert_index: int = -1) -> int:
        if self._facade:
            idx = self._facade.add_layer(name, int(insert_index))
            if idx >= 0:
                self._mark_document_dirty("add_layer")
            return idx
        return -1

    def remove_layer(self, index: int) -> bool:
        if self._facade:
            res = self._facade.remove_layer(index)
            if res:
                self._mark_document_dirty("remove_layer")
            return res
        return False

    def select_layer(self, index: int) -> bool:
        if self._facade:
            return self._facade.select_layer(index)
        return False

    def set_layer_opacity(self, index: int, opacity: float) -> None:
        if self._facade:
            self._facade.set_layer_opacity(index, float(opacity))
            self._mark_document_dirty("layer_opacity")

    def set_layer_visibility(self, index: int, visible: bool) -> None:
        if self._facade:
            self._facade.set_layer_visibility(index, bool(visible))
            self._mark_document_dirty("layer_visibility")

    def set_layer_lock(self, index: int, locked: bool) -> None:
        if self._facade:
            self._facade.set_layer_lock(index, bool(locked))
            self._mark_document_dirty("layer_lock")

    def is_layer_alpha_locked(self, index: int) -> bool:
        if self._facade:
            return self._facade.is_layer_alpha_locked(index)
        return False

    def is_layer_clipping_mask(self, index: int) -> bool:
        if self._facade:
            return self._facade.is_layer_clipping_mask(index)
        return False

    def get_active_layer_index(self) -> int:
        if self._facade:
            return self._facade.get_active_layer_index()
        return 0

    def get_drawing_layer_count(self) -> int:
        if self._facade:
            return self._facade.get_drawing_layer_count()
        return 1

    def get_layer_thumbnail_buffer(self, layer_index: int, thumb_w: int, thumb_h: int) -> Optional[bytes]:
        if self._facade:
            raw = self._facade.get_layer_thumbnail_buffer(int(layer_index), int(thumb_w), int(thumb_h))
            return bytes(raw) if raw else None
        return None

    def undo(self) -> bool:
        if self._facade:
            result = self._facade.undo()
            self._width, self._height = self._facade.get_width(), self._facade.get_height()
            if result:
                self._mark_document_dirty("undo")
            return result
        return False

    def get_history_error(self) -> str:
        if self._facade:
            return str(self._facade.get_history_error() or "")
        return ""

    def redo(self) -> bool:
        if self._facade:
            result = self._facade.redo()
            self._width, self._height = self._facade.get_width(), self._facade.get_height()
            if result:
                self._mark_document_dirty("redo")
            return result
        return False

    def set_undo_memory_limit_mb(self, mb: int) -> None:
        self._undo_memory_limit_mb = int(mb)
        if self._facade:
            self._facade.set_undo_memory_limit_mb(int(mb))
        for fac in self._doc_facades.values():
            if fac:
                fac.set_undo_memory_limit_mb(int(mb))

    def get_undo_memory_limit_mb(self) -> int:
        if self._facade:
            return self._facade.get_undo_memory_limit_mb()
        return self._undo_memory_limit_mb

    def set_undo_max_steps(self, steps: int) -> None:
        self._undo_max_steps = int(steps)
        if self._facade:
            self._facade.set_undo_max_steps(int(steps))
        for fac in self._doc_facades.values():
            if fac:
                fac.set_undo_max_steps(int(steps))

    def get_undo_max_steps(self) -> int:
        if self._facade:
            return self._facade.get_undo_max_steps()
        return self._undo_max_steps

    def get_undo_count(self) -> int:
        if self._facade:
            return self._facade.get_undo_count()
        return 0

    def get_redo_count(self) -> int:
        if self._facade:
            return self._facade.get_redo_count()
        return 0

    def can_undo(self) -> bool:
        if self._facade:
            return self._facade.can_undo()
        return self.get_undo_count() > 0

    def can_redo(self) -> bool:
        if self._facade:
            return self._facade.can_redo()
        return self.get_redo_count() > 0
