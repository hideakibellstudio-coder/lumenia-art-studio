"""
BrushPlugin — Plugin UI das Configurações do Pincel & Ferramentas (Lumenia V2)
=============================================================================
Registra o painel isolado BrushSettingsPanel na doca esquerda abaixo da Roda de Cores.
"""

from __future__ import annotations

import logging

from ui.core.plugins.base import BasePlugin
from ui.core.plugins.metadata import PluginMetadata, PluginType
from ui.core.plugins.workspace_contract import WorkspaceService
from ui.core.state import BrushState, require
from .panel import BrushSettingsPanel

logger = logging.getLogger(__name__)


class BrushPlugin(BasePlugin):
    """Plugin de UI que registra o BrushSettingsPanel na doca esquerda."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="lumenia.brush_ui",
            name="Brush Settings Panel",
            version="2.0.0",
            author="Lumenia Team",
            description="Painel de configurações de pincel, preview do traço e parâmetros rápidos.",
            plugin_type=PluginType.UI,
            dependencies=["lumenia.workspace_core"],
        )

    def get_priority(self) -> int:
        return 50  # Adiciona na doca esquerda abaixo de Cores

    def initialize(self, context) -> None:
        super().initialize(context)
        self._panel = None

    def activate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws is None:
            raise RuntimeError("[BrushPlugin] WorkspaceService não encontrado.")

        self._panel = BrushSettingsPanel(require(self.context.service_registry, BrushState))

        ws.add_panel(
            panel_id="brush_settings",
            title="Pincel & Ferramentas",
            widget=self._panel,
            area="left",
            icon_path="brush",
        )

        logger.info("[BrushPlugin] Pincéis & Ferramentas registrado na doca esquerda abaixo de Cores.")

    def deactivate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws and self._panel:
            ws.remove_panel("brush_settings")
        self._panel = None
        logger.info("[BrushPlugin] BrushSettingsPanel removido.")
