"""Avisa o usuário, na partida, que o motor de pintura não carregou.

Até 2026-10-01 a falha (binário ausente, de outra versão, sem uma DLL) ia para um
log INFO e o app abria com o canvas vazio, sem explicação. O motivo vem do
`EngineRegistry.load_error`; a janela é a do app real (`app_runner.launch`), não
a do construtor da `MainWindow`, para que os testes que constroem a janela sem
motor não abram um diálogo modal.
"""

from __future__ import annotations

from PySide6 import QtWidgets

from ui.core.engine.registry import EngineRegistry
from ui.infrastructure.i18n import tr


def report_engine_failure(parent: QtWidgets.QWidget | None) -> bool:
    """Mostra a causa se não há motor ativo. Devolve True quando mostrou."""
    registry = EngineRegistry.instance()
    if registry.get_backend() is not None:
        return False
    detail = registry.load_error or tr("messages.engine_unavailable_unknown", "o motor não foi encontrado")
    QtWidgets.QMessageBox.critical(
        parent,
        tr("messages.engine_unavailable_title", "Motor de pintura indisponível"),
        tr("messages.engine_unavailable",
           "O motor de pintura (ALADYN) não foi carregado, e o Lumenia vai abrir sem canvas.\n\n"
           "Causa: {detail}\n\n"
           "Reinstale o Lumenia. Numa cópia de desenvolvimento, recompile o motor: "
           "python scripts/build_native.py",
           detail=detail))
    return True
