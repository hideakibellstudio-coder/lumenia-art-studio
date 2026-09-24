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
from ui.core.plugins.panel_ids import PanelId
from .engine.recording_engine import TimelapseRecordingEngine
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
        self._engine: Optional[TimelapseRecordingEngine] = None
        self._canvas = None

    def activate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws is None:
            raise RuntimeError("[RecordingPlugin] WorkspaceService não encontrado no ServiceRegistry.")
        # O plugin é o dono: cria o motor de gravação e liga o fim de cada
        # traço do canvas a ele; guias vêm do renderizador do workspace.
        self._engine = TimelapseRecordingEngine()
        self._engine.set_guides_renderer(ws.render_geometry_overlay)
        self._canvas = ws.canvas
        if self._canvas is not None:
            self._canvas.strokeFinished.connect(self._engine.on_stroke_finished)
        self._panel = RecordingPanel(self._engine, anchor=self._canvas)

        ws.add_panel(
            panel_id=PanelId.RECORDING,
            title="Timelapse",
            widget=self._panel,
            area="right",
            icon_path="video",
        )
        logger.info("[RecordingPlugin] Painel de Gravação & Timelapse ativado com sucesso.")

    def deactivate(self) -> None:
        ws = self.context.service_registry.get(WorkspaceService)
        if ws is not None and self._panel is not None:
            ws.remove_panel(PanelId.RECORDING)
        if self._canvas is not None and self._engine is not None:
            self._canvas.strokeFinished.disconnect(self._engine.on_stroke_finished)
        if self._panel is not None:
            self._panel.shutdown()
        if self._engine is not None:
            self._engine.cleanup_temp_files()
        self._panel = self._engine = self._canvas = None
        logger.info("[RecordingPlugin] Painel de Gravação & Timelapse desativado.")
