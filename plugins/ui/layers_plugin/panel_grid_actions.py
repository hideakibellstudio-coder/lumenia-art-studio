"""Ações da grade do painel de Camadas (limpar, duplicar/excluir seleção, travas, recorte).

Separado de panel.py em 2026-09-22 (447 linhas, na parede dos 450).
"""
from __future__ import annotations

import logging
from typing import Optional

from ui.core.document.local_layer import LocalLayer
from .model import ROLE_LOCKED, ROLE_ALPHA_LOCK, ROLE_CLIPPING_MASK
from ui.core.document.history import layer_transaction

logger = logging.getLogger(__name__)


class LayersPanelGridActionsMixin:
    """Mixin extraído de panel.py (métodos movidos sem alteração)."""

    # --- Ações do Grid ---
    @layer_transaction
    def grid_clear(self): 
        active = self.layer_manager.get_active_layer()
        if not active:
            return
        
        if active.locked:
            self._show_status("A camada está bloqueada e não pode ser limpa.")
            return

        self._sync_to_native_engine("clear_layer")
        self._show_status(f"Conteúdo de '{active.name}' limpo.")

    def duplicate_selection(self):
        self.duplicate_layer()

    @layer_transaction
    def delete_selection(self):
        layer: Optional[LocalLayer] = self.layer_manager.get_active_layer()
        if layer:
            self._updating_selection = True
            try:
                self._sync_to_native_engine("delete")
                self.layer_manager.remove_layer(layer.uid)
                active = self.layer_manager.get_active_layer()
                if active:
                    self._select_uid_in_view(active.uid)
                    self._sync_to_native_engine("select")
                self._show_status(f"Camada '{layer.name}' removida.")
            finally:
                self._updating_selection = False
    
    @layer_transaction
    def grid_toggle_lock(self):
        layer: Optional[LocalLayer] = self.layer_manager.get_active_layer()
        if layer:
            idx = self.model._find_index_by_uid(layer.uid)
            new_lock = not layer.locked
            self.model.setData(idx, new_lock, ROLE_LOCKED)
            self._sync_to_native_engine("lock", layer.uid, new_lock)

    @layer_transaction
    def grid_toggle_alpha(self):
        layer: Optional[LocalLayer] = self.layer_manager.get_active_layer()
        if layer:
            idx = self.model._find_index_by_uid(layer.uid)
            new_val = not layer.alpha_locked
            self.model.setData(idx, new_val, ROLE_ALPHA_LOCK)
            self._sync_to_native_engine("alpha_lock", layer.uid, new_val)
            self._show_status(f"Alpha Lock em '{layer.name}': {'Ativado' if new_val else 'Desativado'}")

    def grid_toggle_clip(self):
        layer: Optional[LocalLayer] = self.layer_manager.get_active_layer()
        if layer:
            self._on_context_toggle_clipping(layer.uid)

    @layer_transaction
    def _on_context_toggle_clipping(self, uid: int):
        layer: Optional[LocalLayer] = self.layer_manager.get_layer_by_uid(uid)
        if layer:
            idx = self.model._find_index_by_uid(layer.uid)
            new_val = not layer.clipping_mask
            self.model.setData(idx, new_val, ROLE_CLIPPING_MASK)
            self._sync_to_native_engine("clipping_mask", layer.uid, new_val)
            self._show_status(f"Clipping Mask em '{layer.name}': {'Ativado' if new_val else 'Desativado'}")
