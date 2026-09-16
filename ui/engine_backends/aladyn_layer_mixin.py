"""
AladynLayerMixin — Gerenciador Atômico de Camadas, Grupos e Filtros para o AladynBackend.
==========================================================================================
Isola todas as operações de pilha de camadas, modos de mesclagem, hierarquias de pais,
camadas de ajuste e histórico de desfazer/refazer (Undo/Redo) do motor ALADYN ENGINE.
"""

from __future__ import annotations
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AladynLayerMixin:
    """Mixin responsável pelo gerenciamento de camadas, grupos e filtros no AladynBackend."""

    def clear_canvas(self) -> None:
        if self._facade:
            self._facade.clear_canvas()

    def clear_layer(self, index: int) -> None:
        if self._facade:
            self._facade.clear_layer(index)

    def set_layer_alpha_lock(self, index: int, locked: bool) -> None:
        if self._facade:
            self._facade.set_layer_alpha_lock(index, locked)

    def set_layer_clipping_mask(self, index: int, clipped: bool) -> None:
        if self._facade:
            self._facade.set_layer_clipping_mask(index, clipped)

    def set_layer_blend_mode(self, index: int, mode_val: Any) -> None:
        if self._facade and self._native:
            if isinstance(mode_val, int):
                bm_enum = self._native.LayerBlendMode(mode_val)
            elif isinstance(mode_val, str):
                blend_map = {
                    "Normal": 0, "Multiply": 1, "Multiplicação": 1, "Screen": 2, "Divisão": 2,
                    "Overlay": 3, "Sobreposição": 3, "Darken": 4, "Escurecer": 4, "Lighten": 5, "Clarear": 5,
                    "Erase": 6, "Borracha": 6, "Pass-Through": 7, "Atravessar": 7, "PassThrough": 7,
                    "ColorDodge": 8, "Color Dodge": 8, "Subexposição (Dodge)": 8, "Subexposição": 8,
                    "ColorBurn": 9, "Color Burn": 9, "Superexposição (Burn)": 9, "Superexposição": 9,
                    "Difference": 10, "Diferença": 10, "Exclusion": 11, "Exclusão": 11,
                    "Add": 12, "Adicionar (Add)": 12, "Adicionar": 12
                }
                bm_enum = self._native.LayerBlendMode(blend_map.get(mode_val, 0))
            else:
                bm_enum = mode_val
            self._facade.set_layer_blend_mode(index, bm_enum)

    def reorder_layer(self, from_index: int, to_index: int) -> bool:
        if self._facade:
            return self._facade.reorder_layer(from_index, to_index)
        return False

    def reorder_layers(self, new_order: list[int]) -> bool:
        if self._facade:
            return self._facade.reorder_layers(new_order)
        return False

    def set_layer_parents(self, parent_indices: list[int]) -> bool:
        if self._facade:
            return self._facade.set_layer_parents(parent_indices)
        return False

    def set_layer_document_uid(self, index: int, uid: int) -> bool:
        if self._facade:
            return bool(self._facade.set_layer_document_uid(int(index), int(uid)))
        return False

    def add_group(self, name: str = "Novo Grupo", insert_index: int = -1) -> int:
        if self._facade:
            return self._facade.add_group(name, int(insert_index))
        return -1

    def add_filter_layer(self, name: str, filter_type_id: int, insert_index: int = -1) -> int:
        if self._facade:
            return self._facade.add_filter_layer(name, filter_type_id, int(insert_index))
        return -1

    def set_filter_params(self, index: int, params: list[float]) -> None:
        if self._facade:
            self._facade.set_filter_params(index, [float(x) for x in params])

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

    def get_layer_info(self, index: int) -> dict:
        if self._facade:
            return dict(self._facade.get_layer_info(int(index)))
        return {}

    def is_group(self, index: int) -> bool:
        if self._facade:
            return self._facade.is_group(index)
        return False

    def set_group_pass_through(self, index: int, pass_through: bool) -> bool:
        if self._facade:
            return self._facade.set_group_pass_through(index, pass_through)
        return False

    def duplicate_layer(self, index: int) -> int:
        if self._facade:
            return self._facade.duplicate_layer(index)
        return -1

    def flatten_group(self, index: int) -> bool:
        if self._facade:
            return self._facade.flatten_group(index)
        return False

    def merge_layer_down(self, index: int) -> bool:
        if self._facade:
            return self._facade.merge_layer_down(index)
        return False

    def add_layer(self, name: str = "", insert_index: int = -1) -> int:
        if self._facade:
            return self._facade.add_layer(name, int(insert_index))
        return -1

    def remove_layer(self, index: int) -> bool:
        if self._facade:
            return self._facade.remove_layer(index)
        return False

    def select_layer(self, index: int) -> bool:
        if self._facade:
            return self._facade.select_layer(index)
        return False

    def set_layer_opacity(self, index: int, opacity: float) -> None:
        if self._facade:
            self._facade.set_layer_opacity(index, float(opacity))

    def set_layer_visibility(self, index: int, visible: bool) -> None:
        if self._facade:
            self._facade.set_layer_visibility(index, bool(visible))

    def set_layer_lock(self, index: int, locked: bool) -> None:
        if self._facade:
            self._facade.set_layer_lock(index, bool(locked))

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
            return result
        return False

    def set_undo_memory_limit_mb(self, mb: int) -> None:
        self._undo_memory_limit_mb = int(mb)
        if self._facade:
            self._facade.set_undo_memory_limit_mb(int(mb))
        if hasattr(self, "_doc_facades"):
            for fac in self._doc_facades.values():
                if fac:
                    fac.set_undo_memory_limit_mb(int(mb))

    def get_undo_memory_limit_mb(self) -> int:
        if self._facade:
            return self._facade.get_undo_memory_limit_mb()
        return getattr(self, "_undo_memory_limit_mb", 512)

    def set_undo_max_steps(self, steps: int) -> None:
        self._undo_max_steps = int(steps)
        if self._facade:
            self._facade.set_undo_max_steps(int(steps))
        if hasattr(self, "_doc_facades"):
            for fac in self._doc_facades.values():
                if fac:
                    fac.set_undo_max_steps(int(steps))

    def get_undo_max_steps(self) -> int:
        if self._facade:
            return self._facade.get_undo_max_steps()
        return getattr(self, "_undo_max_steps", 50)

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
