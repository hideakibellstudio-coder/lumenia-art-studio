"""
LayersPlugin — Plugin UI de Gerenciamento de Camadas (Lumenia V2)
================================================================
Registra o painel isolado LayersPanel na doca direita abaixo do Navegador.
"""

from __future__ import annotations

import logging

from ui.core.plugins.base import BasePlugin
from ui.core.plugins.metadata import PluginMetadata, PluginType
from ui.core.plugins.workspace_contract import WorkspaceService
from .panel import LayersPanel

logger = logging.getLogger(__name__)


class LayersPlugin(BasePlugin):
    """Plugin de UI que registra o LayersPanel na doca direita."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="lumenia.layers_ui",
            name="Layers Panel",
            version="2.0.0",
            author="Lumenia Team",
            description="Gerenciador de camadas, grupos, modos de mesclagem e opacidade.",
            plugin_type=PluginType.UI,
            dependencies=["lumenia.workspace_core"],
        )

    def get_priority(self) -> int:
        return 60  # Adiciona na doca direita abaixo do Navegador

    def initialize(self, context) -> None:
        super().initialize(context)
        self._panel = None

    def activate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws is None:
            raise RuntimeError("[LayersPlugin] WorkspaceService não encontrado.")

        self._panel = LayersPanel()

        ws.add_panel(
            panel_id="layers",
            title="Camadas",
            widget=self._panel,
            area="right",
            icon_path="layers",
        )

        logger.info("[LayersPlugin] Gerenciador de Camadas registrado na doca direita abaixo do Navegador.")



    def deactivate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws and self._panel:
            ws.remove_panel("layers")
        self._panel = None
        logger.info("[LayersPlugin] Gerenciador de Camadas removido.")
