"""
ColorPlugin — Plugin UI da Roda de Cores (Lumenia V2)
=====================================================
Registra o painel isolado da Roda de Cores no topo da doca esquerda (left_dock).

Dependência: lumenia.workspace_core (deve estar ativo primeiro).
"""

from __future__ import annotations

import logging

from ui.core.plugins.base import BasePlugin
from ui.core.plugins.metadata import PluginMetadata, PluginType
from ui.core.plugins.workspace_contract import WorkspaceService

logger = logging.getLogger(__name__)


class ColorPlugin(BasePlugin):
    """Plugin de UI que registra o ColorWheelPanel no topo da doca esquerda."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="lumenia.color_ui",
            name="Color Wheel Panel",
            version="2.0.0",
            author="Lumenia Team",
            description="Roda de cores HSL e amostras de cores recentes.",
            plugin_type=PluginType.UI,
            dependencies=["lumenia.workspace_core"],
        )

    def get_priority(self) -> int:
        return 60  # Prioridade alta: adiciona no topo da doca esquerda

    def initialize(self, context) -> None:
        super().initialize(context)
        self._panel = None

    def activate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws is None:
            raise RuntimeError("[ColorPlugin] WorkspaceService não encontrado.")

        initial_color = getattr(ws.workspace_container, "saved_color", None)
        from .panel import ColorWheelPanel


        self._panel = ColorWheelPanel(initial_color=initial_color)

        ws.add_panel(
            panel_id="color_wheel",
            title="Roda de Cores",
            widget=self._panel,
            area="left",
            icon_path="palette",
        )

        logger.info("[ColorPlugin] Roda de Cores registrada no topo da doca esquerda.")

    def deactivate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws and self._panel:
            ws.remove_panel("color_wheel")
        self._panel = None
        logger.info("[ColorPlugin] Roda de Cores removida.")
