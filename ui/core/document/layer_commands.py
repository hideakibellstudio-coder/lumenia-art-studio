"""LayerCommands — comandos de camada iniciados pela interface.

Um só lugar para "nova camada", "mesclar para baixo", "achatar imagem",
"propriedades"... Usado pelo painel de camadas e pelo menu Camada da janela
principal. Cada comando é uma transação de camadas (`layer_transaction`):
chama o `LocalLayerManager` (fonte única, que sincroniza o motor) e relata o
resultado por `show_status`. Não conhece widgets: as views se atualizam pelos
sinais do gerenciador.

Histórico: até 2026-09-24 existiam duas implementações. O painel chamava o
gerenciador (`plugins/ui/layers_plugin/layer_commands.py`); o menu chamava o
motor primeiro e o gerenciador depois (`main_window_menu_actions.py`), e só o
menu achatava grupos no motor. As duas davam certo por acaso, graças às
guardas de contagem de `layer_backend_sync`.
"""
from __future__ import annotations

from typing import Callable, Optional

from ui.core.engine.registry import EngineRegistry
from ui.core.plugins.canvas_access import request_canvas_repaint

from .history import layer_transaction
from .layer_blend_mode import LayerBlendMode
from .layer_manager import LocalLayerManager


class LayerCommands:
    def __init__(
        self,
        show_status: Callable[[str], None],
        manager: Callable[[], Optional[LocalLayerManager]],
    ) -> None:
        # `manager` devolve o gerenciador em que os comandos agem: o painel
        # passa o que ele mostra; a janela principal, o do documento ativo.
        # `layer_transaction` exige que seja o do documento ativo.
        self._manager = manager
        self._status = show_status

    @property
    def layer_manager(self) -> Optional[LocalLayerManager]:
        return self._manager()

    def show_status(self, message: str) -> None:
        """Também usado por `layer_transaction` para relatar falhas."""
        self._status(message)

    # ── Estrutura ─────────────────────────────────────────────────────────

    @layer_transaction
    def add_layer(self, name: Optional[str] = None) -> None:
        manager = self.layer_manager
        layer_name = name or f"Camada {len(manager.layers) + 1}"
        manager.add_layer(layer_name)
        self.show_status(f"Camada '{layer_name}' criada.")

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

    @layer_transaction
    def flatten_active_group(self) -> None:
        manager = self.layer_manager
        layer = manager.get_active_layer()
        if layer and layer.is_group and manager.flatten_group(manager.active_index):
            self.show_status("Grupo achatado com sucesso.")

    @layer_transaction
    def flatten_image(self) -> None:
        if self.layer_manager.flatten_image():
            self.show_status("Imagem achatada completamente.")

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
    def set_active_properties(
        self, *, name: str, opacity: float, blend_mode, visible: bool,
        alpha_locked: bool, clipping: bool,
    ) -> None:
        """Diálogo de propriedades: todos os campos num só passo de histórico."""
        manager = self.layer_manager
        idx = manager.active_index
        if idx < 0:
            return
        manager.set_layer_name(idx, name)
        manager.set_layer_opacity(idx, opacity)
        manager.set_layer_blend_mode(idx, blend_mode)
        manager.set_layer_visibility(idx, visible)
        manager.set_alpha_lock(idx, alpha_locked)
        manager.set_clipping_mask(idx, clipping)
        self.show_status("Propriedades da camada atualizadas.")

    @layer_transaction
    def toggle_visibility(self, uid: int) -> None:
        layer, idx = self._layer_and_index(uid)
        if layer:
            self.layer_manager.set_layer_visibility(idx, not layer.visible)
            self.show_status(f"Camada '{layer.name}' {'visível' if layer.visible else 'oculta'}.")

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

    def active_uid(self) -> Optional[int]:
        """UID da camada ativa do gerenciador (para os comandos de alternar)."""
        manager = self.layer_manager
        layer = manager.get_active_layer() if manager else None
        return layer.uid if layer else None

    def _layer_and_index(self, uid: int):
        layer = self.layer_manager.get_layer_by_uid(uid)
        return (layer, self.layer_manager.layers.index(layer)) if layer else (None, -1)
