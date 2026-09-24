"""LayerCommands — comandos que o painel de camadas dispara sobre o documento ativo.

Cada comando é uma transação de camadas (`layer_transaction`): chama o
`LocalLayerManager` (fonte única, que sincroniza o motor) e devolve uma
mensagem de status. Não conhece widgets: a view se atualiza pelos sinais do
gerenciador.

Substitui `panel_actions.py`, `panel_grid_actions.py` e `panel_sync.py`
(2026-09-24): funções soltas que recebiam o painel, mexiam nos atributos
privados dele e sincronizavam o motor por um segundo caminho, paralelo ao do
gerenciador — com as duas sincronizações ativas, "mover camada" reordenava
o motor duas vezes e dependia do histórico para desfazer a diferença.
"""
from __future__ import annotations

from typing import Callable, Optional

from ui.core.document.history import layer_transaction
from ui.core.document.layer_blend_mode import LayerBlendMode
from ui.core.document.layer_manager import LocalLayerManager
from ui.core.engine.registry import EngineRegistry
from ui.core.plugins.canvas_access import request_canvas_repaint


class LayerCommands:
    def __init__(self, show_status: Callable[[str], None]) -> None:
        # Documento cujas camadas os comandos alteram (trocado pelo painel
        # quando o documento ativo muda). `layer_transaction` exige que seja o
        # gerenciador do documento ativo.
        self.layer_manager: Optional[LocalLayerManager] = None
        self._status = show_status

    def show_status(self, message: str) -> None:
        """Também usado por `layer_transaction` para relatar falhas."""
        self._status(message)

    # ── Estrutura ─────────────────────────────────────────────────────────

    @layer_transaction
    def add_layer(self, name: Optional[str] = None) -> None:
        self.layer_manager.add_layer(name or f"Camada {len(self.layer_manager.layers) + 1}")

    @layer_transaction
    def add_group(self, name: Optional[str] = None) -> None:
        group_name = name or "Novo Grupo"
        self.layer_manager.add_group(group_name)
        self.show_status(f"Grupo '{group_name}' criado com sucesso.")

    @layer_transaction
    def delete_active(self) -> None:
        layer = self.layer_manager.get_active_layer()
        if layer and self.layer_manager.remove_layer(layer.uid):
            self.show_status(f"Camada '{layer.name}' removida.")

    @layer_transaction
    def duplicate_active(self) -> None:
        layer = self.layer_manager.get_active_layer()
        if layer and self.layer_manager.duplicate_layer(layer.uid):
            self.show_status(f"Camada '{layer.name}' duplicada com sucesso.")

    @layer_transaction
    def merge_active_down(self) -> None:
        layer = self.layer_manager.get_active_layer()
        if layer and self.layer_manager.merge_down(layer.uid):
            self.show_status(f"Camada '{layer.name}' fundida para baixo.")

    @layer_transaction
    def move_active_up(self) -> None:
        layer = self.layer_manager.get_active_layer()
        if layer and self.layer_manager.move_layer_up(layer.uid):
            self.show_status(f"Camada '{layer.name}' movida para cima.")

    @layer_transaction
    def move_active_down(self) -> None:
        layer = self.layer_manager.get_active_layer()
        if layer and self.layer_manager.move_layer_down(layer.uid):
            self.show_status(f"Camada '{layer.name}' movida para baixo.")

    @layer_transaction
    def rename(self, uid: int, name: str) -> None:
        self.layer_manager.rename_layer(uid, name)

    # ── Pixels ────────────────────────────────────────────────────────────

    @layer_transaction
    def clear_active_pixels(self) -> None:
        layer = self.layer_manager.get_active_layer()
        if not layer:
            return
        if layer.locked:
            self.show_status("A camada está bloqueada e não pode ser limpa.")
            return
        backend = EngineRegistry.instance().get_backend()
        if backend is not None:
            backend.clear_layer(self.layer_manager.active_index)
            request_canvas_repaint()
            self.layer_manager.request_thumbnails([layer.uid])
        self.show_status(f"Conteúdo de '{layer.name}' limpo.")

    # ── Propriedades ──────────────────────────────────────────────────────

    @layer_transaction
    def set_active_opacity(self, opacity: float) -> None:
        self.layer_manager.set_layer_opacity(self.layer_manager.active_index, opacity)

    @layer_transaction
    def set_active_blend_mode(self, mode: LayerBlendMode) -> None:
        self.layer_manager.set_layer_blend_mode(self.layer_manager.active_index, mode)

    @layer_transaction
    def toggle_visibility(self, uid: int) -> None:
        layer, idx = self._layer_and_index(uid)
        if layer:
            self.layer_manager.set_layer_visibility(idx, not layer.visible)

    @layer_transaction
    def toggle_lock(self, uid: int) -> None:
        layer, idx = self._layer_and_index(uid)
        if layer:
            self.layer_manager.set_layer_lock(idx, not layer.locked)

    @layer_transaction
    def toggle_alpha_lock(self, uid: int) -> None:
        layer, idx = self._layer_and_index(uid)
        if layer:
            self.layer_manager.set_alpha_lock(idx, not layer.alpha_locked)
            self.show_status(f"Alpha Lock em '{layer.name}': {'Ativado' if layer.alpha_locked else 'Desativado'}")

    @layer_transaction
    def toggle_clipping_mask(self, uid: int) -> None:
        layer, idx = self._layer_and_index(uid)
        if layer:
            self.layer_manager.set_clipping_mask(idx, not layer.clipping_mask)
            self.show_status(f"Clipping Mask em '{layer.name}': {'Ativado' if layer.clipping_mask else 'Desativado'}")

    def _layer_and_index(self, uid: int):
        layer = self.layer_manager.get_layer_by_uid(uid)
        return (layer, self.layer_manager.layers.index(layer)) if layer else (None, -1)
