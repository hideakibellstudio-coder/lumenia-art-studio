"""LayerActions — menu Camada da janela principal.

Os comandos são os mesmos do painel de camadas
(`ui.core.document.layer_commands.LayerCommands`), aplicados ao documento
ativo; aqui ficam só o diálogo de propriedades e os atalhos "na camada ativa".
Colaborador da `MainWindow` (ver `shell_actions.py`).
"""
from __future__ import annotations

from PySide6 import QtWidgets

from ui.core.dialogs.layer_properties_dialog import LayerPropertiesDialog
from ui.core.document.layer_commands import LayerCommands
from ui.core.document.manager import DocumentManager

from .shell_actions import ShellActions


class LayerActions(ShellActions):
    def __init__(self, window: QtWidgets.QWidget, dm: DocumentManager) -> None:
        super().__init__(window)
        self._window = window
        self._dm = dm
        self.commands = LayerCommands(
            show_status=lambda message: self._say(message, 3000),
            manager=self._active_manager,
        )

    def _active_manager(self):
        doc = self._dm.active_document()
        return doc.layer_manager if doc is not None else None

    def toggle_active_clipping(self) -> None:
        self.commands.toggle_clipping_mask(self.commands.active_uid())

    def toggle_active_alpha_lock(self) -> None:
        self.commands.toggle_alpha_lock(self.commands.active_uid())

    def toggle_active_visibility(self) -> None:
        self.commands.toggle_visibility(self.commands.active_uid())

    def open_properties_dialog(self) -> None:
        manager = self._active_manager()
        layer = manager.get_active_layer() if manager is not None else None
        if layer is None:
            return
        dialog = LayerPropertiesDialog(
            name=layer.name,
            opacity=layer.opacity,
            blend_mode=layer.blend_mode,
            is_visible=layer.visible,
            is_alpha_locked=layer.alpha_locked,
            is_clipping=layer.clipping_mask,
            parent=self._window,
        )
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        res = dialog.get_results()
        self.commands.set_active_properties(
            name=res["name"],
            opacity=res["opacity"],
            blend_mode=res["blend_mode"],
            visible=res["is_visible"],
            alpha_locked=res["is_alpha_locked"],
            clipping=res["is_clipping"],
        )
