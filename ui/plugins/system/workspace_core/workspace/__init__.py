"""
ui.plugins.system.workspace_core.workspace
=======================================
Pacote do Workspace — centralizado DENTRO do plugin de sistema WorkspaceCore
(regra: a pasta do plugin contém o que ele carrega na interface).

Contém o WorkspaceContainer (widget central), o CanvasWidget, o sistema de
docas/gavetas, a barra flutuante e o viewport com abas MDI.
"""

from .workspace_container import WorkspaceContainer
from .canvas import CanvasWidget
from .viewport_container import TabbedViewportContainer
from .dock.dock_system import AdvancedDockSystem
from .floating_toolbar import FloatingToolbar
from .canvas_overlay import CanvasOverlay
from .pill_handle import PillHandle

__all__ = [
    "WorkspaceContainer",
    "CanvasWidget",
    "TabbedViewportContainer",
    "AdvancedDockSystem",
    "FloatingToolbar",
    "CanvasOverlay",
    "PillHandle",
]