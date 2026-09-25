"""FilterLayerFlow — criar e editar camadas de ajuste com prévia ao vivo.

Enquanto o diálogo de filtro está aberto, a prévia é uma camada de ajuste
temporária criada só no motor, dentro da transação de camadas aberta pelo
fluxo. Confirmar remove a prévia e cria a camada de verdade pelo
`LocalLayerManager` (modelo + motor). Cancelar desfaz a transação inteira —
o histórico restaura pixels e camadas, prévia inclusive.

Colaborador com estado próprio (`_preview_idx`, `_cancelled`). Antes de
2026-09-24 esse estado vivia no painel (`panel._preview_filter_idx`) e era
manipulado por funções soltas em `panel_actions.py`.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6 import QtWidgets

from ui.core.document.history import LayerTransactionCancelled, layer_transaction
from ui.core.document.layer_manager import LocalLayerManager
from ui.core.engine.registry import EngineRegistry
from ui.infrastructure.i18n import tr
from ui.core.plugins.canvas_access import request_canvas_repaint


class FilterLayerFlow:
    def __init__(self, dialog_parent: QtWidgets.QWidget, show_status: Callable[[str], None]) -> None:
        self.layer_manager: Optional[LocalLayerManager] = None  # trocado pelo painel
        self._dialog_parent = dialog_parent
        self._status = show_status
        self._preview_idx = -1
        self._cancelled = False

    def show_status(self, message: str) -> None:
        self._status(message)

    # ── Nova camada de ajuste ─────────────────────────────────────────────

    @layer_transaction
    def add_filter_layer(self) -> None:
        from ui.core.screens.filters import FilterAdjustmentDialog

        dialog = FilterAdjustmentDialog(self._dialog_parent)
        self._preview_idx = -1
        self._cancelled = False
        dialog.preview_changed.connect(self._on_preview_changed)
        dialog.preview_cancelled.connect(self._on_preview_cancelled)
        dialog.filter_created.connect(self._on_filter_created)
        dialog.exec()
        if self._cancelled:
            self._preview_idx = -1
            raise LayerTransactionCancelled()

    def _on_preview_changed(self, name: str, type_id: int, params: list) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend is None:
            return
        if self._preview_idx >= 0 and backend.get_filter_type(self._preview_idx) != type_id:
            backend.remove_layer(self._preview_idx)
            self._preview_idx = -1
        if self._preview_idx < 0:
            self._preview_idx = backend.add_filter_layer(f"Preview {name}", type_id)
        if self._preview_idx >= 0:
            backend.set_filter_params(self._preview_idx, params)
        request_canvas_repaint()

    def _on_preview_cancelled(self) -> None:
        # A prévia pertence à transação aberta em add_filter_layer: não é
        # removida aqui; o cancelamento restaura o snapshot completo.
        self._cancelled = True
        request_canvas_repaint()

    def _on_filter_created(self, name: str, type_id: int, params: list) -> None:
        backend = EngineRegistry.instance().get_backend()
        if self._preview_idx >= 0 and backend is not None:
            backend.remove_layer(self._preview_idx)
        self._preview_idx = -1
        self.layer_manager.add_filter_layer(name, type_id, params)
        self.show_status(tr("status.filter_layer_created", "Camada de Ajuste '{name}' criada com sucesso.",
                            name=name))

    # ── Editar parâmetros de uma camada de ajuste existente ───────────────

    @layer_transaction
    def edit_filter(self, uid: int) -> None:
        layer = self.layer_manager.get_layer_by_uid(uid)
        backend = EngineRegistry.instance().get_backend()
        if layer is None or backend is None:
            return
        c_idx = self.layer_manager.layers.index(layer)
        if not backend.is_filter_layer(c_idx):
            self.show_status(tr("status.not_filter_layer", "A camada '{name}' não é uma camada de ajuste.",
                                name=layer.name))
            return

        from ui.core.screens.filters import FilterEditPopup

        popup = FilterEditPopup(
            c_idx, layer.name, backend.get_filter_type(c_idx), backend.get_filter_params(c_idx), self._dialog_parent
        )
        popup.params_changed.connect(self._on_params_changed)
        if popup.exec() != popup.Accepted:
            raise LayerTransactionCancelled()

    @staticmethod
    def _on_params_changed(native_idx: int, params: list) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend is not None:
            backend.set_filter_params(native_idx, params)
            request_canvas_repaint()
