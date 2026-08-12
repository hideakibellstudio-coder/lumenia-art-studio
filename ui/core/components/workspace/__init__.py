"""
ui.core.components.workspace  (shim de compatibilidade)
=========================================================
Os arquivos foram movidos para plugins.system.workspace_core.workspace.
Este módulo re-exporta para manter compatibilidade com qualquer import restante.
"""

from plugins.system.workspace_core.workspace.workspace_container import WorkspaceContainer
from plugins.system.workspace_core.workspace.dock_system import AdvancedDockSystem

__all__ = ["WorkspaceContainer", "AdvancedDockSystem"]
