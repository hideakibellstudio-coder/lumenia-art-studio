"""
TelemetryPlugin — Plugin UI de Telemetria do ALADYN ENGINE
============================================================
Registra o painel isolado de Telemetria na doca direita.
"""

from __future__ import annotations

import logging

from ui.core.plugins.base import BasePlugin
from ui.core.plugins.metadata import PluginMetadata, PluginType
from ui.core.plugins.workspace_contract import WorkspaceService

logger = logging.getLogger(__name__)


class TelemetryPlugin(BasePlugin):
    """Plugin de UI que registra o TelemetryPanel na doca direita."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="lumenia.telemetry_ui",
            name="Painel de Telemetria",
            version="1.0.0",
            author="Aladyn Team",
            description="Exibe métricas físicas de pressão, velocidade e vazão em tempo real.",
            plugin_type=PluginType.UI,
            dependencies=["lumenia.workspace_core"],
        )

    def get_priority(self) -> int:
        return 40  # Carregado após o brush_plugin

    def initialize(self, context) -> None:
        super().initialize(context)
        self._panel = None

    def activate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws is None:
            raise RuntimeError("[TelemetryPlugin] WorkspaceService não encontrado.")

        from .panel import TelemetryPanel

        self._panel = TelemetryPanel()

        ws.add_panel(
            panel_id="telemetry",
            title="Telemetria",
            widget=self._panel,
            area="right",
            icon_path="chart",
        )

        logger.info("[TelemetryPlugin] Painel de Telemetria registrado na doca direita.")

    def deactivate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws and self._panel:
            ws.remove_panel("telemetry")
        self._panel = None
        logger.info("[TelemetryPlugin] Painel de Telemetria removido.")
