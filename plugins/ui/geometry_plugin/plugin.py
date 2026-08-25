"""GeometryPlugin — Plugin UI de Réguas, Simetrias e Perspectiva (Lumenia V2)."""

from __future__ import annotations

import os
import logging
from ui.core.plugins.base import BasePlugin
from ui.core.plugins.metadata import PluginMetadata, PluginType
from ui.core.plugins.workspace_contract import WorkspaceService
from .panel import GeometryPanel

logger = logging.getLogger(__name__)

class GeometryPlugin(BasePlugin):
    """Plugin de UI que registra o GeometryPanel na doca direita."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="lumenia.geometry_ui",
            name="Geometry & Symmetry Panel",
            version="2.0.0",
            author="Lumenia Team",
            description="Painel de Réguas, Simetrias Dinâmicas e Guias de Perspectiva.",
            plugin_type=PluginType.UI,
            dependencies=["lumenia.workspace_core"],
        )

    def get_priority(self) -> int:
        return 65

    def initialize(self, context) -> None:
        super().initialize(context)
        self._panel = None

    def activate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws is None:
            raise RuntimeError("[GeometryPlugin] WorkspaceService não encontrado.")

        self._panel = GeometryPanel()

        ws.add_panel(
            panel_id="geometry",
            title="Guias & Simetria",
            widget=self._panel,
            area="right",
            icon_path="shapes",
        )
        logger.info("[GeometryPlugin] Painel de Guias & Simetria ativado com sucesso.")

    def deactivate(self) -> None:
        if self._panel is not None:
            self._panel.deleteLater()
            self._panel = None
