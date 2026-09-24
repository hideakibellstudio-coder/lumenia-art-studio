"""ShellActions — base dos colaboradores de ação da janela principal.

Cada colaborador (documentos, edição, camadas, imagem, diálogos,
recuperação) recebe pelo construtor o que usa e fala com o usuário pelo sinal
`statusMessage`, que a `MainWindow` liga à barra de status. Nenhum lê atributo
de outro: é isso que os separa dos seis mixins que existiam até 2026-09-24,
que se liam uns aos outros por `self` (`self.status_bar`, `self.workspace`,
`self._backend_ready`...).
"""
from __future__ import annotations

from typing import Any, Callable

from PySide6 import QtCore

BackendProvider = Callable[[], Any]


class ShellActions(QtCore.QObject):
    statusMessage = QtCore.Signal(str, int)

    def _say(self, text: str, timeout_ms: int = 2000) -> None:
        self.statusMessage.emit(text, timeout_ms)


def backend_ready(backend: Any) -> bool:
    """Motor presente e utilizável (sem ele as ações só avisam)."""
    return bool(backend is not None and backend.available)
