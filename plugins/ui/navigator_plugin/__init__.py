"""
NavigatorPlugin — Plugin UI de Navegação da Tela (Lumenia V2)
============================================================
Registra o painel isolado NavigatorPanel na doca direita (right_dock).
"""

from __future__ import annotations

import logging

from ui.core.plugins.base import BasePlugin
from ui.core.plugins.metadata import PluginMetadata, PluginType
from ui.core.plugins.workspace_contract import WorkspaceService
from ui.core.plugins.panel_ids import PanelId
from .panel import NavigatorPanel

logger = logging.getLogger(__name__)


class NavigatorPlugin(BasePlugin):
    """Plugin de UI que registra o NavigatorPanel na doca direita."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="lumenia.navigator_ui",
            name="Navigator Panel",
            version="2.0.0",
            author="Lumenia Team",
            description="Painel de navegação, zoom, rotação e controle de câmera do canvas.",
            plugin_type=PluginType.UI,
            dependencies=["lumenia.workspace_core"],
        )

    def get_priority(self) -> int:
        return 70  # Prioridade alta: adiciona no topo da doca direita

    def initialize(self, context) -> None:
        super().initialize(context)
        self._panel = None

    def activate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws is None:
            raise RuntimeError("[NavigatorPlugin] WorkspaceService não encontrado.")

        self._panel = NavigatorPanel()

        ws.add_panel(
            panel_id=PanelId.NAVIGATOR,
            title="Navegador",
            widget=self._panel,
            area="right",
            icon_path="compass",
        )

        logger.info("[NavigatorPlugin] Navegador registrado no topo da doca direita.")



    def deactivate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws and self._panel:
            ws.remove_panel(PanelId.NAVIGATOR)
        self._panel = None
        logger.info("[NavigatorPlugin] Navegador removido.")
