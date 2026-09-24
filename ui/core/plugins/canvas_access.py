"""
canvas_access — Caminho canônico para alcançar o canvas ativo.
==============================================================
Substitui as varreduras `QApplication.topLevelWidgets()` que painéis e o
modelo de documento usavam para achar o CanvasWidget e pedir repaint (Lei do
Leito do Rio nº 3: zero navegação cega pela árvore de widgets entre plugins).

Tudo passa pelo contrato `WorkspaceService`, registrado pelo WorkspaceCore no
`ServiceRegistry`. Sem workspace registrado (testes headless, boot parcial),
as funções são no-op silenciosos por desenho — não há canvas para atualizar.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ui.core.plugins.registry import ServiceRegistry
from ui.core.plugins.workspace_contract import WorkspaceService

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


def workspace_service() -> Optional[WorkspaceService]:
    """Retorna o WorkspaceService registrado, ou None se não houver workspace."""
    return ServiceRegistry.instance().get(WorkspaceService)


def active_canvas() -> Optional["QWidget"]:
    """Retorna o CanvasWidget ativo, ou None se não houver workspace."""
    ws = workspace_service()
    return ws.canvas if ws is not None else None


def request_canvas_repaint() -> None:
    """Agenda um repaint do canvas ativo (QWidget.update — assíncrono e barato)."""
    ws = workspace_service()
    if ws is not None:
        ws.request_canvas_repaint()
