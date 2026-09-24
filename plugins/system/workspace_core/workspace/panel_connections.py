"""PanelConnections — painéis registrados por `add_panel` e as conexões ligadas a eles.

Toda conexão que depende da vida de um painel passa por aqui, sob o id do
painel. Remover o painel desfaz as conexões dele; adicionar de novo não
herda slots ligados a um QObject prestes a ser destruído.

Colaborador com estado próprio do `WorkspaceContainer` (antes era o mixin
`WorkspacePanelBindingsMixin`, que criava `_panel_widgets` e
`_panel_connections` no dono).
"""
from __future__ import annotations

from typing import Any, Optional

from PySide6 import QtCore


class PanelConnections:
    def __init__(self) -> None:
        self._widgets: dict[str, Any] = {}
        self._connections: dict[str, list[tuple[Any, Any]]] = {}

    def register(self, panel_id: str, widget: Any) -> None:
        self._widgets[panel_id] = widget

    def widget(self, panel_id: str) -> Optional[Any]:
        return self._widgets.get(panel_id)

    def bind(self, panel_id: str, signal: Any, slot: Any, *, unique: bool = False) -> None:
        """Conecta `signal` a `slot` e lembra a conexão sob `panel_id` (sem duplicar)."""
        connections = self._connections.setdefault(panel_id, [])
        if any(bound is signal and bound_slot == slot for bound, bound_slot in connections):
            return
        if unique:
            signal.connect(slot, QtCore.Qt.UniqueConnection)
        else:
            signal.connect(slot)
        connections.append((signal, slot))

    def disconnect(self, panel_id: str) -> None:
        for signal, slot in reversed(self._connections.pop(panel_id, [])):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                # O emissor pode já ter sido destruído por deleteLater().
                pass

    def release(self, panel_id: str) -> Optional[Any]:
        """Desfaz as conexões do painel e esquece o widget (devolvido)."""
        self.disconnect(panel_id)
        return self._widgets.pop(panel_id, None)
