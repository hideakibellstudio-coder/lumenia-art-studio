"""
RecordingPlugin — Plugin UI de Gravação de Traços & Timelapse (Lumenia V2)
=========================================================================
Registra o painel isolado RecordingPanel na doca direita (right_dock)
com captura contínua de traços e exportação para MP4 e ZIP.
"""

from __future__ import annotations

import logging
from typing import Optional

from ui.core.plugins.base import BasePlugin
from ui.core.plugins.metadata import PluginMetadata, PluginType
from ui.core.plugins.workspace_contract import WorkspaceService
from .panel import RecordingPanel

logger = logging.getLogger(__name__)


class RecordingPlugin(BasePlugin):
    """Plugin de UI que registra o RecordingPanel na doca direita."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="lumenia.recording_ui",
            name="Gravação & Timelapse",
            version="2.0.0",
            author="Lumenia Team",
            description="Painel de gravação de traços e timelapse do canvas.",
            plugin_type=PluginType.UI,
            dependencies=["lumenia.workspace_core"],
        )

    def get_priority(self) -> int:
        return 60  # Posição na doca direita abaixo do navegador

    def initialize(self, context) -> None:
        super().initialize(context)
        self._panel: Optional[RecordingPanel] = None

    def activate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws is None:
            raise RuntimeError("[RecordingPlugin] WorkspaceService não encontrado no ServiceRegistry.")

        canvas_widget = getattr(ws, "canvas", None)
        self._panel = RecordingPanel(canvas=canvas_widget)

        # Injeta o renderizador de guias do workspace para desacoplamento total
        if hasattr(ws, "render_geometry_overlay"):
            self._panel.engine.set_guides_renderer(ws.render_geometry_overlay)

        ws.add_panel(
            panel_id="recording",
            title="Timelapse",
            widget=self._panel,
            area="right",
            icon_path="video",
        )

        logger.info("[RecordingPlugin] Painel de Gravação & Timelapse ativado com sucesso.")

    def deactivate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws and self._panel:
            ws.remove_panel("recording")

        if self._panel:
            if hasattr(self._panel, "floating_bar") and self._panel.floating_bar:
                self._panel.floating_bar.hide_bar()
                self._panel.floating_bar.close()
            self._panel.engine.cleanup_temp_files()
            self._panel = None

        logger.info("[RecordingPlugin] Painel de Gravação & Timelapse desativado.")
