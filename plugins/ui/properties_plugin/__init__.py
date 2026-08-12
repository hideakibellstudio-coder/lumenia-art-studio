"""
PropertiesPlugin — Plugin de UI para o painel de propriedades
=============================================================
Adiciona o PropertiesDock (Navigator + Camadas) na doca direita
do workspace e conecta os sinais de câmera ao WorkspaceContainer.

Dependência: lumenia.workspace_core (deve estar ativo primeiro).
"""

from __future__ import annotations

import logging

from ui.core.plugins.base import BasePlugin
from ui.core.plugins.metadata import PluginMetadata, PluginType
from ui.core.plugins.workspace_contract import WorkspaceService
from .dock import PropertiesDock

logger = logging.getLogger(__name__)


class PropertiesPlugin(BasePlugin):
    """
    Plugin de UI que registra o PropertiesDock no workspace.

    Ao ser ativado:
      1. Cria o PropertiesDock (Navigator + Camadas)
      2. Adiciona na área direita via WorkspaceService.add_panel()
      3. Conecta sinais de câmera e camadas ao WorkspaceContainer

    Ao ser desativado:
      - Remove o painel via WorkspaceService.remove_panel()
    """

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="lumenia.properties_ui",
            name="Properties Panel",
            version="2.0.0",
            author="Lumenia Team",
            description="Painel de navegação (Navigator) e gerenciamento de camadas.",
            plugin_type=PluginType.UI,
            dependencies=["lumenia.workspace_core"],
        )

    def get_priority(self) -> int:
        return 40  # Carregado após WorkspaceCore e plugins individuais

    def initialize(self, context) -> None:
        super().initialize(context)
        self._dock = None

    def activate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws is None:
            raise RuntimeError(
                "[PropertiesPlugin] WorkspaceService não encontrado no ServiceRegistry. "
                "Certifique-se de que lumenia.workspace_core está ativo."
            )

        self._dock = PropertiesDock()

        ws.add_panel(
            panel_id="properties",
            title="Navegador & Camadas",
            widget=self._dock,
            area="right",
        )

        logger.info("[PropertiesPlugin] PropertiesDock adicionado na doca direita.")

    def deactivate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws and self._dock:
            ws.remove_panel("properties")
        self._dock = None
        logger.info("[PropertiesPlugin] PropertiesDock removido.")
