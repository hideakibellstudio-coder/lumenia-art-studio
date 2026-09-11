"""Registro reversível das conexões criadas por painéis dinâmicos."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore


class WorkspacePanelBindingsMixin:
    """Mantém conexão Qt e widget sob a mesma chave de painel.

    Todo ``connect`` que depende da vida de um painel deve passar por este
    registro. Assim, remover e adicionar novamente um painel não preserva
    slots ligados a um QObject que está prestes a ser destruído.
    """

    def _initialize_panel_bindings(self) -> None:
        self._panel_widgets: dict[str, Any] = {}
        self._panel_connections: dict[str, list[tuple[Any, Any]]] = {}

    def _register_panel_widget(self, panel_id: str, widget: Any) -> None:
        self._panel_widgets[panel_id] = widget

    def _bind_panel_signal(
        self,
        panel_id: str,
        signal: Any,
        slot: Any,
        *,
        unique: bool = False,
    ) -> None:
        connections = self._panel_connections.setdefault(panel_id, [])
        if any(bound_signal is signal and bound_slot == slot for bound_signal, bound_slot in connections):
            return
        if unique:
            signal.connect(slot, QtCore.Qt.UniqueConnection)
        else:
            signal.connect(slot)
        connections.append((signal, slot))

    def _disconnect_panel_signals(self, panel_id: str) -> None:
        for signal, slot in reversed(self._panel_connections.pop(panel_id, [])):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                # O emissor pode já ter sido destruído por deleteLater().
                pass

    def _take_panel_widget(self, panel_id: str) -> Any:
        self._disconnect_panel_signals(panel_id)
        return self._panel_widgets.pop(panel_id, None)
